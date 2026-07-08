import hashlib, json
from pathlib import Path

def _hash(p: Path) -> str:
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def record(workdir: Path, tool: str, args: dict, inputs: list[Path], outputs: list[Path], exit_code: int) -> dict:
    rec = {
        "ts": args.get("_ts", "unstamped"),
        "tool": tool,
        "args": {k: v for k, v in args.items() if not k.startswith("_")},
        "inputs": [{"path": str(p), "sha256": _hash(p)} for p in inputs],
        "outputs": [str(p.relative_to(workdir)) if p.is_relative_to(workdir) else str(p) for p in outputs],
        "exit_code": exit_code,
    }
    with (workdir / "provenance.jsonl").open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec
