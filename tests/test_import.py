import os
from pathlib import Path

def test_import_flight(monkeypatch, tmp_path):
    tmp_flight_gpkg = tmp_path / "flight_log.gpkg"
    monkeypatch.setenv(
        "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH",
        str(tmp_flight_gpkg),
    )
    env_flight_gpkg = Path(os.getenv("PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH"))
    assert tmp_flight_gpkg.resolve() == env_flight_gpkg.resolve()
