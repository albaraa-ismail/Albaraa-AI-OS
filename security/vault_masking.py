import base64
import hashlib
import os
import re


class EncryptedSecretVault:
    def __init__(self, master_seed: str = "") -> None:
        seed = master_seed or os.environ.get("SUPABASE_KEY", "Albaraa-OS-Default-Master-Key")
        self._key_bytes = hashlib.sha256(seed.encode("utf-8")).digest()
        self._vault: dict[str, str] = {}

    def _transform(self, raw: bytes) -> bytes:
        klen = len(self._key_bytes)
        return bytes(b ^ self._key_bytes[i % klen] for i, b in enumerate(raw))

    def store_secret(self, name: str, plaintext: str) -> None:
        if not plaintext:
            return
        enc = self._transform(plaintext.encode("utf-8"))
        self._vault[name] = base64.urlsafe_b64encode(enc).decode("ascii")

    def retrieve_secret(self, name: str) -> str:
        token = self._vault.get(name)
        if not token:
            return os.environ.get(name, "").strip()
        try:
            raw = base64.urlsafe_b64decode(token.encode("ascii"))
            return self._transform(raw).decode("utf-8")
        except Exception:
            return os.environ.get(name, "").strip()


class SensitiveDataMasker:
    PATTERNS = [
        ("NATIONAL_ID", r"\b[12]\d{9}\b"),
        ("SA_PHONE", r"\b(?:\+?966|0)5\d{8}\b"),
        ("IBAN", r"\bSA\d{2}[A-Z0-9]{18,20}\b"),
        ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        ("API_KEY", r"\b(?:sk-|gsk_|AIza)[A-Za-z0-9_\-]{16,}\b"),
    ]

    def mask(self, text: str) -> tuple[str, dict[str, str]]:
        if not text:
            return text, {}
        mapping: dict[str, str] = {}
        reverse_map: dict[str, str] = {}
        masked = text
        counter = 1
        for label, pattern in self.PATTERNS:
            for match in list(re.finditer(pattern, masked)):
                original = match.group(0)
                if original in reverse_map:
                    placeholder = reverse_map[original]
                else:
                    placeholder = f"[REDACTED_{label}_{counter}]"
                    mapping[placeholder] = original
                    reverse_map[original] = placeholder
                    counter += 1
                masked = masked.replace(original, placeholder)
        return masked, mapping

    def unmask(self, text: str, mapping: dict[str, str]) -> str:
        if not text or not mapping:
            return text
        restored = text
        for placeholder, original in mapping.items():
            pattern = re.compile(re.escape(placeholder), flags=re.IGNORECASE)
            restored = pattern.sub(lambda _: original, restored)
        return restored


SECRET_VAULT = EncryptedSecretVault()
PII_MASKER = SensitiveDataMasker()
