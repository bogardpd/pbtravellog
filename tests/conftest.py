"""Common fixtures."""
from pathlib import Path
import pytest

@pytest.fixture
def bcbp_data():
    """Reads a BCBP fixture from the fixtures folder."""
    def _get_bcbp(filename: str) -> str:
        data_path = Path(__file__).parent / "fixtures" / filename
        return data_path.read_text(encoding="utf-8").strip()
    return _get_bcbp