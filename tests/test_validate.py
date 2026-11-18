"""Tests validate module."""
from pbtravellog import flight_log as fl, travel_log as tl, validate

def test_validate_flight_distances_zero_distance(
    setup_empty_geopackages, sample_record
):
    """Tests validation of flights having 0 distance."""
    sample_record(fl.Flight, "flight_validate_distance_zero").save()
    sample_record(fl.Flight, "flight_validate_distance_valid").save()
    flights = fl.FlightTable.from_all().joined()
    v = validate.ValidateFlightDistances(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_distances_too_long(
    setup_empty_geopackages, sample_record
):
    """Tests validation of flights having too long of a distance."""
    sample_record(fl.Flight, "flight_validate_distance_too_long").save()
    sample_record(fl.Flight, "flight_validate_distance_valid").save()
    flights = fl.FlightTable.from_all().joined()
    v = validate.ValidateFlightDistances(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_distances_too_fast(
    setup_empty_geopackages, sample_record
):
    """Tests validation of flights having too fast of a speed."""
    sample_record(fl.Flight, "flight_validate_distance_too_fast").save()
    sample_record(fl.Flight, "flight_validate_distance_valid").save()
    flights = fl.FlightTable.from_all().joined()
    v = validate.ValidateFlightDistances(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_overlaps(setup_empty_geopackages, sample_record):
    """Tests validation of no flight overlaps."""
    sample_record(fl.Flight, "flight_validate_overlapping_1").save()
    sample_record(fl.Flight, "flight_validate_overlapping_2").save()
    sample_record(fl.Flight, "flight_validate_overlapping_3_valid").save()
    flights = fl.FlightTable.from_all().joined()
    v = validate.ValidateFlightOverlaps(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_times(setup_empty_geopackages, sample_record):
    """Tests validation of flights having flight times."""
    sample_record(fl.Flight, "flight_validate_times_no_utc").save()
    sample_record(fl.Flight, "flight_validate_times_valid").save()
    flights = fl.FlightTable.from_all().joined()
    v = validate.ValidateFlightTimes(flights=flights)
    v.run()
    assert len(v.warnings) == 2

def test_validate_layover_length(setup_empty_geopackages, sample_record):
    """Tests validation of reasonable layovers."""
    sample_record(tl.Trip, "trip_las_vegas").save()
    sample_record(fl.Flight, "flight_validate_long_layover_1").save()
    sample_record(fl.Flight, "flight_validate_long_layover_2").save()
    sample_record(fl.Flight, "flight_validate_long_layover_3_valid").save()
    flights = fl.FlightTable.from_all().joined()
    v = validate.ValidateLayoverLength(flights=flights)
    v.run()
    assert len(v.warnings) == 1
