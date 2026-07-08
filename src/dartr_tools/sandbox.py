import re
from pathlib import Path
from .config import settings

_SAFE_BASENAME = re.compile(r"^[A-Za-z0-9._-]+$")

class SandboxError(Exception):
    pass

def _roots(workdir: Path) -> list[Path]:
    try:
        return [workdir.resolve(), *(d.resolve() for d in settings().data_dirs)]
    except (OSError, RuntimeError) as e:
        raise SandboxError("cannot resolve path") from e

def _within(p: Path, roots: list[Path]) -> bool:
    return any(p == r or p.is_relative_to(r) for r in roots)

def resolve_input(path: str, workdir: Path) -> Path:
    try:
        p = (workdir / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise SandboxError(f"cannot resolve path: {path}") from e
    if not _within(p, _roots(workdir)):
        raise SandboxError(f"input path outside allowed roots: {path}")
    return p

def resolve_output(path: str, workdir: Path) -> Path:
    try:
        root = workdir.resolve()
    except (OSError, RuntimeError) as e:
        raise SandboxError(f"cannot resolve path: {path}") from e
    try:
        p = (workdir / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise SandboxError(f"cannot resolve path: {path}") from e
    if not (p == root or p.is_relative_to(root)):
        raise SandboxError(f"output path must be inside the session workdir: {path}")
    if not _SAFE_BASENAME.match(p.name):
        raise SandboxError(f"output filename contains disallowed characters: {p.name!r}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def bounded(value, lo, hi, name):
    if value < lo or value > hi:
        raise SandboxError(f"{name}={value} out of range [{lo}, {hi}]")
    return value
