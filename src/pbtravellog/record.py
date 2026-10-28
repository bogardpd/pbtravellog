"""Manages travel records."""

# Standard imports
import csv
from importlib import resources
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Self

# Third-party imports
import geopandas as gpd
import pandas as pd
from tabulate import tabulate

# Project imports
from pbtravellog.geometry import CRS, GPKG_GEOM_COL

DATA_ENV_VARS = {
    "travel": "PBTRAVELLOG_TRAVEL_GEOPACKAGE_PATH",
    "flight": "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH",
}

class Record(dict):
    """Represents a generic travel record.

    Designed to be inherited by specific travel object types.
    """
    DATA_FILE_ENV = None
    LOG_TYPE = None
    LAYER = None
    GEOM_FIELD = None
    GPKG_FORMAT_FIELDS = {} # Field names to format with _format_field()
    FIND_BY_CODES = []
    DTYPES = {}
    PARSE_DATES = [] # Only dates, not datetimes!

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, geojson: Path | None = None) -> None:
        """Saves a record to its GeoPackage layer."""
        # Load existing layer table structure.
        existing = gpd.GeoDataFrame(gpd.read_file(
            self.data_file(),
            layer=self.LAYER,
            engine="pyogrio",
            rows=0,
        ))
        if existing.active_geometry_name is not None:
            existing = existing.rename_geometry(GPKG_GEOM_COL)
        existing_cols = list(existing.columns)
        # Build and format values.
        gpkg_values = {
            col: self._format_field(
                self.get(col), self.GPKG_FORMAT_FIELDS.get(col)
            )
            for col in existing_cols if col != GPKG_GEOM_COL
        }
        if self.GEOM_FIELD is None:
            gdf = gpd.GeoDataFrame([gpkg_values], geometry=None)
        else:
            if GPKG_GEOM_COL not in existing_cols:
                raise ValueError(
                    f"Geometry column {GPKG_GEOM_COL} not found in existing "
                    f"layer schema {existing_cols}"
                )
            gpkg_values[GPKG_GEOM_COL] = self.get(self.GEOM_FIELD)
            gdf = gpd.GeoDataFrame(
                [gpkg_values],
                geometry=GPKG_GEOM_COL,
                crs=CRS,
            )
        if geojson is not None:
            # Save to GeoJSON instead of database.
            gdf.to_file(geojson, driver="GeoJSON")
            print(f"Wrote flight to {geojson}.")
            sys.exit(0)
        # Add missing columns from existing schema as null values.
        for col in existing_cols:
            if col not in gdf.columns:
                gdf[col] = None
                print(
                    f"No value was provided for column '{col}'; setting "
                    "its value to null."
                )
        # Reorder columns to match existing schema.
        gdf = gpd.GeoDataFrame(gdf[existing_cols])
        # Write file.
        gdf.to_file(
            self.data_file(),
            layer=self.LAYER,
            engine="pyogrio",
            mode="a",
        )
        print(f"Appended {type(self).__name__} to \"{self.data_file()}\".")

    def _format_field(self, field, field_format):
        """Applies formatting to a field."""
        if field_format is None:
            return field
        if field is None:
            return None
        if field_format == "datetime":
            return field.strftime("%Y-%m-%dT%H:%M:%SZ")
        if field_format == "json":
            return json.dumps(field)
        return field

    @classmethod
    def data_file(cls, log_type: str | None = None) -> Path | None:
        """Gets the path of the geopackage hosting this class."""
        if log_type is None:
            log_type = cls.LOG_TYPE
        if log_type is None:
            return None
        data_log = Path(os.getenv(DATA_ENV_VARS[log_type]))
        if data_log is None:
            raise KeyError(
                f"Environment variable {DATA_ENV_VARS[log_type]} is missing."
            )
        return data_log

    @classmethod
    def every(cls) -> gpd.GeoDataFrame:
        """Returns a GeoDataFrame of all records."""
        records = gpd.read_file(
            cls.data_file(),
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
            cls.data_file(),
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
        record["fid"] = int(record_row.name)
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
            cls.RECORD_CLASS.data_file(),
            layer=cls.RECORD_CLASS.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).astype(cls.RECORD_CLASS.DTYPES)
        for col in cls.RECORD_CLASS.PARSE_DATES:
            records[col] = records[col].dt.date
        records = records.astype(object).where(pd.notna(records), None)
        record_dict = records.to_dict(orient="index")
        record_dict = {k: cls.RECORD_CLASS(v) for k, v in record_dict.items()}
        for k, v in record_dict.items():
            v["fid"] = k
        return cls(record_dict)

    @classmethod
    def from_fids(cls, fids: list[int]) -> Self:
        """Creates a table with records matching a list of fids."""
        rec_table = {k: v for k, v in cls.from_all().items() if k in fids}
        return cls(rec_table)

def init_gpkg():
    """Creates empty GeoPackage files with schema-defined layers."""
    for log_type, _ in DATA_ENV_VARS.items():
        log_path = Record.data_file(log_type=log_type)
        proj_path = resources.files("pbtravellog")
        if log_path.exists():
            print(f"{log_type.title()} log already exists at \"{log_path}\".")
            continue
        empty_gpkg_path = proj_path / f"data/gpkg/{log_type}_log_empty.gpkg"
        with resources.as_file(empty_gpkg_path) as source_path:
            shutil.copy2(source_path, log_path)
        print(f"Created {log_type} log GeoPackage file at \"{log_path}\".")
