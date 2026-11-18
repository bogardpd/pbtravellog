"""Tests validate module."""
from pbtravellog import flight_log, travel_log, validate

def test_validate_flight_overlaps(setup_empty_geopackages, sample_record):
    """Tests validation of no flight overlaps."""
    sample_record(flight_log.Flight, "flight_validate_overlapping_1").save()
    sample_record(flight_log.Flight, "flight_validate_overlapping_2").save()
    flights = flight_log.FlightTable.from_all().joined()
    v = validate.ValidateFlightOverlaps(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_times(setup_empty_geopackages, sample_record):
    """Tests validation of flights having flight times."""
    sample_record(flight_log.Flight, "flight_validate_no_utc").save()
    flights = flight_log.FlightTable.from_all().joined()
    v = validate.ValidateFlightTimes(flights=flights)
    v.run()
    assert len(v.warnings) == 2

def test_validate_layover_length(setup_empty_geopackages, sample_record):
    """Tests validation of reasonable layovers."""
    sample_record(travel_log.Trip, "trip_las_vegas").save()
    sample_record(flight_log.Flight, "flight_validate_long_layover_1").save()
    sample_record(flight_log.Flight, "flight_validate_long_layover_2").save()
    sample_record(flight_log.Flight, "flight_validate_long_layover_3").save()
    flights = flight_log.FlightTable.from_all().joined()
    v = validate.ValidateLayoverLength(flights=flights)
    v.run()
    assert len(v.warnings) == 1
