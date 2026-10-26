"""Common fixtures."""
# Standard imports
from importlib.resources import files
from pathlib import Path
import tomllib

# Third-party imports
import pytest

@pytest.fixture()
def bcbp_data():
    """Reads a BCBP fixture from the fixtures folder."""
    def _get_bcbp(filename: str) -> str:
        data_path = files("tests.fixtures").joinpath(filename)
        return data_path.read_text(encoding="utf-8").strip()
    return _get_bcbp

@pytest.fixture()
def sample_record():
    """Gets sample record data."""
    def _get_data(record_class, record_name) -> dict:
        data_path = files("tests.fixtures").joinpath("sample_records.toml")
        with open(data_path, "rb") as f:
            samples = tomllib.load(f)
        return record_class(samples[record_class.__name__][record_name])
    return _get_data
