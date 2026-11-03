"""Tests browser module."""

# Third-party imports
import pytest

# Project imports
from pbtravellog.browser import create_browser_app

@pytest.fixture(name="client")
def fixture_client():
    """Represents a Flask client."""
    app = create_browser_app()
    app.config["TESTING"] = True
    return app.test_client()

@pytest.mark.parametrize("flask_route", [
    "/",
    "/milestones/",
    "/trips/",
    "/years/",
    "/flights/",
    "/aircraft_types/",
    "/airlines/",
    "/airports/",
    "/classes/",
    "/routes/",
    "/tail_numbers/",
])

def test_flask_routes_return_200(client, flask_route):
    """Checks that flask routes return a response code of 200 OK."""
    response = client.get(flask_route)
    assert response.status_code == 200
