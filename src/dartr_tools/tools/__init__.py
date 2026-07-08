from . import io, filter as _filter

def register_all(mcp) -> None:
    mcp.tool()(io.read_vcf)
    mcp.tool()(io.convert)
    mcp.tool()(_filter.filter_snps)
