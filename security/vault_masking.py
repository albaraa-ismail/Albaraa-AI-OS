import os
import re
import base64
import hashlib
from typing import Dict, Tuple


class EncryptedSecretVault:
    """قبو الأسرار والمفاتيح المشفر (XOR-SHA256 Stream Cipher) لحماية مفاتيح السحابة في الذاكرة."""

    def __init__(self, master_seed: str = ""):
        seed = master_seed or os.environ.get("SUPABASE_KEY", "Albaraa-OS-Default-Master-Key")
        self._key_bytes = hashlib.sha256(seed.encode("utf-8")).digest()
        self._vault: Dict[str, str] = {}

    def _transform(self, raw: bytes) -> bytes:
        klen = len(self._key_bytes)
        return bytes(b ^ self._key_bytes[i % klen] for i, b in enumerate(raw))

    def store_secret(self, name: str, plaintext: str):
        if not plaintext:
            return
        enc = self._transform(plaintext.encode("utf-8"))
        self._vault[name] = base64.urlsafe_b64encode(enc).decode("ascii")

    def retrieve_secret(self, name: str) -> str:
        token = self._vault.get(name)
        if not token:
            return os.environ.get(name, "").strip()
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        return self._transform(raw).decode("utf-8")


class SensitiveDataMasker:
    """نظام إخفاء البيانات الحساسة تلقائياً (PII Redaction) قبل إرسال النصوص لنماذج الذكاء الخارجية."""

    PATTERNS = [
        ("NATIONAL_ID", r"\b[12]\d{9}\b"),
        ("SA_PHONE", r"\b(?:\+?966|0)5\d{8}\b"),
        ("IBAN", r"\bSA\d{2}[A-Z0-9]{18,20}\b"),
        ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        ("API_KEY", r"\b(?:sk-|gsk_|AIza)[A-Za-z0-9_\-]{16,}\b"),
    ]

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        if not text:
            return text, {}
        mapping: Dict[str, str] = {}
        masked = text
        counter = 1
        for label, pattern in self.PATTERNS:
            for match in list(re.finditer(pattern, masked)):
                original = match.group(0)
                placeholder = f"[REDACTED_{label}_{counter}]"
                if original not in mapping.values():
                    mapping[placeholder] = original
                    masked = masked.replace(original, placeholder)
                    counter += 1
        return masked, mapping

    def unmask(self, text: str, mapping: Dict[str, str]) -> str:
        if not text or not mapping:
            return text
        restored = text
        for placeholder, original in mapping.items():
            restored = restored.replace(placeholder, original)
        return restored


SECRET_VAULT = EncryptedSecretVault()
PII_MASKER = SensitiveDataMasker()
