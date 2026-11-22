import hashlib
import os
from typing import Any


class IAMGateway:
    ROLE_PERMISSIONS: dict[str, set[str]] = {
        "admin": {"read", "write", "execute", "spawn_agent", "export", "audit"},
        "partner": {"read", "write", "execute", "export"},
        "trainee": {"read", "execute"},
        "guest": {"read"},
    }

    def __init__(self) -> None:
        self.admin_phone = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "")))
        self.partner_phone = "".join(filter(str.isdigit, os.environ.get("AHMED_PHONE", "")))
        self.allowed_group = os.environ.get("ALLOWED_GROUP", "").strip()
        self.admin_secret = os.environ.get("ADMIN_SECRET", "").strip()

    @staticmethod
    def _phones_match(phone_a: str, phone_b: str) -> bool:
        if not phone_a or not phone_b:
            return False
        if phone_a == phone_b:
            return True
        return len(phone_a) >= 9 and len(phone_b) >= 9 and phone_a[-9:] == phone_b[-9:]

    def _tenant_hash(self, raw_id: str) -> str:
        clean = "".join(filter(str.isdigit, raw_id)) or raw_id
        return "tenant_" + hashlib.sha256(clean.encode("utf-8")).hexdigest()[:12]

    def resolve_session(
        self, cid: str, requested_role: str = "trainee", sender: str = "", token: str = ""
    ) -> dict[str, Any]:
        cid_digits = "".join(filter(str.isdigit, cid.split("@")[0]))
        sender_digits = "".join(filter(str.isdigit, sender.split("@")[0]))

        if "@c.us" in cid:
            if self._phones_match(self.admin_phone, cid_digits):
                role, auth = "admin", True
            elif self._phones_match(self.partner_phone, cid_digits):
                role, auth = "partner", True
            else:
                role, auth = "guest", not bool(self.admin_phone)
        elif "@g.us" in cid:
            if self.allowed_group and (cid == self.allowed_group or self.allowed_group in cid):
                auth = True
                role = "admin" if self._phones_match(self.admin_phone, sender_digits) else "partner"
            else:
                auth, role = False, "guest"
        else:
            if requested_role == "admin":
                is_local_cli = cid == "web_cli_admin"
                has_valid_token = bool(self.admin_secret and token == self.admin_secret)
                role = "admin" if (is_local_cli or has_valid_token) else "trainee"
            else:
                role = requested_role if requested_role in self.ROLE_PERMISSIONS else "trainee"
            auth = True

        tenant_id = "tenant_shared_ops" if "@g.us" in cid else self._tenant_hash(cid)
        return {
            "authorized": auth,
            "role": role,
            "tenant_id": tenant_id,
            "permissions": sorted(self.ROLE_PERMISSIONS.get(role, set())),
        }

    def check_permission(self, role: str, action: str) -> bool:
        return action in self.ROLE_PERMISSIONS.get(role, set())


IAM_GATEWAY = IAMGateway()
