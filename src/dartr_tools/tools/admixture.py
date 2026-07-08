import re
from pathlib import Path
from ..session import workdir
from ..sandbox import resolve_input, bounded
from ..registry import resolve
from ..config import settings
from ..executor import run_local, run_remote
from ..provenance import record

_CV = re.compile(r"CV error \(K=(\d+)\):\s*([0-9.]+)")

def run_admixture(session_id: str, plink: str, k_min: int = 2, k_max: int = 6,
                  heavy: bool = False, snp_threshold: int = 200_000) -> dict:
    """Run ADMIXTURE with cross-validation across a K range on a PLINK bfile prefix."""
    wd = workdir(session_id)
    bounded(k_min, 1, 20, "k_min"); bounded(k_max, k_min, 20, "k_max")
    bed = resolve_input(f"{plink}.bed", wd)
    nsnp = sum(1 for _ in (wd / f"{plink}.bim").open())
    binary = resolve("admixture")
    remote = heavy or nsnp > snp_threshold
    cv, outputs = {}, []
    for k in range(k_min, k_max + 1):
        argv = [str(binary), "--cv", str(bed), str(k)]
        if remote:
            r = run_remote(argv, remote_cwd=f"/mnt/local/output/{session_id}", host=settings().luism01_host,
                           stage_in=[wd / f"{plink}.{e}" for e in ("bed", "bim", "fam")],
                           stage_out_dir=wd, timeout=settings().remote_timeout)
        else:
            r = run_local(argv, cwd=wd, timeout=settings().local_timeout)
        m = _CV.search(r.stdout)
        if m:
            cv[int(m.group(1))] = float(m.group(2))
        outputs += [f"{plink}.{k}.Q", f"{plink}.{k}.P"]
    record(wd, "run_admixture", {"plink": plink, "k_min": k_min, "k_max": k_max, "remote": remote},
           [bed], [wd / o for o in outputs], 0)
    return {"outputs": outputs, "cv": cv}
