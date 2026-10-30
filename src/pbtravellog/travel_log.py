"""Manages records from the overall Travel Log data file.

Some record types involve multiple types of travel, and those types
should be defined here.
"""

# Standard imports
from datetime import date
from typing import Self

# Project imports
from pbtravellog.record import Record, RecordLayerTable

TRAVEL_DATA_FILE_ENV = "PBTRAVELLOG_TRAVEL_GEOPACKAGE_PATH"

class Trip(Record):
    """Represents a trip record."""
    LOG_TYPE = "travel"
    LAYER = "trips"
    FIND_BY_CODES = []
    DTYPES = {
        "fh_id": "Int64",
    }
    PARSE_DATES = ["start_date", "end_date"]

    @classmethod
    def select_by_date(cls, departure_date: date) -> Self | None:
        """
        Selects a trip based on departure date.

        The date provided should be the flight departure date from a
        boarding pass.
        """
        trips = TripTable.from_all()
        trips = [
            t for t in trips.values()
            if t["start_date"] is not None and t["end_date"] is not None
            and t["start_date"] <= departure_date <= t["end_date"]
        ]
        if len(trips) == 0:
            print(f"{departure_date} does not fall within any existing trip.")
            return None
        trips = sorted(trips, key=lambda x: (x["start_date"], x["end_date"]))
        return trips[-1]

class TripTable(RecordLayerTable):
    """Represents a dict of Trip instances."""
    RECORD_CLASS = Trip

    @classmethod
    def from_all(cls):
        """Creates a table of trips."""

        rec_table = super().from_all().sort("end_date").sort("start_date")
        for idx, (_, v) in enumerate(rec_table.items()):
            v["order"] = idx + 1
        return cls(rec_table)
