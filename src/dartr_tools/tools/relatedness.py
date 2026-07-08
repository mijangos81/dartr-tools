from ..session import workdir
from ..sandbox import resolve_input
from ..config import settings
from ..registry import resolve, RegistryError
from ..rbridge import call_gl
from ..provenance import record

def run_relatedness(session_id: str, rds: str, iseed: int = 42, inbreed: bool = False,
                    dry_run: bool = False) -> dict:
    """Estimate pairwise relatedness with EMIBD9 (Wang 2022) via gl.run.EMIBD9 (dartR.captive).

    Input is a genlight RDS; returns a square pairwise relatedness matrix as `relatedness.csv`
    (deterministic given `iseed`). Note: EMIBD9 truncates individual IDs to 20 characters and
    forbids spaces / '/', so keep sample IDs short and unique.
    """
    wd = workdir(session_id)
    rin = resolve_input(rds, wd)
    try:
        emibd9_path = str(resolve("emibd9").parent)
    except RegistryError:
        emibd9_path = str(settings().programs_dir)
    params = {"rds": str(rin), "emibd9_path": emibd9_path,
              "iseed": iseed, "inbreed": inbreed}
    res = call_gl("gl.run.EMIBD9", params, wd, dry_run=dry_run)
    if dry_run:
        return res
    record(wd, "run_relatedness", {"rds": str(rin), "iseed": iseed, "inbreed": inbreed},
           [rin], [wd / o for o in res["outputs"]], 0)
    return res
