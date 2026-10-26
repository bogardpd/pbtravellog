"""Tests AeroAPI import functionality."""

import io
import json
from pathlib import Path
import requests

import pytest
from pytest import approx

from pbtravellog.flight_log import FlightTable, import_flight_bcbp
from pbtravellog.record import init_gpkg

class MockResponse(requests.Response):
    """Mocks API responses."""
    def __init__(self, filename: str):
        super().__init__()
        self.response_path = Path(__file__).parent / "fixtures" / filename
        self.status_code = 200
        self.reason = "OK"
        self.url = self.response_path

    def json(self, **kwargs) -> dict:
        """Returns a JSON response."""
        with open(self.response_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

@pytest.fixture(name="setup_empty_geopackages")
def fixture_setup_empty_geopackages(monkeypatch, tmp_path):
    """Creates empty GeoPackage files for test use."""
    tmp_travel_gpkg = tmp_path / "travel_log.gpkg"
    tmp_flight_gpkg = tmp_path / "flight_log.gpkg"
    def mock_get(*args, **_kwargs):
        provided_url = args[0]
        mocks = {
            "https://aeroapi.flightaware.com/aeroapi/flights/AA777": (
                "aeroapi_get_flights_ident_response.json"
            ),
            "https://aeroapi.flightaware.com/aeroapi/flights/AAL777-1792303609-airline-766p/track": (
                "aeroapi_get_flights_ident_track_response.json"
            )
        }
        return MockResponse(mocks[provided_url])
    monkeypatch.setenv(
        "PBTRAVELLOG_TRAVEL_GEOPACKAGE_PATH", str(tmp_travel_gpkg)
    )
    monkeypatch.setenv(
        "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH", str(tmp_flight_gpkg)
    )
    monkeypatch.setenv("AEROAPI_API_KEY", "invalid_key")
    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr("sys.stdin", io.StringIO("6\n"))
    init_gpkg()

@pytest.fixture(name="populate_geopackages")
def fixture_populate_geopackages(setup_empty_geopackages):
    """Adds some sample data to travel log GeoPackages."""
    # TODO: Implement

def test_import_flight_bcbp_blank_db(setup_empty_geopackages, bcbp_data):
    """
    Tests importing a flight with no airline, airport, aircraft type, or
    trip data available to look up.
    """
    flight_bcbp = bcbp_data("bcbp_import.txt")
    import_flight_bcbp(flight_bcbp)

    # Check results.
    flights = FlightTable.from_all()
    assert len(flights) == 1
    flight = flights[list(flights)[-1]]
    assert flight["airline_fid"] is None
    assert flight["operator_fid"] is None
    assert flight["origin_airport_fid"] is None
    assert flight["destination_airport_fid"] is None
    assert flight["aircraft_type_fid"] is None
    assert flight["trip_fid"] is None
    assert flight["flight_number"] == "777"
    assert flight["fa_flight_id"] == "AAL777-1792303609-airline-766p"
    assert flight["geom_source"] == "FlightAware"
    assert flight["geometry"].geoms[0].coords[0] == approx((
        -97.03544, 32.89897, 0.0
    ))

def test_import_flight_bcbp(populate_geopackages):
    """Tests importing a flight via BCBP data."""
    # TODO: Implement
