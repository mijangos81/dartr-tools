import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    programs_dir: Path
    data_dirs: list[Path]
    work_root: Path
    luism01_host: str
    local_timeout: int
    remote_timeout: int

def _paths(env: str) -> list[Path]:
    raw = os.environ.get(env, "")
    return [Path(p).expanduser() for p in raw.split(":") if p]

def settings() -> Settings:
    return Settings(
        programs_dir=Path(os.environ.get("DARTR_PROGRAMS_DIR", str(Path.home() / "programs"))).expanduser(),
        data_dirs=_paths("DARTR_DATA_DIRS"),
        work_root=Path(os.environ.get("DARTR_WORK_ROOT", str(Path.home() / ".dartr-tools" / "work"))).expanduser(),
        luism01_host=os.environ.get("DARTR_LUISM01_HOST", "luism01"),
        local_timeout=int(os.environ.get("DARTR_LOCAL_TIMEOUT", "1800")),
        remote_timeout=int(os.environ.get("DARTR_REMOTE_TIMEOUT", "21600")),
    )
