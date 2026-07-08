import pytest
from pathlib import Path

@pytest.fixture
def tiny_vcf() -> Path:
    return Path(__file__).parent / "fixtures" / "tiny.vcf"

@pytest.fixture
def tiny_meta() -> Path:
    return Path(__file__).parent / "fixtures" / "tiny.csv"
