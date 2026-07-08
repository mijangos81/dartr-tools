from importlib.metadata import version, PackageNotFoundError
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dartr-tools")

def _version() -> str:
    try:
        return version("dartr-tools")
    except PackageNotFoundError:
        return "0.0.0-dev"

@mcp.tool()
def status() -> dict:
    """Report server name, version, and number of registered tools."""
    return {"name": "dartr-tools", "version": _version(), "tools": len(mcp._tool_manager.list_tools())}

from . import tools
tools.register_all(mcp)

def main() -> None:
    mcp.run()

if __name__ == "__main__":
    main()
