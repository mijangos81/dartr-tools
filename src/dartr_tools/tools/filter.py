from ..session import workdir
from ..sandbox import resolve_input, resolve_output, bounded
from ..rbridge import call_gl
from ..provenance import record

def filter_snps(session_id: str, rds: str, callrate: float | None = None, maf: float | None = None,
                rdepth: int | None = None, monomorphs: bool = False, out: str = "filtered.rds",
                dry_run: bool = False) -> dict:
    """Filter SNPs by call rate / MAF / read depth, optionally dropping monomorphs."""
    wd = workdir(session_id)
    rin = resolve_input(rds, wd); resolve_output(out, wd)
    if callrate is not None: bounded(callrate, 0, 1, "callrate")
    if maf is not None: bounded(maf, 0, 0.5, "maf")
    params = {"rds": str(rin), "callrate": callrate, "maf": maf, "rdepth": rdepth,
              "monomorphs": monomorphs, "out": out}
    res = call_gl("gl.filter", params, wd, dry_run=dry_run)
    if dry_run:
        return res
    record(wd, "filter_snps", params, [rin], [wd / out], 0)
    return res
