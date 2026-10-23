import io
import json
import os
import requests
from pathlib import Path
from pbtravellog.flight_log import import_flight_bcbp

class MockResponse(requests.Response):
    def __init__(self, filename: str):
        self.response_path = Path(__file__).parent / "fixtures" / filename
        self.status_code = 200
        self.reason = "OK"
        self.url = self.response_path

    def json(self) -> dict:
        with open(self.response_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

def test_import_flight_bcbp(bcbp_data, monkeypatch, tmp_path):
    tmp_flight_gpkg = tmp_path / "flight_log.gpkg"
    def mock_get(*args, **kwargs):
        provided_url = args[0]
        mocks = {
            "https://aeroapi.flightaware.com/aeroapi/flights/AAL777": (
                "aeroapi_get_flights_ident_response.json"
            ),
            "https://aeroapi.flightaware.com/aeroapi/flights/AAL777-1792303609-airline-766p/track": (
                "aeroapi_get_flights_ident_track_response.json"
            )
        }
        return MockResponse(mocks[provided_url])
    monkeypatch.setenv(
        "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH", str(tmp_flight_gpkg)
    )
    monkeypatch.setenv("AEROAPI_API_KEY", "invalid_key")
    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr("sys.stdin", io.StringIO("6\n"))
    env_flight_gpkg = Path(os.getenv("PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH"))
    flight_bcbp = bcbp_data("bcbp_import.txt")
    import_flight_bcbp(flight_bcbp)
    assert tmp_flight_gpkg.resolve() == env_flight_gpkg.resolve()