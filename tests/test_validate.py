"""Tests validate module."""

# Standard imports
from datetime import date, datetime, timezone

# Third-party imports
from shapely.geometry import MultiLineString

# Project imports
from pbtravellog import flight_log as fl, travel_log as tl, validate

def test_validate_trip_dates(sample_record):
    """Tests validation of travel dates being within trip dates."""
    trip = tl.Trip({
        "start_date": date(2024, 9, 22),
        "end_date": date(2024, 9, 27),
    })
    airport_kdfw = sample_record(fl.Airport, "airport_kdfw")
    airport_klas = sample_record(fl.Airport, "airport_klas")
    flights = [
        fl.Flight({
            "departure_utc": datetime(2024, 9, day, 12, tzinfo=timezone.utc),
            "arrival_utc": datetime(2024, 9, day, 13, tzinfo=timezone.utc),
            "origin_airport": airport_kdfw,
            "destination_airport": airport_klas,
            "trip": trip,
            "trip_fid": 1,
        })
        for day in [20, 24, 29] # Too early, valid, too late
    ]
    flights = fl.FlightTable(dict(enumerate(flights)))
    v = validate.ValidateTripDates(flights=flights)
    v.run()
    # Too early and too late flights each have arrival and departure out
    # of range, so they should generate two warnings each.
    assert len(v.warnings) == 4

def test_validate_flight_altitudes():
    """Tests validation of flight altitude units."""
    flights = fl.FlightTable(dict(enumerate([
        fl.Flight({"geometry": MultiLineString([[[0, 0, alt], [1, 1, alt]]])})
        for alt in [300, 9000] # Wrong units, valid units
    ])))
    v = validate.ValidateFlightAltitudes(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_distances():
    """Tests validation of flights having 0 distance."""
    flights = fl.FlightTable(dict(enumerate([
        fl.Flight({"distance_mi": dist})
        for dist in [0, 2000, 13000] # Zero, Valid, Too Long
    ])))
    v = validate.ValidateFlightDistances(flights=flights)
    v.run()
    # Zero and Too Long should each give a warning
    assert len(v.warnings) == 2

def test_validate_flight_distances_too_fast():
    """Tests validation of flights having too fast of a speed."""
    flights = fl.FlightTable(dict(enumerate([
        fl.Flight({
            "departure_utc": datetime(2024, 9, 22, 12, tzinfo=timezone.utc),
            "arrival_utc": datetime(2024, 9, 22, 13, tzinfo=timezone.utc),
            "distance_mi": dist,
        })
        for dist in [500, 1500] # 500 mph (valid), 1500 mph (too fast)
    ])))
    v = validate.ValidateFlightDistances(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_overlaps():
    """Tests validation of no flight overlaps."""
    times = [
        ( # Overlaps next flight times
            datetime(2024, 9, 22, 12, tzinfo=timezone.utc),
            datetime(2024, 9, 22, 18, tzinfo=timezone.utc),
        ),
        ( # Overlaps previous flight times
            datetime(2024, 9, 22, 15, tzinfo=timezone.utc),
            datetime(2024, 9, 22, 21, tzinfo=timezone.utc),
        ),
        ( # Does not overlap
            datetime(2024, 9, 22, 22, tzinfo=timezone.utc),
            datetime(2024, 9, 22, 23, tzinfo=timezone.utc),
        ),
    ]
    flights = fl.FlightTable(dict(enumerate([
        fl.Flight({"departure_utc": t[0], "arrival_utc": t[1]})
        for t in times
    ])))
    v = validate.ValidateFlightOverlaps(flights=flights)
    v.run()
    assert len(v.warnings) == 1

def test_validate_flight_times():
    """Tests validation of flights having flight times."""
    times = [
        (None, None), # No departure or arrival
        ( # Valid departure and arrival
            datetime(2024, 9, 22, 14, tzinfo=timezone.utc),
            datetime(2024, 9, 22, 15, tzinfo=timezone.utc),
        ),
    ]
    flights = fl.FlightTable(dict(enumerate([
        fl.Flight({"departure_utc": t[0], "arrival_utc": t[1]})
        for t in times
    ])))
    v = validate.ValidateFlightTimes(flights=flights)
    v.run()
    assert len(v.warnings) == 2

def test_validate_layover_length():
    """Tests validation of reasonable layovers."""
    times = [
        ( # Flight before too-long layover
            datetime(2024, 9, 22, 12, tzinfo=timezone.utc),
            datetime(2024, 9, 22, 13, tzinfo=timezone.utc),
        ),
        ( # Flight after too-long layover, and before valid layover
            datetime(2024, 9, 23, 12, tzinfo=timezone.utc),
            datetime(2024, 9, 23, 13, tzinfo=timezone.utc),
        ),
        ( # Flight after valid layover
            datetime(2024, 9, 23, 14, tzinfo=timezone.utc),
            datetime(2024, 9, 23, 15, tzinfo=timezone.utc),
        ),
    ]
    flights = fl.FlightTable(dict(enumerate([
        fl.Flight({
            "departure_utc": t[0],
            "arrival_utc": t[1],
            "trip_fid": 1,
            "trip_section": 1,
        })
        for t in times
    ])))
    v = validate.ValidateLayoverLength(flights=flights)
    v.run()
    assert len(v.warnings) == 1
