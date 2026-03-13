# backend/ids.py
import hashlib, base64, unicodedata

from datetime import datetime, timezone
from typing import Optional, Tuple


def digest_id_hour(digest_at: Optional[str] = None) -> Tuple[str, datetime]:
    """
    Convert a timestamp string (YYYYMMDDTHH) or None into a digest ID and UTC datetime.

    If digest_at is a string in the format YYYYMMDDTHH, parse it as a UTC datetime.
    Otherwise, use the current UTC time.

    Returns:
        digest_id: str formatted as YYYYMMDDTHH
        dt: datetime object in UTC
    """
    if isinstance(digest_at, str):
        try:
            # Parse 'YYYYMMDDTHH' as UTC
            dt = datetime.strptime(digest_at, "%Y%m%dT%H").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"Invalid digest_at format '{digest_at}', expected YYYYMMDDTHH")
    else:
        dt = datetime.now(timezone.utc)

    digest_id = dt.strftime("%Y%m%dT%H")
    return digest_id, dt

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", (s or "").strip())
    return " ".join(s.split())

def stable_index_id(title: str, source: str, url: str="") -> str:
    key = f"{_norm(title)}|{_norm(source)}|{url.strip().lower()}"
    h = hashlib.sha1(key.encode("utf-8")).digest()
    return base64.b32encode(h)[:10].decode("ascii")

