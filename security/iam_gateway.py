import os
import hashlib
from typing import Dict, Any


class IAMGateway:
    """بوابة التحكم بالوصول والهوية الموحدة (RBAC + Multi-Tenant Data Isolation)."""

    ROLE_PERMISSIONS = {
        "admin": {"read", "write", "execute", "spawn_agent", "export", "audit"},
        "partner": {"read", "write", "execute", "export"},
        "trainee": {"read", "execute"},
        "guest": {"read"},
    }

    def __init__(self):
        self.admin_phone = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "")))
        self.partner_phone = "".join(filter(str.isdigit, os.environ.get("AHMED_PHONE", "")))
        self.allowed_group = os.environ.get("ALLOWED_GROUP", "").strip()

    def _tenant_hash(self, raw_id: str) -> str:
        clean = "".join(filter(str.isdigit, raw_id)) or raw_id
        return "tenant_" + hashlib.sha256(clean.encode("utf-8")).hexdigest()[:12]

    def resolve_session(self, cid: str, requested_role: str = "admin", sender: str = "") -> Dict[str, Any]:
        cid_digits = "".join(filter(str.isdigit, cid))
        sender_digits = "".join(filter(str.isdigit, sender))

        if "@c.us" in cid:
            if self.admin_phone and self.admin_phone in cid_digits:
                role = "admin"
                auth = True
            elif self.partner_phone and self.partner_phone in cid_digits:
                role = "partner"
                auth = True
            else:
                role = "guest"
                auth = not bool(self.admin_phone)
        elif "@g.us" in cid:
            if self.allowed_group and self.allowed_group in cid:
                auth = True
                role = "admin" if (self.admin_phone and self.admin_phone in sender_digits) else "partner"
            else:
                auth = False
                role = "guest"
        else:
            # قنوات الويب أو الروبوتية الداخلية
            role = requested_role if requested_role in self.ROLE_PERMISSIONS else "trainee"
            auth = True

        tenant_id = "tenant_shared_ops" if "@g.us" in cid else self._tenant_hash(cid)
        return {
            "authorized": auth,
            "role": role,
            "tenant_id": tenant_id,
            "permissions": sorted(list(self.ROLE_PERMISSIONS.get(role, set()))),
        }

    def check_permission(self, role: str, action: str) -> bool:
        return action in self.ROLE_PERMISSIONS.get(role, set())


IAM_GATEWAY = IAMGateway()
