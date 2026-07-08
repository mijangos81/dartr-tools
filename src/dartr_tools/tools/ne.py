from ..session import workdir
from ..sandbox import resolve_input
from ..registry import resolve, RegistryError
from ..rbridge import call_gl
from ..provenance import record

def estimate_ne(session_id: str, rds: str, dry_run: bool = False) -> dict:
    """Estimate effective population size (LD method) via gl.LDNe / NeEstimator."""
    wd = workdir(session_id); rin = resolve_input(rds, wd)
    try:
        # gl.LDNe's `neest.path` wants the DIRECTORY containing the NeEstimator
        # binary, not the binary file itself — pass the registry-pinned path's
        # parent. Sourced server-side only; never a tool-signature parameter.
        neest_path = str(resolve("ne2").parent)
    except RegistryError:
        neest_path = ""  # let dartRverse fall back to its own discovery
    params = {"rds": str(rin), "out": "ne", "neest_path": neest_path}
    res = call_gl("gl.LDNe", params, wd, dry_run=dry_run)
    if dry_run:
        return res
    record(wd, "estimate_ne", {"rds": str(rin), "neest_path": neest_path}, [rin], [wd / o for o in res["outputs"]], 0)
    return res
