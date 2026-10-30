"""Tests record module."""

# Project imports
from pbtravellog.flight_log import Airport, AirportTable

def test_record_table_find_by_code(setup_empty_geopackages, sample_record):
    """Tests RecordTable.find_by_code()"""
    # The current Denver International and the old Denver Stapleton both
    # share the same codes. find_by_code() should return Denver
    # International since it is not defunct.
    sample_record(Airport, "airport_kden_defunct").save()
    sample_record(Airport, "airport_kden").save()
    airport_kden = AirportTable.find_by_code("KDEN")
    assert airport_kden["name"] == "Denver (International)"
    # A code that matches no airport should return None.
    airport_no_matching = AirportTable.find_by_code("ZZZ")
    assert airport_no_matching is None
