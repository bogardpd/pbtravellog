import os
from pathlib import Path
from pbtravellog.flight_log import import_flight_bcbp

def test_import_flight_bcbp(bcbp_data, monkeypatch, tmp_path):
    tmp_flight_gpkg = tmp_path / "flight_log.gpkg"
    monkeypatch.setenv(
        "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH", str(tmp_flight_gpkg)
    )
    monkeypatch.setenv("AEROAPI_API_KEY", "invalid_key")
    env_flight_gpkg = Path(os.getenv("PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH"))
    flight_bcbp = bcbp_data("bcbp_import.txt")
    import_flight_bcbp(flight_bcbp)
    assert tmp_flight_gpkg.resolve() == env_flight_gpkg.resolve()