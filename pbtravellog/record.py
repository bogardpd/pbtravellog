"""Manages travel records."""

# Standard imports
from typing import Self
import re

# Third-party imports
import geopandas as gpd
import pandas as pd

class Record(dict):
    """Represents a generic record from any travel log table.

    Designed to be inherited by specific travel record types.
    """
    DATA_FILE = None
    LAYER = None
    FIND_BY_CODES = []
    DTYPES = {}

    @classmethod
    def every(cls) -> gpd.GeoDataFrame:
        """Returns a GeoDataFrame of all records."""
        records = gpd.read_file(
            cls.DATA_FILE,
            layer=cls.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).astype(cls.DTYPES)
        return records

    @classmethod
    def to_dict(cls) -> dict:
        """Returns a dictionary of all records."""
        records = cls.every().copy()
        records = records.astype(object).where(pd.notna(records), None)
        return records.to_dict(orient="index")

    @classmethod
    def find_by_code(cls, code: str, check_fid=False) -> Self | None:
        """Finds a record by searching through code fields."""
        if getattr(cls, "FIND_BY_CODES", None) is None:
            return None
        if len(cls.FIND_BY_CODES) == 0:
            return None
        records = gpd.read_file(
            cls.DATA_FILE,
            layer = cls.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        )

        # Check for fid on numeric codes. Note that this will allow
        # defunct records since fids are unique.
        if check_fid and re.search(r'^[0-9]+$', code):
            if int(code) in records.index:
                record_dict = records.loc[int(code)].to_dict()
                record_dict["fid"] = int(code)
                record = cls()
                for key, value in record_dict.items():
                    setattr(record, key, value)
                return record

        # Filter out defunct records. This is helpful in situations
        # where current records use the same codes as an old record
        # (for example, the current PSA airlines and the defunct Comair
        # both use the IATA code "OH".)
        if "is_defunct" in records.columns:
            records = records[~records["is_defunct"]]
        for code_type in cls.FIND_BY_CODES:
            # Search for matching codes.
            matching_code = records[records[code_type] == code]
            if len(matching_code) == 1:
                record_dict = matching_code.iloc[0].to_dict()
                record_dict["fid"] = int(matching_code.index[0])
                record = cls()
                for key, value in record_dict.items():
                    setattr(record, key, value)
                return record
        print(f"⚠️ Could not find {cls.__name__} matching \"{code}\".")
        return None
