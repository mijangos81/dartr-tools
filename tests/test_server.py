from dartr_tools import server

def test_status_tool_registered():
    names = {t.name for t in server.mcp._tool_manager.list_tools()}
    assert "status" in names

def test_status_returns_metadata():
    out = server.status()
    assert out["name"] == "dartr-tools"
    assert isinstance(out["version"], str) and out["version"]
    assert out["tools"] >= 1
