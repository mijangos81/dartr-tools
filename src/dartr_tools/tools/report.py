from ..session import workdir
from ..sandbox import resolve_input, resolve_output
from ..rbridge import call_gl
from ..provenance import record

def report_diversity(session_id: str, rds: str, out: str = "diversity.csv") -> dict:
    """Per-population heterozygosity / diversity report (CSV)."""
    wd = workdir(session_id); rin = resolve_input(rds, wd); resolve_output(out, wd)
    res = call_gl("gl.report.heterozygosity", {"rds": str(rin), "out": out}, wd)
    record(wd, "report_diversity", {"rds": str(rin), "out": out}, [rin], [wd / out], 0)
    return res

def report_fst(session_id: str, rds: str, out: str = "fst.rds") -> dict:
    """Pairwise Fst between populations (saved as .RDS)."""
    wd = workdir(session_id); rin = resolve_input(rds, wd); resolve_output(out, wd)
    res = call_gl("gl.fst.pop", {"rds": str(rin), "out": out}, wd)
    record(wd, "report_fst", {"rds": str(rin), "out": out}, [rin], [wd / out], 0)
    return res

def pcoa(session_id: str, rds: str, out_coords: str = "pcoa.rds", out_plot: str = "pcoa.png") -> dict:
    """Principal-coordinates ordination with a plot."""
    wd = workdir(session_id); rin = resolve_input(rds, wd)
    resolve_output(out_coords, wd); resolve_output(out_plot, wd)
    params = {"rds": str(rin), "out_coords": out_coords, "out_plot": out_plot}
    res = call_gl("gl.pcoa", params, wd)
    record(wd, "pcoa", params, [rin], [wd / out_coords, wd / out_plot], 0)
    return res
