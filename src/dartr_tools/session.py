import re
from pathlib import Path
from .config import settings

_SAFE = re.compile(r"^[A-Za-z0-9_-]+$")

def workdir(session_id: str) -> Path:
    if not _SAFE.match(session_id):
        raise ValueError(f"unsafe session id: {session_id!r}")
    d = settings().work_root / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d
