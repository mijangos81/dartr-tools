from pathlib import Path
from .config import settings

class SandboxError(Exception):
    pass

def _roots(workdir: Path) -> list[Path]:
    return [workdir.resolve(), *(d.resolve() for d in settings().data_dirs)]

def _within(p: Path, roots: list[Path]) -> bool:
    return any(p == r or p.is_relative_to(r) for r in roots)

def resolve_input(path: str, workdir: Path) -> Path:
    p = (workdir / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not _within(p, _roots(workdir)):
        raise SandboxError(f"input path outside allowed roots: {path}")
    return p

def resolve_output(path: str, workdir: Path) -> Path:
    root = workdir.resolve()
    p = (workdir / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not (p == root or p.is_relative_to(root)):
        raise SandboxError(f"output path must be inside the session workdir: {path}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def bounded(value, lo, hi, name):
    if value < lo or value > hi:
        raise SandboxError(f"{name}={value} out of range [{lo}, {hi}]")
    return value
