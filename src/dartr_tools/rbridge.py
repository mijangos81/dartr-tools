import json
from pathlib import Path
from . import executor

ALLOW = {"gl.read.vcf", "gl.filter", "gl2plink", "gl2vcf",
         "gl.report.heterozygosity", "gl.fst.pop", "gl.pcoa", "gl.LDNe"}
_RUNNER = Path(__file__).parent / "r" / "runner.R"

def call_gl(fn: str, params: dict, workdir: Path, timeout: int | None = None, dry_run: bool = False) -> dict:
    if fn not in ALLOW:
        raise ValueError(f"gl function not allowed: {fn}")
    req = {"fn": fn, "params": params, "workdir": str(workdir)}
    reqfile = workdir / "_rreq.json"
    reqfile.write_text(json.dumps(req))
    if dry_run:
        res = executor.run_local(["Rscript", str(_RUNNER), str(reqfile)], cwd=workdir, timeout=timeout, dry_run=dry_run)
        return {"outputs": [], "dry_run": res.stdout}
    respfile = workdir / "_rresp.json"
    respfile.unlink(missing_ok=True)
    res = executor.run_local(["Rscript", str(_RUNNER), str(reqfile)], cwd=workdir, timeout=timeout, dry_run=dry_run)
    if not respfile.is_file():
        raise RuntimeError(
            f"R runner did not produce a response file ({respfile}); stderr:\n{res.stderr}"
        )
    return json.loads(respfile.read_text())
