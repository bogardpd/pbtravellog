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
from pbtravellog.record import Record

TRAVEL_LOG = os.getenv("PBTRAVELLOG_TRAVEL_GEOPACKAGE_PATH")
if TRAVEL_LOG is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_TRAVEL_GEOPACKAGE_PATH is missing."
    )

class Trip(Record):
    """Represents a trip record."""
    DATA_FILE = TRAVEL_LOG
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
            cls.DATA_FILE,
            layer=cls.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).dropna(subset=["start_date", "end_date"]).astype(cls.DTYPES)

        matching = records[
            (records["start_date"].dt.date <= departure_date)
            & (records["end_date"].dt.date >= departure_date)
        ].sort_values(by=["start_date", "end_date"], ascending=False)
        if matching.size == 0:
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
