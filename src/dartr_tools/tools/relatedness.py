from ..session import workdir
from ..sandbox import resolve_input
from ..registry import resolve
from ..config import settings
from ..executor import run_local, run_remote
from ..provenance import record

def run_relatedness(session_id: str, plink: str, heavy: bool = False) -> dict:
    """Estimate pairwise relatedness (EMIBD9) on a PLINK bfile prefix."""
    wd = workdir(session_id)
    # Sandbox-validate all three PLINK files (bed, bim, fam) so a path escape
    # via .bim/.fam can't bypass resolve_input's root check.
    bed = resolve_input(f"{plink}.bed", wd)
    bim = resolve_input(f"{plink}.bim", wd)
    fam = resolve_input(f"{plink}.fam", wd)
    # Always resolve the local binary: it's required for the local branch, and
    # doubles as an availability check even though the remote branch uses its
    # own copy on luism01's PATH (see below).
    binary = resolve("emibd9")
    if heavy:
        # run_remote executes on luism01 (Linux): stage_in rsyncs the local
        # absolute files into remote_cwd by basename, and the macOS binary
        # resolved above can't run there — so the remote argv must use the
        # bare binary name (resolved on the remote PATH) and basename inputs
        # relative to remote_cwd, not the local absolute paths.
        argv = ["EM_IBD_P", "--bfile", plink]
        r = run_remote(argv, remote_cwd=f"/mnt/local/output/{session_id}", host=settings().luism01_host,
                       stage_in=[bed, bim, fam],
                       stage_out_dir=wd, timeout=settings().remote_timeout)
    else:
        # run_local executes on this machine, so absolute local paths are correct.
        argv = [str(binary), "--bfile", str(wd / plink)]
        r = run_local(argv, cwd=wd, timeout=settings().local_timeout)
    outputs = ["relatedness.out"]
    record(wd, "run_relatedness", {"plink": plink, "heavy": heavy}, [bed, bim, fam], [wd / o for o in outputs], 0)
    return {"outputs": outputs}
