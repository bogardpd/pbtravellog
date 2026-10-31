"""Tests AeroAPI import functionality."""
# Standard imports
from datetime import datetime, timezone
from importlib.resources import files
import io
import json
from pathlib import Path
import requests
import shutil

# Third-party imports
import pytest
from pytest import approx

# Project imports
from pbtravellog.aeroapi import AeroAPIRateLimiter
from pbtravellog.boarding_pass import Leg
from pbtravellog.flight_log import (
    AircraftType, Airline, Airport, FlightTable,
    import_flight_bcbp, import_flight_fa_flight_id, import_flight_number,
    import_flight_pkpasses,
)
from pbtravellog.travel_log import Trip

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

@pytest.fixture(name="setup_aeroapi_mocking")
def fixture_setup_aeroapi_mocking(monkeypatch):
    """Mock AeroAPI responses."""
    def mock_get(*args, **_kwargs):
        provided_url = args[0]
        mocks = {
            "https://aeroapi.flightaware.com/aeroapi/flights/AA777": \
                "aeroapi/get_flights_ident_response.json",
            "https://aeroapi.flightaware.com/aeroapi/flights/AAL777": \
                "aeroapi/get_flights_ident_response.json",
            "https://aeroapi.flightaware.com/aeroapi/flights/AAL777-1792303609-airline-766p": \
                "aeroapi/get_flights_ident_fa_flight_id_response.json",
            "https://aeroapi.flightaware.com/aeroapi/flights/AAL777-1792303609-airline-766p/track": \
                "aeroapi/get_flights_ident_track_response.json",
        }
        return MockResponse(mocks[provided_url])
    def mock_date(*_args, **_kwargs):
        return datetime(2024, 9, 22, 20, 0, 0, tzinfo=timezone.utc)
    def zero_wait(*_args, **_kwargs):
        """Skips API rate limiter wait."""
        return
    monkeypatch.setenv("AEROAPI_API_KEY", "invalid_key")
    monkeypatch.setattr(AeroAPIRateLimiter, "wait", zero_wait)
    monkeypatch.setattr(Leg, "_now", mock_date)
    monkeypatch.setattr(requests, "get", mock_get)

@pytest.fixture(name="select_flight")
def fixture_select_flight(monkeypatch):
    """Selects a flight from the CLI."""
    # Always select result 6 from the list of flights:
    monkeypatch.setattr("sys.stdin", io.StringIO("6\n"))

@pytest.fixture(name="populate_geopackages")
def fixture_populate_geopackages(setup_empty_geopackages, sample_record):
    """Adds some sample data to travel log GeoPackages."""
    sample_record(Airline, "airline_aal").save()
    sample_record(Airport, "airport_kdfw").save()
    sample_record(Airport, "airport_klas").save()
    sample_record(AircraftType, "aircraft_type_a321").save()
    sample_record(Trip, "trip_las_vegas").save()

def test_import_flight_bcbp_blank_db(
    setup_empty_geopackages, setup_aeroapi_mocking, select_flight, bcbp_data,
):
    """
    Tests importing a flight with no airline, airport, aircraft type, or
    trip data available to look up.
    """
    flight_bcbp = bcbp_data("aa777.txt")
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

def test_import_flight_bcbp(
    populate_geopackages, setup_aeroapi_mocking, select_flight, bcbp_data
):
    """Tests importing a flight from BCBP data."""
    flight_bcbp = bcbp_data("aa777.txt")
    import_flight_bcbp(flight_bcbp)
    flights = FlightTable.from_all().joined()
    assert len(flights) == 1
    flight = flights[list(flights)[-1]]
    assert flight["airline"]["icao_code"] == "AAL"
    assert flight["operator"]["icao_code"] == "AAL"
    assert flight["origin_airport"]["icao_code"] == "KDFW"
    assert flight["destination_airport"]["icao_code"] == "KLAS"
    assert flight["aircraft_type"]["icao_code"] == "A321"
    assert flight["trip"]["name"] == "Las Vegas, NV"
    assert flight["trip_section"] == 1
    assert flight["boarding_pass_data"] == flight_bcbp

def test_import_fa_flight_id(
    populate_geopackages, setup_aeroapi_mocking
):
    """Tests importing a flight from an AeroAPI fa_flight_id"""
    fa_flight_id = "AAL777-1792303609-airline-766p"
    import_flight_fa_flight_id(fa_flight_id)
    flights = FlightTable.from_all().joined()
    assert len(flights) == 1
    flight = flights[list(flights)[-1]]
    assert flight["airline_fid"] is None
    assert flight["operator"]["icao_code"] == "AAL"
    assert flight["origin_airport"]["icao_code"] == "KDFW"
    assert flight["destination_airport"]["icao_code"] == "KLAS"
    assert flight["aircraft_type"]["icao_code"] == "A321"
    assert flight["trip"]["name"] == "Las Vegas, NV"
    assert flight["trip_section"] == 1
    assert flight["boarding_pass_data"] is None

def test_import_flight_number(
    populate_geopackages, setup_aeroapi_mocking, select_flight
):
    """Tests importing a flight from a flight number."""
    import_flight_number("AAL", "777")
    flights = FlightTable.from_all().joined()
    assert len(flights) == 1
    flight = flights[list(flights)[-1]]
    assert flight["airline"]["icao_code"] == "AAL"
    assert flight["operator"]["icao_code"] == "AAL"
    assert flight["origin_airport"]["icao_code"] == "KDFW"
    assert flight["destination_airport"]["icao_code"] == "KLAS"
    assert flight["aircraft_type"]["icao_code"] == "A321"
    assert flight["trip"]["name"] == "Las Vegas, NV"
    assert flight["trip_section"] == 1
    assert flight["boarding_pass_data"] is None

def test_import_flight_pkpasses(
    monkeypatch, tmp_path, populate_geopackages, setup_aeroapi_mocking,
    select_flight, bcbp_data,
):
    """Tests importing flights from PKPasses."""
    # Set up folders.
    folders = [
        ("import", "PBTRAVELLOG_FLIGHT_IMPORT_PATH"),
        ("archive", "PBTRAVELLOG_PKPASS_ARCHIVE_PATH"),
    ]
    tmp_folders = {}
    for name, env in folders:
        tmp_folders[name] = tmp_path / name
        tmp_folders[name].mkdir()
        monkeypatch.setenv(env, str(tmp_folders[name]))
    imp_file = tmp_folders["import"] / "aa777.pkpass"
    arch_file = tmp_folders["archive"] / "20240922T2057Z_AA_777_DFW-LAS.pkpass"
    shutil.copy(
        files("tests.fixtures.pkpass").joinpath("aa777.pkpass"),
        imp_file,
    )
    # Run function and check results.
    import_flight_pkpasses()
    flights = FlightTable.from_all().joined()
    assert len(flights) == 1
    flight = flights[list(flights)[-1]]
    assert flight["airline"]["icao_code"] == "AAL"
    assert flight["operator"]["icao_code"] == "AAL"
    assert flight["origin_airport"]["icao_code"] == "KDFW"
    assert flight["destination_airport"]["icao_code"] == "KLAS"
    assert flight["aircraft_type"]["icao_code"] == "A321"
    assert flight["trip"]["name"] == "Las Vegas, NV"
    assert flight["trip_section"] == 1
    assert flight["boarding_pass_data"] == bcbp_data("aa777.txt")
    # Verify pass was moved from import to archive.
    assert not imp_file.exists()
    assert arch_file.exists()
