import os
from pathlib import Path
from .config import settings

class RegistryError(Exception):
    pass

# Logical name -> filename under ~/programs (pinned; never PATH-resolved).
BINARIES: dict[str, str] = {
    "admixture": "admixture",
    "emibd9": "EM_IBD_P",
    "ne2": "Ne2-1M",
    "plink": "plink",
}

def resolve(name: str) -> Path:
    if name not in BINARIES:
        raise RegistryError(f"unknown binary: {name}")
    p = (settings().programs_dir / BINARIES[name]).resolve()
    if not p.is_file() or not os.access(p, os.X_OK):
        raise RegistryError(f"binary not found or not executable: {p}")
    return p
