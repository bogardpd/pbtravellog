"""Tests browser module."""

# Third-party imports
import pytest
from shapely.geometry import Point

# Project imports
from pbtravellog.browser import create_browser_app
from pbtravellog.flight_log import (
    AircraftType, Airline, Airport, Flight, SeatClass
)
from pbtravellog.travel_log import Trip

@pytest.fixture(name="setup_sample_data")
def fixture_setup_sample_data(setup_empty_geopackages, sample_record):
    """Sets up sample data."""
    sample_record(Trip, "trip_las_vegas").save()
    sample_record(AircraftType, "aircraft_type_a321").save()
    sample_record(Airline, "airline_aal").save()
    airport_kdfw = sample_record(Airport, "airport_kdfw")
    airport_kdfw["geometry"] = Point(-97.0380, 32.8969)
    airport_kdfw.save()
    airport_klas = sample_record(Airport, "airport_klas")
    airport_klas["geometry"] = Point(-115.1522, 36.0800)
    airport_klas.save()
    sample_record(SeatClass, "seat_class_economy").save()
    sample_record(Flight, "flight_aal_777").save()

@pytest.fixture(name="client")
def fixture_client():
    """Represents a Flask client."""
    app = create_browser_app()
    app.config["TESTING"] = True
    return app.test_client()

def test_flask_routes_return_200(setup_sample_data, client):
    """Checks that flask routes return a response code of 200 OK."""
    # Deliberately using multiple assertions instead of parametrize
    # as we want all the tests to read the same set of sample data,
    # rather than reinitializing the data every time.
    assert client.get("/").status_code == 200
    assert client.get("/milestones/").status_code == 200
    assert client.get("/trips/").status_code == 200
    assert client.get("/trips/1/").status_code == 200
    assert client.get("/years/").status_code == 200
    assert client.get("/years/2024/").status_code == 200
    assert client.get("/flights/").status_code == 200
    assert client.get("/flights/1/").status_code == 200
    assert client.get("/aircraft_types/").status_code == 200
    assert client.get("/aircraft_types/1/").status_code == 200
    assert client.get("/airlines/").status_code == 200
    assert client.get("/airlines/1/").status_code == 200
    assert client.get("/airlines/operators/1/").status_code == 200
    assert client.get("/airports/").status_code == 200
    assert client.get("/airports/1/").status_code == 200
    assert client.get("/classes/").status_code == 200
    assert client.get("/classes/1/").status_code == 200
    assert client.get("/routes/").status_code == 200
    assert client.get("/routes/1/2/").status_code == 200
    assert client.get("/routes/2/1/").status_code == 200
    assert client.get("/tail_numbers/").status_code == 200
    assert client.get("/tail_numbers/N159AN/").status_code == 200
