"""Manages records from the overall Travel Log data file.

Some record types involve multiple types of travel, and those types
should be defined here.
"""

# Standard imports
from datetime import date
import os
from typing import Self

# Third-party imports
import geopandas as gpd

# Project imports
from pbtravellog.record import Record, RecordLayerTable

TRAVEL_DATA_FILE_ENV = "PBTRAVELLOG_TRAVEL_GEOPACKAGE_PATH"

class Trip(Record):
    """Represents a trip record."""
    DATA_FILE_ENV = TRAVEL_DATA_FILE_ENV
    LAYER = "trips"
    FIND_BY_CODES = []
    DTYPES = {"fh_id": "Int64"}

    @classmethod
    def select_by_date(cls, departure_date: date) -> Self | None:
        """
        Selects a trip based on departure date.

        The date provided should be the flight departure date from a
        boarding pass.
        """
        records = gpd.read_file(
            cls.data_file(),
            layer=cls.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).dropna(subset=["start_date", "end_date"]).astype(cls.DTYPES)

        matching = records[
            (records["start_date"].dt.date <= departure_date)
            & (records["end_date"].dt.date >= departure_date)
        ].sort_values(by=["start_date", "end_date"], ascending=False)
        if matching.size == 0:
            print(f"{departure_date} does not fall within any existing trip.")
            return None
        record_dict = matching.iloc[0].to_dict()
        record_dict["fid"] = int(matching.index[0])
        record = cls()
        for k, v in record_dict.items():
            setattr(
                record,
                k,
                v.date() if hasattr(v, "date") else v
            )
        return record

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
