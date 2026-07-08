import os, stat, pytest
from dartr_tools import registry

def test_known_names_present():
    assert {"admixture", "emibd9", "ne2"} <= set(registry.BINARIES)

def test_resolve_ok(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tmp_path))
    b = tmp_path / registry.BINARIES["admixture"]
    b.write_text("#!/bin/sh\n"); b.chmod(b.stat().st_mode | stat.S_IEXEC)
    assert registry.resolve("admixture") == b.resolve()

def test_resolve_unknown(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tmp_path))
    with pytest.raises(registry.RegistryError):
        registry.resolve("rm")

def test_resolve_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tmp_path))
    with pytest.raises(registry.RegistryError):
        registry.resolve("admixture")
