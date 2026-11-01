"""Tests flight_log module."""

# Standard imports
from datetime import datetime, timezone

# Project imports
from pbtravellog.flight_log import Flight, estimate_trip_section
from pbtravellog.travel_log import Trip, TripTable

def test_flight_alert_prior_flown_tail(setup_empty_geopackages, sample_record):
    """Tests counting flights on same tail number."""
    flight1 = sample_record(Flight, "flight_same_tail")
    flight1.save()
    assert flight1.alert_prior_flown_tail() == 1
    flight2 = sample_record(Flight, "flight_same_tail")
    flight2.save()
    assert flight2.alert_prior_flown_tail() == 2

def test_estimate_trip_section(setup_empty_geopackages, sample_record):
    """Tests behavior of estimate_trip_section."""
    trip = sample_record(Trip, "trip_las_vegas")
    trip.save()
    trip_fid = max(TripTable.from_all().keys())
    # The trip has no flights, so the trip section should be 1.
    assert estimate_trip_section(
        trip_fid,
        datetime(2024, 9, 22, 17, 0, 0, tzinfo=timezone.utc)
    ) == 1
    # Add a flight to this trip (departing 2023-09-22T17:00:00Z).
    flight_with_section = sample_record(Flight, "flight_trip_section")
    flight_with_section["trip_fid"] = trip_fid
    flight_with_section.save()
    # A flight earlier than the latest flight should return None.
    assert estimate_trip_section(
        trip_fid,
        datetime(2024, 9, 22, 16, 0, 0, tzinfo=timezone.utc)
    ) is None
    # A flight within 24 hours of the latest flight should return the
    # same trip section. A flight 24 hours or more after the latest
    # flight should return a new trip section.
    assert estimate_trip_section(
        trip_fid,
        datetime(2024, 9, 23, 16, 59, 59, tzinfo=timezone.utc)
    ) == 1
    assert estimate_trip_section(
        trip_fid,
        datetime(2024, 9, 23, 17, 00, 00, tzinfo=timezone.utc)
    ) == 2
    # Add a flight with no trip section. Now any estimate_trip_section
    # call should return None.
    flight_no_section = sample_record(Flight, "flight_trip_section_no_section")
    flight_no_section["trip_fid"] = trip_fid
    flight_no_section.save()
    assert estimate_trip_section(
        trip_fid,
        datetime(2024, 9, 22, 17, 0, 0, tzinfo=timezone.utc)
    ) is None
