from . import io, filter as _filter, report, admixture, relatedness, ne

# Tools that shell out to potentially long-running external binaries — the
# host should require explicit user confirmation before invoking these.
EXPENSIVE = {"run_admixture", "run_relatedness"}

def register_all(mcp) -> None:
    mcp.tool()(io.read_vcf)
    mcp.tool()(io.convert)
    mcp.tool()(_filter.filter_snps)
    mcp.tool()(report.report_diversity)
    mcp.tool()(report.report_fst)
    mcp.tool()(report.pcoa)
    mcp.tool()(admixture.run_admixture)
    mcp.tool()(relatedness.run_relatedness)
    mcp.tool()(ne.estimate_ne)
