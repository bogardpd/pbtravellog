"""Common fixtures."""
# Standard imports
from importlib.resources import files
import tomllib

# Third-party imports
import pytest

# Project imports
from pbtravellog.record import init_gpkg

@pytest.fixture(name="bcbp_data")
def fixture_bcbp_data():
    """Reads sample BCBP data from the fixtures folder."""
    def _get_bcbp(filename: str) -> str:
        data_path = files("tests.fixtures.bcbp").joinpath(filename)
        return data_path.read_text(encoding="utf-8").strip()
    return _get_bcbp

@pytest.fixture(name="sample_record")
def fixture_sample_record():
    """Gets sample record data."""
    def _get_data(record_class, record_name) -> dict:
        data_path = files("tests.fixtures").joinpath("sample_records.toml")
        with open(data_path, "rb") as f:
            samples = tomllib.load(f)
        return record_class(samples[record_class.__name__][record_name])
    return _get_data

@pytest.fixture(name="setup_empty_geopackages")
def fixture_setup_empty_geopackages(monkeypatch, tmp_path):
    """Creates empty GeoPackage files for test use."""
    tmp_travel_gpkg = tmp_path / "travel_log.gpkg"
    tmp_flight_gpkg = tmp_path / "flight_log.gpkg"
    monkeypatch.setenv(
        "PBTRAVELLOG_TRAVEL_GEOPACKAGE_PATH", str(tmp_travel_gpkg)
    )
    monkeypatch.setenv(
        "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH", str(tmp_flight_gpkg)
    )
    init_gpkg()