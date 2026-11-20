import time
import threading
from typing import Dict, Any, List
from core.event_bus import BUS
from security.audit_ledger import AUDIT_LEDGER


class RoboticsAndMCPBridge:
    """بروتوكول الربط الشامل (Model Context Protocol + Robotics Telemetry & Command Bridge)."""

    ALLOWED_COMMANDS = {"MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "STOP", "HOVER", "SCAN_AREA", "RETURN_HOME"}

    def __init__(self):
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._command_queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def register_telemetry(self, device_id: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._devices[device_id] = {
                "device_id": device_id,
                "status": telemetry.get("status", "online"),
                "battery": telemetry.get("battery", 100),
                "coords": telemetry.get("coords", {"x": 0.0, "y": 0.0, "z": 0.0}),
                "last_seen": time.time(),
            }
        BUS.publish("robotics.telemetry", {"device_id": device_id, "telemetry": telemetry})
        return {"ok": True, "device": self._devices[device_id]}

    def dispatch_command(self, actor: str, device_id: str, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        cmd = command.strip().upper()
        if cmd not in self.ALLOWED_COMMANDS:
            AUDIT_LEDGER.append(actor, "ROBOTICS_CMD_REJECTED", {"device": device_id, "cmd": cmd})
            return {"ok": False, "error": f"أمر غير مصرح به في بروتوكول السلامة: {cmd}"}

        packet = {
            "device_id": device_id,
            "command": cmd,
            "params": params or {},
            "issued_by": actor,
            "timestamp": time.time(),
        }
        with self._lock:
            self._command_queue.append(packet)
            if len(self._command_queue) > 100:
                self._command_queue.pop(0)

        AUDIT_LEDGER.append(actor, "ROBOTICS_CMD_SENT", {"device": device_id, "cmd": cmd})
        BUS.publish("robotics.command", packet)
        return {"ok": True, "dispatched": packet}

    def fleet_status(self) -> Dict[str, Any]:
        with self._lock:
            return {"connected_units": len(self._devices), "devices": dict(self._devices), "queued_cmds": len(self._command_queue)}


ROBOTICS_BRIDGE = RoboticsAndMCPBridge()
