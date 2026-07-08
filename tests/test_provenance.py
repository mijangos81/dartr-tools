import json
from pathlib import Path
from dartr_tools import provenance

def test_appends_record(tmp_path):
    f = tmp_path / "in.txt"; f.write_text("abc")
    rec = provenance.record(tmp_path, "read_vcf", {"x": 1}, [f], [tmp_path / "out.rds"], 0)
    lines = (tmp_path / "provenance.jsonl").read_text().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["tool"] == "read_vcf" and parsed["exit_code"] == 0
    assert parsed["inputs"][0]["sha256"] and parsed["outputs"] == ["out.rds"]

def test_two_calls_append(tmp_path):
    provenance.record(tmp_path, "a", {}, [], [], 0)
    provenance.record(tmp_path, "b", {}, [], [], 0)
    assert len((tmp_path / "provenance.jsonl").read_text().splitlines()) == 2
