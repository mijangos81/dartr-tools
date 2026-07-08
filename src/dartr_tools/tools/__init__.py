from . import io, filter as _filter, report

def register_all(mcp) -> None:
    mcp.tool()(io.read_vcf)
    mcp.tool()(io.convert)
    mcp.tool()(_filter.filter_snps)
    mcp.tool()(report.report_diversity)
    mcp.tool()(report.report_fst)
    mcp.tool()(report.pcoa)
