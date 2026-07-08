import re
from ..session import workdir
from ..sandbox import resolve_input, bounded
from ..registry import resolve
from ..config import settings
from ..executor import run_local, run_remote
from ..provenance import record

_CV = re.compile(r"CV error \(K=(\d+)\):\s*([0-9.]+)")

def run_admixture(session_id: str, plink: str, k_min: int = 2, k_max: int = 6,
                  heavy: bool = False, snp_threshold: int = 200_000, dry_run: bool = False) -> dict:
    """Run ADMIXTURE with cross-validation across a K range on a PLINK bfile prefix."""
    wd = workdir(session_id)
    bounded(k_min, 1, 20, "k_min"); bounded(k_max, k_min, 20, "k_max")
    # Sandbox-validate all three PLINK files (not just .bed) so a path escape
    # via .bim/.fam can't bypass resolve_input's root check.
    bed = resolve_input(f"{plink}.bed", wd)
    bim = resolve_input(f"{plink}.bim", wd)
    fam = resolve_input(f"{plink}.fam", wd)
    with bim.open() as fh:
        nsnp = sum(1 for _ in fh)
    # Always resolve the local binary: it's required for the local branch, and
    # doubles as an availability check even though the remote branch uses its
    # own copy on luism01's PATH (see below).
    binary = resolve("admixture")
    remote = heavy or nsnp > snp_threshold
    if dry_run:
        dry_cmds = []
        for k in range(k_min, k_max + 1):
            if remote:
                argv_remote = ["admixture", "--cv", f"{plink}.bed", str(k)]
                r = run_remote(argv_remote, remote_cwd=f"/mnt/local/output/{session_id}", host=settings().luism01_host,
                               stage_in=[bed, bim, fam],
                               stage_out_dir=wd, timeout=settings().remote_timeout, dry_run=True)
            else:
                argv_local = [str(binary), "--cv", str(bed), str(k)]
                r = run_local(argv_local, cwd=wd, timeout=settings().local_timeout, dry_run=True)
            dry_cmds.append(r.stdout)
        return {"dry_run": dry_cmds, "outputs": []}
    cv, outputs = {}, []
    for k in range(k_min, k_max + 1):
        if remote:
            # run_remote executes on luism01 (Linux): stage_in rsyncs the local
            # absolute files into remote_cwd by basename, and the macOS binary
            # resolved above can't run there — so the remote argv must use the
            # bare binary name (resolved on the remote PATH) and basename inputs
            # relative to remote_cwd, not the local absolute paths.
            argv_remote = ["admixture", "--cv", f"{plink}.bed", str(k)]
            r = run_remote(argv_remote, remote_cwd=f"/mnt/local/output/{session_id}", host=settings().luism01_host,
                           stage_in=[bed, bim, fam],
                           stage_out_dir=wd, timeout=settings().remote_timeout)
        else:
            # run_local executes on this machine, so absolute local paths are correct.
            argv_local = [str(binary), "--cv", str(bed), str(k)]
            r = run_local(argv_local, cwd=wd, timeout=settings().local_timeout)
        m = _CV.search(r.stdout)
        if m:
            cv[int(m.group(1))] = float(m.group(2))
        outputs += [f"{plink}.{k}.Q", f"{plink}.{k}.P"]
    record(wd, "run_admixture", {"plink": plink, "k_min": k_min, "k_max": k_max, "remote": remote},
           [bed, bim, fam], [wd / o for o in outputs], 0)
    return {"outputs": outputs, "cv": cv}
