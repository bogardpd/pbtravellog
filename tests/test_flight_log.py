"""Tests flight_log module."""

# Project imports
from pbtravellog.flight_log import Flight

def test_flight_alert_prior_flown_tail(setup_empty_geopackages, sample_record):
    """Tests counting flights on same tail number."""
    flight1 = sample_record(Flight, "flight_same_tail")
    flight1.save()
    assert flight1.alert_prior_flown_tail() == 1
    flight2 = sample_record(Flight, "flight_same_tail")
    flight2.save()
    assert flight2.alert_prior_flown_tail() == 2
