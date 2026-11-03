"""Tests browser module."""

# Third-party imports
import pytest
from shapely.geometry import Point

# Project imports
from pbtravellog.browser import create_browser_app
from pbtravellog.flight_log import (
    AircraftType, Airline, Airport, Flight, SeatClass, SeatClassTable
)
from pbtravellog.travel_log import Trip

@pytest.fixture(name="client")
def fixture_client():
    """Represents a Flask client."""
    app = create_browser_app()
    app.config["TESTING"] = True
    return app.test_client()

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

@pytest.mark.parametrize("flask_route", [
    "/",
    "/milestones/",
    "/trips/",
    "/trips/1/",
    "/years/",
    "/years/2024/",
    "/flights/",
    "/flights/1/",
    "/aircraft_types/",
    "/aircraft_types/1/",
    "/airlines/",
    "/airlines/1/",
    "/airlines/operators/1/",
    "/airports/",
    "/airports/1/",
    "/classes/",
    "/classes/1/",
    "/routes/",
    "/routes/1/2/",
    "/tail_numbers/",
    "/tail_numbers/N159AN/",
])

def test_flask_routes_return_200(setup_sample_data, client, flask_route):
    """Checks that flask routes return a response code of 200 OK."""
    response = client.get(flask_route)
    assert response.status_code == 200
