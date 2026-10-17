"""Manages travel records."""

# Standard imports
import csv
from pathlib import Path
import re
from typing import Self

# Third-party imports
import geopandas as gpd
import pandas as pd
from tabulate import tabulate

class Record(dict):
    """Represents a generic travel record.

    Designed to be inherited by specific travel object types.
    """
    DATA_FILE = None
    LAYER = None
    FIND_BY_CODES = []
    DTYPES = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fid: int | None = None

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
                record = cls.from_gpd_row(matching_code.iloc[0])
                return record
        print(f"⚠️ Could not find {cls.__name__} matching \"{code}\".")
        return None

    @classmethod
    def from_gpd_row(cls, row: pd.Series) -> Self:
        """Creates a class instance from a geopandas row."""
        record_row = row.copy().astype(object).where(pd.notna(row), None)
        record = cls(record_row.to_dict())
        record.fid = int(record_row.name)
        return record

class RecordTable(dict):
    """Represents a dict of instances of travel log records.

    Designed to be inherited by specific travel table types.
    """
    RECORD_CLASS = Record
    FID_LABEL = "fid"
    PRINT_COLS = {}

    def print(self) -> None:
        """Prints a table to the console."""
        print(tabulate(self._rows(), headers=self._headers()))

    def sort(self, col: str, ascending: bool = True) -> Self:
        """Sorts the table by the provided column."""
        records = self.__class__(sorted(
            self.items(),
            key=lambda x: x[1][col],
            reverse=(not ascending),
        ))
        return self.__class__(records)

    def write_csv(self, output_file: Path) -> None:
        """Writes a table to a CSV file."""
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self._headers())
            writer.writerows(self._rows())
        print(f"Wrote CSV to \"{output_file}\".")

    def _headers(self) -> list:
        """Returns print column names."""
        return [self.FID_LABEL, *self.PRINT_COLS.keys()]

    def _rows(self) -> list:
        """Converts the table into rows based on PRINT_COLS."""
        rows = []
        for fid, record in self.items():
            row = [fid]
            for column in self.PRINT_COLS.values():
                if callable(column):
                    value = column(record)
                else:
                    value = record[column]
                row.append(value)
            rows.append(row)
        return rows

class RecordLayerTable(RecordTable):
    """A RecordTable that comes from a GeoPackage layer."""

    @classmethod
    def from_all(cls) -> Self:
        """Creates a table of every object."""
        records = gpd.read_file(
            cls.RECORD_CLASS.DATA_FILE,
            layer=cls.RECORD_CLASS.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).astype(cls.RECORD_CLASS.DTYPES)
        records = records.astype(object).where(pd.notna(records), None)
        record_dict = records.to_dict(orient="index")
        record_dict = {k: cls.RECORD_CLASS(v) for k, v in record_dict.items()}
        return cls(record_dict)

    @classmethod
    def from_fids(cls, fids: list[int]) -> Self:
        """Creates a table with records matching a list of fids."""
        rec_table = {k: v for k, v in cls.from_all().items() if k in fids}
        return cls(rec_table)
