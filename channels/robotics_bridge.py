import math
import time
import threading
from collections import defaultdict, deque
from typing import Any, Optional
from core.event_bus import BUS
from security.audit_ledger import AUDIT_LEDGER


def _geo_metrics(lat1: float, lon1: float, lat2: float, lon2: float, speed_mps: float = 12.0) -> dict[str, float]:
    from geopy.distance import geodesic

    dist_m = round(geodesic((lat1, lon1), (lat2, lon2)).meters, 2)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lon = math.radians(lon2 - lon1)
    y = math.sin(d_lon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lon)
    bearing = round((math.degrees(math.atan2(y, x)) + 360) % 360, 1)
    eta_sec = round(dist_m / max(speed_mps, 0.5), 1)
    return {"distance_m": dist_m, "bearing_deg": bearing, "eta_sec": eta_sec}


class RoboticsAndMCPBridge:
    """بروتوكول التحكم الذاتي والملاحة الجغرافية والقياس عن بُعد (MCP + Drone/Robotics Bridge)."""

    COMMAND_MATRIX: dict[str, dict[str, Any]] = {
        "TAKEOFF": {"min_battery": 30, "requires_coords": False, "desc": "إقلاع عمودي وتثبيت الارتفاع"},
        "LAND": {"min_battery": 0, "requires_coords": False, "desc": "هبوط آمن في الموقع الحالي"},
        "HOVER": {"min_battery": 15, "requires_coords": False, "desc": "تثبيت الموقع الجغرافي (GPS Hold)"},
        "MOVE_FORWARD": {"min_battery": 20, "requires_coords": False, "desc": "تقدم وفق المسار الحالي"},
        "GOTO_WAYPOINT": {"min_battery": 25, "requires_coords": True, "desc": "توجه إلى إحداثيات GPS محددة"},
        "SCAN_AREA": {"min_battery": 30, "requires_coords": False, "desc": "مسح جغرافي وبصري للمنطقة"},
        "TURN_LEFT": {"min_battery": 15, "requires_coords": False, "desc": "انعطاف يسار"},
        "TURN_RIGHT": {"min_battery": 15, "requires_coords": False, "desc": "انعطاف يمين"},
        "RETURN_HOME": {"min_battery": 0, "requires_coords": False, "desc": "عودة تلقائية لنقطة الانطلاق (RTH)"},
        "STOP": {"min_battery": 0, "requires_coords": False, "desc": "إيقاف فوري للطوارئ"},
    }

    MAX_GEOFENCE_METERS = 5000.0

    def __init__(self) -> None:
        self._devices: dict[str, dict[str, Any]] = {}
        self._queues: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=50))
        self._lock = threading.Lock()

    def register_telemetry(self, device_id: str, telemetry: dict[str, Any]) -> dict[str, Any]:
        coords = telemetry.get("coords") or {"lat": 0.0, "lon": 0.0, "alt": 0.0}
        battery = float(telemetry.get("battery", 100.0))
        now = time.time()

        with self._lock:
            prev = self._devices.get(device_id, {})
            home = prev.get("home_coords") or dict(coords)
            geo = _geo_metrics(home.get("lat", 0.0), home.get("lon", 0.0), coords.get("lat", 0.0), coords.get("lon", 0.0))
            failsafe = battery < 20.0 or geo["distance_m"] > self.MAX_GEOFENCE_METERS

            self._devices[device_id] = {
                "device_id": device_id,
                "status": "failsafe_rth" if failsafe else telemetry.get("status", "online"),
                "battery": battery,
                "coords": coords,
                "home_coords": home,
                "distance_from_home_m": geo["distance_m"],
                "bearing_from_home_deg": geo["bearing_deg"],
                "last_seen": now,
            }
            if failsafe:
                self._queues[device_id].append({"command": "RETURN_HOME", "reason": "auto_failsafe", "timestamp": now})

        BUS.publish("robotics.telemetry", {"device_id": device_id, "failsafe": failsafe})
        return {"ok": True, "device": self._devices[device_id]}

    def dispatch_command(self, actor: str, device_id: str, command: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        cmd = command.strip().upper()
        spec = self.COMMAND_MATRIX.get(cmd)
        if not spec:
            AUDIT_LEDGER.append(actor, "ROBOTICS_CMD_REJECTED", {"device": device_id, "cmd": cmd})
            return {"ok": False, "error": f"أمر غير مدرج في مصفوفة السلامة: {cmd}"}

        params = params or {}
        with self._lock:
            dev = self._devices.get(device_id, {"battery": 100.0, "coords": {"lat": 0.0, "lon": 0.0}})
            if dev.get("battery", 100.0) < spec["min_battery"]:
                return {"ok": False, "error": f"البطارية ({dev['battery']}%) أقل من الحد الآمن للأمر {cmd}"}

            nav_plan = {}
            if spec["requires_coords"] and "lat" in params and "lon" in params:
                cur = dev.get("coords", {})
                nav_plan = _geo_metrics(cur.get("lat", 0.0), cur.get("lon", 0.0), float(params["lat"]), float(params["lon"]))
                if nav_plan["distance_m"] > self.MAX_GEOFENCE_METERS:
                    return {"ok": False, "error": f"الهدف خارج نطاق السياج الجغرافي ({nav_plan['distance_m']}m)"}

            packet = {"device_id": device_id, "command": cmd, "params": params, "nav": nav_plan, "issued_by": actor, "timestamp": time.time()}
            self._queues[device_id].append(packet)

        AUDIT_LEDGER.append(actor, "ROBOTICS_CMD_SENT", {"device": device_id, "cmd": cmd})
        BUS.publish("robotics.command", packet)
        return {"ok": True, "dispatched": packet}

    def pull_commands(self, device_id: str) -> list[dict[str, Any]]:
        with self._lock:
            cmds = list(self._queues[device_id])
            self._queues[device_id].clear()
            return cmds

    def fleet_status(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            summary = {
                k: {**v, "online": (now - v.get("last_seen", 0)) < 30, "pending_cmds": len(self._queues[k])}
                for k, v in self._devices.items()
            }
            return {"connected_units": len(summary), "devices": summary}


ROBOTICS_BRIDGE = RoboticsAndMCPBridge()
