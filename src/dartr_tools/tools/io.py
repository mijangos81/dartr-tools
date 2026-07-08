from ..session import workdir
from ..sandbox import resolve_input, resolve_output
from ..rbridge import call_gl
from ..provenance import record
from ..config import settings

def read_vcf(session_id: str, vcf: str, metafile: str | None = None, out: str = "gl.rds") -> dict:
    """Load a VCF into a dartRverse genlight object (saved as .RDS).

    `metafile` (optional) assigns individuals to populations via
    `gl.read.vcf(ind.metafile=)`. Without it every individual collapses into
    a single `pop1`, which breaks downstream population-level analyses (e.g.
    Fst) — always pass one when population structure is known.
    """
    wd = workdir(session_id)
    vin = resolve_input(vcf, wd)
    resolve_output(out, wd)
    params = {"vcf": str(vin), "out": out}
    inputs = [vin]
    if metafile is not None:
        min_ = resolve_input(metafile, wd)
        params["metafile"] = str(min_)
        inputs.append(min_)
    res = call_gl("gl.read.vcf", params, wd)
    record(wd, "read_vcf", params, inputs, [wd / out], 0)
    return res

def convert(session_id: str, rds: str, fmt: str, out: str) -> dict:
    """Convert a genlight RDS to PLINK ('plink') or VCF ('vcf').

    The PLINK binary path is sourced server-side from `config.settings()` —
    never accepted from the agent — because it flows into a shell-out
    (`gl2vcf`'s `plink.bin.path`) inside the R runner.
    """
    wd = workdir(session_id)
    rin = resolve_input(rds, wd)
    resolve_output(out, wd)
    fn = {"plink": "gl2plink", "vcf": "gl2vcf"}.get(fmt)
    if fn is None:
        raise ValueError("fmt must be 'plink' or 'vcf'")
    params = {"rds": str(rin), "out": out}
    if fmt == "vcf":
        params["plink_path"] = str(settings().programs_dir)
    res = call_gl(fn, params, wd)
    record(wd, "convert", {"rds": str(rin), "fmt": fmt, "out": out}, [rin], [wd / o for o in res["outputs"]], 0)
    return res
