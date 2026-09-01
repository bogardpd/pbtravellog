"""Scripts for interacting with the flight log."""

# Standard imports
from datetime import datetime, date, timedelta, timezone
import json
from math import ceil
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Self

# Third-party imports
from dateutil.parser import isoparse
import geopandas as gpd
import pandas as pd
from pyproj import Geod
from shapely.geometry import Point, LineString, MultiLineString
from tabulate import tabulate

# Project imports
import pbtravellog.aeroapi as aero
from pbtravellog.boarding_pass import BoardingPass, PKPass

METERS_PER_MILE = 1609.344
METERS_PER_HUNDRED_FEET = 30.48
METERS_BETWEEN_GC_POINTS = 100000

CRS = "EPSG:4326" # WGS-84

flight_log = os.getenv("PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH")
if flight_log is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH is missing."
    )

class Record():
    """Represents a record from a flight log table."""
    LAYER = None
    FIND_BY_CODES = []
    DTYPES = {}

    @classmethod
    def all(cls) -> gpd.GeoDataFrame:
        """Returns a GeoDataFrame of all records."""
        records = gpd.read_file(
            flight_log,
            layer=cls.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).astype(cls.DTYPES)
        return records

    @classmethod
    def pluck(cls, column) -> list[Self]:
        """Returns a list of all values of a column."""
        records = cls.all()
        return records[column].to_list()

    @classmethod
    def find_by_code(cls, code: str, check_fid=False) -> Self | None:
        """Finds a record by searching through code fields."""
        if getattr(cls, 'FIND_BY_CODES', None) is None:
            return None
        if len(cls.FIND_BY_CODES) == 0:
            return None
        records = gpd.read_file(
            flight_log,
            layer = cls.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        )

        # Check for fid on numeric codes. Note that this will allow
        # defunct records since fids are unique.
        if check_fid and re.search(r'^[0-9]+$', code):
            if int(code) in records.index:
                record_dict = records.loc[int(code)].to_dict()
                record_dict['fid'] = int(code)
                record = cls()
                for key, value in record_dict.items():
                    setattr(record, key, value)
                return record

        # Filter out defunct records. This is helpful in situations
        # where current records use the same codes as an old record
        # (for example, the current PSA airlines and the defunct Comair
        # both use the IATA code 'OH'.)
        if 'is_defunct' in records.columns:
            records = records[~records['is_defunct']]
        for code_type in cls.FIND_BY_CODES:
            # Search for matching codes.
            matching_code = records[records[code_type] == code]
            if len(matching_code) == 1:
                record_dict = matching_code.iloc[0].to_dict()
                record_dict['fid'] = int(matching_code.index[0])
                record = cls()
                for key, value in record_dict.items():
                    setattr(record, key, value)
                return record
        print(f"⚠️ Could not find {cls.__name__} matching \"{code}\".")
        return None

class AircraftType(Record):
    """Represents an aircraft type record."""
    LAYER = "aircraft_types"
    FIND_BY_CODES = ['icao_code']
    DTYPES = {}

    def __init__(self):
        # Fields used in flight log database:
        self.fid: int | None = None
        self.manufacturer: str | None = None
        self.name: str | None = None
        self.icao_code: str | None = None
        self.iata_code: str | None = None
        self.family: str | None = None
        self.category: str | None = None

class Airline(Record):
    """Represents an airline record."""
    LAYER = "airlines"
    FIND_BY_CODES = ['icao_code', 'iata_code']
    DTYPES = {}

    def __init__(self):
        # Fields used in flight log database:
        self.fid: int | None = None
        self.name: str | None = None
        self.icao_code: str | None = None
        self.iata_code: str | None = None
        self.numeric_code: str | None = None
        self.is_only_operator: bool | None = None
        self.is_defunct: bool | None = None

class Airport(Record):
    """Represents an airline record."""
    LAYER = "airports"
    FIND_BY_CODES = ['icao_code', 'iata_code', 'faa_lid']
    DTYPES = {}

    def __init__(self):
        # Fields used in flight log database:
        self.fid: int | None = None
        self.geometry: Point | None = None
        self.name: str | None = None
        self.country: str | None = None
        self.icao_code: str | None = None
        self.iata_code: str | None = None
        self.faa_lid: str | None = None
        self.time_zone: str | None = None
        self.is_defunct: bool | None = None

    def __repr__(self):
        code = self.iata_code or self.icao_code or self.faa_lid
        return f"[{self.fid}] {code}: {self.name}"

class Flight(Record):
    """Represents a flight record."""
    LAYER = "flights"
    FIND_BY_CODES = []
    DTYPES = {
        'origin_airport_fid': "Int64",
        'destination_airport_fid': "Int64",
        'fh_id': "Int64",
        'trip_fid': "Int64",
        'trip_section': "Int64",
    }

    def __init__(self):
        # Fields used in flight log database:
        self.geometry: MultiLineString | None = None
        self.departure_utc: datetime | None = None
        self.arrival_utc: datetime | None = None
        self.trip_fid: int | None = None
        self.trip_section: int | None = None
        self.airline_fid: int | None = None
        self.flight_number: str | None = None
        self.origin_airport_fid: int | None = None
        self.destination_airport_fid: int | None = None
        self.aircraft_type_fid: int | None = None
        self.operator_fid: int | None = None
        self.tail_number: str | None = None
        self.boarding_pass_data: str | None = None
        self.fh_id: int | None = None
        self.fa_flight_id: str | None = None
        self.fa_json: list[dict] | None = None
        self.geom_source: str | None = None
        self.distance_mi: int | None = None

        # Other fields from AeroAPI:
        self.scheduled_out: datetime | None = None
        self.estimated_out: datetime | None = None
        self.actual_out: datetime | None = None
        self.scheduled_in: datetime | None = None
        self.estimated_in: datetime | None = None
        self.actual_in: datetime | None = None
        self.ident: str | None = None
        self.origin_code: str | None = None
        self.origin_tz: str | None = None
        self.destination_code: str | None = None
        self.destination_tz: str | None = None
        self.progress: int | None = None

    def fetch_aeroapi_track_geometry(self) -> None:
        """Gets flight track from AeroAPI"""
        if self.progress is None or self.progress < 100:
            print(
                "⚠️ Cannot get track: flight is not complete "
                f"({self.progress}% complete)."
            )
            return
        if self.fa_flight_id is None:
            print("⚠️ Cannot get track: fa_flight_id is not set.")
            return
        fa_json = aero.get_flights_ident_track(self.fa_flight_id)
        if fa_json is None:
            print(f"⚠️ No track found for {self.fa_flight_id}.")
            return
        positions = fa_json.get('positions')
        if len(positions) == 0:
            print(f"⚠️ No positions found for {self.fa_flight_id}.")
            return
        track_ls = LineString([Point(
            p.get('longitude'),
            p.get('latitude'),
            p.get('altitude') * METERS_PER_HUNDRED_FEET,
        ) for p in positions])
        self.geometry = split_at_antimeridian(track_ls)
        self.geom_source = "FlightAware"
        try:
            self.distance_mi = int(fa_json.get('actual_distance'))
        except TypeError, ValueError:
            print(f"⚠️ No distance found for {self.fa_flight_id}.")

    def exit_if_not_complete(self) -> None:
        """Exits if this flight is not complete."""
        if self.progress is None or self.progress < 100:
            print(
                f"⚠️ Flight is not complete ({self.progress}% complete). "
                "Flight was not added to log."
            )
            sys.exit(1)

    def gdf(self) -> gpd.GeoDataFrame:
        """Returns a GeoDataFrame record for the flight."""
        record = {
            'geometry': self.geometry,
            'departure_utc': _format_time(self.departure_utc),
            'arrival_utc': _format_time(self.arrival_utc),
            'trip_fid': self.trip_fid,
            'trip_section': self.trip_section,
            'airline_fid': self.airline_fid,
            'flight_number': self.flight_number,
            'origin_airport_fid': self.origin_airport_fid,
            'destination_airport_fid': self.destination_airport_fid,
            'aircraft_type_fid': self.aircraft_type_fid,
            'operator_fid': self.operator_fid,
            'tail_number': self.tail_number,
            'boarding_pass_data': self.boarding_pass_data,
            'fh_id': self.fh_id,
            'fa_flight_id': self.fa_flight_id,
            'fa_json': (
                None if self.fa_json is None else json.dumps(self.fa_json)
            ),
            'geom_source': self.geom_source,
            'distance_mi': self.distance_mi,
            'comments': None,
        }
        return gpd.GeoDataFrame([record], geometry='geometry', crs=CRS)

    def save(self, geojson: Path | None = None) -> None:
        """Appends a flight to the geopackage file."""
        record_gdf = self.gdf()

        # Check for matching tail numbers.
        if self.tail_number is not None:
            tails_gdf = Flight.all()
            tails_gdf = tails_gdf[tails_gdf['tail_number'] == self.tail_number]
            if len(tails_gdf) > 0:
                print(
                    f"You've now had {len(tails_gdf) + 1} flights on tail "
                    + f"number '{self.tail_number}'!"
                )

        if geojson is not None:
            # Save to GeoJSON instead of database.
            record_gdf.to_file(geojson, driver='GeoJSON')
            print(f"Wrote flight to {geojson}.")
            sys.exit(0)
        existing = gpd.read_file(
            flight_log,
            layer=Flight.LAYER,
            engine="pyogrio",
            rows=0,
        )
        existing_cols = list(existing.columns)
        incoming_cols = list(record_gdf.columns)

        # Check that geometry column name matches.
        geom_col = record_gdf.geometry.name
        if geom_col not in existing_cols:
            raise ValueError(
                f"Geometry column '{geom_col}' not found in existing "
                "layer schema"
            )

        # Check for columns in new data not in current schema.
        extra_cols = set(incoming_cols) - set(existing_cols)
        if extra_cols:
            raise ValueError(
                "Incoming data has columns not present in layer "
                f"schema: {extra_cols}"
            )

        # Add missing columns from existing schema as null values.
        for col in existing_cols:
            if col not in record_gdf.columns:
                record_gdf[col] = None
                print(
                    f"No value was provided for column '{col}'; setting "
                    "its value to null."
                )

        # Reorder columns to match existing schema.
        gdf = record_gdf[existing_cols]
        gdf.to_file(
            flight_log,
            driver="GPKG",
            engine="pyogrio",
            layer=Flight.LAYER,
            mode="a",
        )
        print(f"Appended flight to {flight_log}.")


    def _arr_utc(self) -> datetime | None:
        """Gets the actual arrival time of a flight."""
        if self.actual_in is None:
            # Flights diverted to a different airport use estimated_in.
            if self.progress == 100:
                return self.estimated_in
            return None
        return self.actual_in

    def _dep_utc(self) -> datetime | None:
        """Gets the actual departure time of a flight."""
        return self.actual_out or None

    @classmethod
    def from_aeroapi(cls, fa_json: dict) -> Self:
        """Loads flight values from an AeroAPI response."""
        flight = cls()
        try:
            flight.progress = int(fa_json.get('progress_percent'))
        except TypeError, ValueError:
            pass
        # Store fa_json as list containing dict because some flight
        # records (such as diverts) may require more than one AeroAPI
        # JSON result stored in the database.
        flight.fa_json = [fa_json]
        flight.ident = fa_json.get('ident')
        flight.scheduled_out = cls.parse_dt(fa_json.get('scheduled_out'))
        flight.estimated_out = cls.parse_dt(fa_json.get('estimated_out'))
        flight.actual_out = cls.parse_dt(fa_json.get('actual_out'))
        flight.scheduled_in = cls.parse_dt(fa_json.get('scheduled_in'))
        flight.estimated_in = cls.parse_dt(fa_json.get('estimated_in'))
        flight.actual_in = cls.parse_dt(fa_json.get('actual_in'))
        flight.departure_utc = flight._dep_utc()
        flight.arrival_utc = flight._arr_utc()
        flight.flight_number = fa_json.get('flight_number')

        origin = fa_json.get('origin', {})
        flight.origin_airport_fid = getattr(
            Airport.find_by_code(origin.get('code')), 'fid', None
        )
        flight.origin_code = origin.get('code_iata') or origin.get('code')
        flight.origin_tz = origin.get('timezone')

        destination = fa_json.get('destination', {})
        flight.destination_airport_fid = getattr(
            Airport.find_by_code(destination.get('code')), 'fid', None
        )
        flight.destination_code = destination.get('code_iata') \
            or destination.get('code')
        flight.destination_tz = destination.get('timezone')

        flight.aircraft_type_fid = getattr(
            AircraftType.find_by_code(fa_json.get('aircraft_type')),
            'fid', None
        )
        flight.operator_fid = getattr(
            Airline.find_by_code(fa_json.get('operator')), 'fid', None
        )
        flight.tail_number = fa_json.get('registration')
        flight.fa_flight_id = fa_json.get('fa_flight_id')
        return flight

    @staticmethod
    def parse_dt(dt_str) -> datetime | None:
        """Parses a datetime string."""
        if dt_str is None:
            return None
        return isoparse(dt_str)

class Route(Record):
    """Represents a route record"""
    LAYER = "routes"
    FIND_BY_CODES = []
    DTYPES = {}

class Trip(Record):
    """Represents a trip record."""
    LAYER = "trips"
    FIND_BY_CODES = []
    DTYPES = {'fh_id': "Int64"}

    def __init__(self):
        # Fields used in flight log database:
        self.fid: int | None = None
        self.fh_id: int | None = None
        self.name: str | None = None
        self.start_date: date | None = None
        self.end_date: date | None = None
        self.comments: str | None = None

    def estimate_trip_section(self, departure_dt: datetime) -> int | None:
        """Suggests a trip section number based on departure time."""
        flights = gpd.read_file(
            flight_log,
            layer=Flight.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).astype(Flight.DTYPES)
        flights = flights[flights['trip_fid'] == self.fid]
        if len(flights) == 0:
            # No flights in trip.
            return 1
        if flights['trip_section'].isnull().any():
            # Some flights have no trip section.
            return None
        flights = flights[['departure_utc', 'trip_fid', 'trip_section']]
        flights = flights.sort_values(by='departure_utc')
        latest_flight = flights.iloc[-1]
        if departure_dt <= latest_flight['departure_utc']:
            # New flight occurs before latest flight.
            return None
        if departure_dt < latest_flight['departure_utc'] + timedelta(days=1):
            # New flight is within 24 hours of latest flight.
            return int(latest_flight['trip_section'])
        # New flight is more than 24 hours after latest flight.
        return int(latest_flight['trip_section']) + 1

    @classmethod
    def select_by_date(cls, departure_date: date) -> Self | None:
        """
        Selects a trip based on departure date.

        The date provided should be the flight departure date from a
        boarding pass.
        """
        records = gpd.read_file(
            flight_log,
            layer=cls.LAYER,
            engine="pyogrio",
            fid_as_index=True,
        ).dropna(subset=['start_date', 'end_date']).astype(cls.DTYPES)

        matching = records[
            (records['start_date'].dt.date <= departure_date)
            & (records['end_date'].dt.date >= departure_date)
        ].sort_values(by=['start_date', 'end_date'], ascending=False)
        if matching.size == 0:
            return None
        record_dict = matching.iloc[0].to_dict()
        record_dict['fid'] = int(matching.index[0])
        record = cls()
        for k, v in record_dict.items():
            setattr(
                record,
                k,
                v.date() if hasattr(v, 'date') else v
            )
        return record


def airport_visits(flights_gdf: gpd.GeoDataFrame) -> pd.Series:
    """Calculates airport visit counts from flights."""
    count_orig = count_origin_visits(flights_gdf)
    flights_gdf.loc[~count_orig, 'origin_airport_fid'] = pd.NA
    counts = flights_gdf[['origin_airport_fid', 'destination_airport_fid']] \
        .stack().value_counts()
    return counts

def count_origin_visits(flights_gdf: gpd.GeoDataFrame) -> pd.Series:
    """Determines whether to count origins as a visit."""
    flights_gdf = flights_gdf[[
        'departure_utc',
        'trip_fid',
        'trip_section',
        'origin_airport_fid',
        'destination_airport_fid',
    ]]
    flights_gdf = flights_gdf.sort_values(by='departure_utc')
    flights_gdf['prev_dest_fid'] = flights_gdf['destination_airport_fid'] \
        .shift(1)
    flights_gdf['prev_trip_fid'] = flights_gdf['trip_fid'].shift(1)
    flights_gdf['prev_trip_section'] = flights_gdf['trip_section'].shift(1)
    # Set origin airport to NA for flights that continue after a
    # layover. A flight is considered continuing after a layover if it
    # has a trip and trip section, the trip and trip section are the
    # same as the previous flight, and the origin is the same as the
    # previous flight's destination. In that case, the continuing
    # flight's origin should not be counted (since it was already
    # counted in the previous flight's destination).
    flights_gdf['orig_visit'] = True
    flights_gdf.loc[
        (flights_gdf['trip_fid'].notna())
        & (flights_gdf['trip_section'].notna())
        & (flights_gdf['origin_airport_fid'] == flights_gdf['prev_dest_fid'])
        & (flights_gdf['trip_fid'] == flights_gdf['prev_trip_fid'])
        & (flights_gdf['trip_section'] == flights_gdf['prev_trip_section']),
    'orig_visit'] = False
    return flights_gdf['orig_visit']

def flights_table(
    flights_gdf: gpd.GeoDataFrame,
    visit_airport_fid: int | None = None,
    extra_columns: dict | None = None,
) -> str:
    """Formats a flight table for printing."""
    airports_gdf = Airport.all()
    airlines_gdf = Airline.all()
    flights_gdf = flights_gdf.join(
        airports_gdf.add_suffix("_orig"),
        on="origin_airport_fid"
    )
    flights_gdf = flights_gdf.join(
        airports_gdf.add_suffix("_dest"),
        on="destination_airport_fid"
    )
    flights_gdf = flights_gdf.join(
        airlines_gdf.add_suffix("_airline"),
        on="airline_fid"
    )
    flights_gdf['order'] = flights_gdf['departure_utc'].rank().astype(int)
    flights_gdf['departure_date'] = flights_gdf.apply(lambda r:
        r['departure_utc'].tz_convert(r['time_zone_orig']).date(),
        axis=1,
    )
    flights_gdf['flight_ident'] = flights_gdf['iata_code_airline'].str.cat(
        flights_gdf['flight_number'], sep=" "
    ).fillna("")
    flights_gdf['orig'] = flights_gdf.apply(lambda r:
        next(val for col in [
            'iata_code_orig', 'icao_code_orig', 'faa_lid_orig'
        ] if pd.notna(val := r[col])),
        axis=1,
    )
    flights_gdf['dest'] = flights_gdf.apply(lambda r:
        next(val for col in [
            'iata_code_dest', 'icao_code_dest', 'faa_lid_dest'
        ] if pd.notna(val := r[col])),
        axis=1,
    )
    table_cols = {
        'order': "#",
        'departure_date': "Departure",
        'flight_ident': "Flight",
        'orig': "Orig",
        'dest': "Dest",
    }
    if visit_airport_fid is not None:
        # Include visit counts for the specified airport.
        flights_gdf['count_origin_visits'] = count_origin_visits(flights_gdf)
        flights_gdf['this_airport_visits'] = flights_gdf.apply(lambda r:
            (1 if (
                r['count_origin_visits']
                and r['origin_airport_fid'] == visit_airport_fid
            ) else 0) + (1 if (
                r['destination_airport_fid'] == visit_airport_fid
            ) else 0),
            axis=1,
        )
        flights_gdf['cumulative_visits'] = flights_gdf['this_airport_visits'] \
            .cumsum()
        table_cols |= {
            'cumulative_visits': "Cumulative\nVisits"
        }
    if extra_columns is not None:
        table_cols |= extra_columns
    records = flights_gdf[table_cols.keys()].to_records()
    return tabulate(
        records,
        headers=["fid", *table_cols.values()],
    )

def great_circle_route(point1, point2) -> pd.Series:
    """
    Creates a great circle line between points.

    Returns a Pandas series with distance in integer miles and a
    MultiLineString geometry.
    """
    if point1 == point2:
        # Returned to same airport. Return zero great circle distance
        # and no geometry.
        return pd.Series([0, None])
    geod = Geod(ellps="WGS84")
    _, _, dist_m = geod.inv(point1.x, point1.y, point2.x, point2.y)
    dist_mi = int(round(dist_m / METERS_PER_MILE))

    # Create a great circle LineString.
    num_points = ceil(dist_m / METERS_BETWEEN_GC_POINTS) + 1
    midpoints = geod.npts(
        point1.x, point1.y,
        point2.x, point2.y,
        num_points - 2,
    )
    geom = split_at_antimeridian(
        LineString([point1, *midpoints, point2])
    )

    return pd.Series([dist_mi, geom])

def import_flight_bcbp(bcbp_str, geojson: Path | None = None) -> None:
    """Parses a Bar-Coded Boarding Pass string."""
    bp = BoardingPass(bcbp_str)
    _import_bp_flights(bp, geojson=geojson)
    refresh_routes()

def import_flight_fa_flight_id(
    fa_flight_id: str,
    geojson: Path | None = None
) -> None:
    """Gets info for a fa_flight_id and saves flight to log."""
    fa_flights = aero.get_flights_ident(fa_flight_id, "fa_flight_id")
    _import_fa_flight_results(fa_flights)
    refresh_routes()

def import_flight_number(
    airline_code: str,
    flight_number: str,
    geojson: Path | None = None
) -> None:
    """Gets info for a flight number and logs the flight."""
    airline = Airline.find_by_code(airline_code)
    # If airline is IATA, try to look up ICAO.
    if len(airline_code) == 2:
        if airline is not None and airline.icao_code is not None:
            airline_code = airline.icao_code
    flight_number = flight_number.lstrip("0") or "0"
    ident = f"{airline_code}{flight_number}"
    fa_flights = aero.get_flights_ident(ident, "designator")
    _import_fa_flight_results(
        fa_flights,
        fields={'airline_fid': airline.fid},
        geojson=geojson,
    )
    refresh_routes()

def import_flight_pkpasses(geojson: Path | None = None) -> None:
    """Imports digital boarding passes."""

    import_folder_env = os.getenv("PBTRAVELLOG_IMPORT_PATH")
    if import_folder_env is None:
        raise KeyError(
            "Environment variable PBTRAVELLOG_IMPORT_PATH is missing."
        )
    import_folder = Path(import_folder_env)
    if not import_folder.is_dir():
        raise KeyError(
            "Environment variable PBTRAVELLOG_IMPORT_PATH is not a directory."
        )
    archive_folder_env = os.getenv("PBTRAVELLOG_PKPASS_ARCHIVE_PATH")
    if archive_folder_env is None:
        raise KeyError(
            "Environment variable PBTRAVELLOG_PKPASS_ARCHIVE_PATH is missing."
        )
    archive_folder = Path(archive_folder_env)
    if not archive_folder.is_dir():
        raise KeyError(
            "Environment variable PBTRAVELLOG_PKPASS_ARCHIVE_PATH is not a "
            + "directory."
        )

    print(f"Importing digital boarding passes from \"{import_folder}\"")
    pkpasses = {
        f: PKPass(f) for f in import_folder.glob("*.pkpass")
        if f.is_file()
    }
    if len(pkpasses) == 0:
        print("⚠️ No .pkpass files found.")

    # Sort passes by relevant_date.
    pkpasses = dict(
        sorted(
            pkpasses.items(),
            key=lambda item: item[1].relevant_date or datetime.max.replace(
                tzinfo=timezone.utc
            )
        )
    )

    # Process passes.
    for pkpass_file, pkpass in pkpasses.items():
        print(pkpass.relevant_date)
        bp = pkpass.boarding_pass
        _import_bp_flights(bp, geojson=geojson)
        archive_file_path = archive_folder / pkpass.archive_filename
        pkpass_file.move(archive_file_path)
        print(f"Archived PKPass to \"{archive_file_path}\"")
    refresh_routes()

def index_airports(
    year: int | None = None,
    output_file : Path | None = None,
) -> None:
    """Provides an index of all airports."""
    flights_gdf = Flight.all()
    if year is not None:
        flights_gdf = flights_gdf[flights_gdf['departure_utc'].dt.year == year]
    if len(flights_gdf) == 0:
        print("No airport visits found.")
        if year is not None:
            print(
                "Try searching a different year or removing the year filter."
            )
        sys.exit(1)
    visits = airport_visits(flights_gdf)
    airports_gdf = Airport.all()
    output = airports_gdf.join(visits, how='right')
    output = output.rename(columns={'count': 'visits'})
    output = output.sort_values(by=['visits', 'name'], ascending=[False, True])
    output['rank'] = output['visits'].rank(
        ascending=False,
        method='min',
    ).astype(int)
    output = output[['rank','name','iata_code','icao_code','faa_lid','visits']]
    if output_file is None:
        output = output.fillna('')
        # print(output.to_string(index=True))
        print(tabulate(
            output.to_records(),
            headers=[
                "fid",
                "Rank",
                "Name",
                "IATA\nCode",
                "ICAO\nCode",
                "FAA\nLID",
                "Visits",
            ],
        ))
        print(f"{len(output)} airport(s) visited")
    else:
        output.to_csv(output_file, index=False)
        print(f"Wrote report to \"{output_file}\"")

def index_tails() -> None:
    """Provides an index of all tail numbers."""
    flights_gdf = Flight.all()
    flights_gdf = flights_gdf.dropna(subset='tail_number')
    tails_df = flights_gdf.groupby('tail_number').agg(
        count=('tail_number', 'count'),
        aircraft_type_fid=('aircraft_type_fid', 'last'),
    )
    types_gdf = AircraftType.all()[['manufacturer', 'name']]
    tails_df = tails_df.join(types_gdf, on='aircraft_type_fid')
    tails_df['type'] = tails_df['manufacturer'].str.cat(
        tails_df['name'],
        sep=" ",
    )
    tails_df = tails_df.sort_values(
        by=['count', tails_df.index.name],
        ascending=[False, True],
    )
    tails_df = tails_df[['type', 'count']]
    print(tabulate(tails_df.to_records(), headers=["Tail", "Type", "Count"]))
    print(f"{len(tails_df)} tails(s) flown")

def refresh_routes():
    """Updates the routes layer based on logged flights."""
    con = sqlite3.connect(flight_log)
    flights_sql = """
        SELECT origin_airport_fid, destination_airport_fid,
            COUNT(*) as flight_count
        FROM flights
        GROUP BY origin_airport_fid, destination_airport_fid
        ORDER BY origin_airport_fid, destination_airport_fid
    """
    flights_df = pd.read_sql(flights_sql, con)
    con.close()

    airports = gpd.read_file(
        flight_log,
        layer='airports',
        engine='pyogrio',
        fid_as_index=True,
    )

    flights_df[['distance_mi', 'geometry']] = flights_df.apply(lambda f:
        _great_circle_airport_lookup(f, airports),
        axis = 1,
    )
    flights_df['distance_mi'] = flights_df['distance_mi'].astype("Int64")

    routes_gdf = gpd.GeoDataFrame(flights_df, geometry='geometry', crs=CRS)

    routes_gdf.to_file(
        flight_log,
        driver='GPKG',
        engine='pyogrio',
        layer='routes',
        mode='w',
    )
    print(
        f"Updated all routes in {flight_log}."
    )

def show_airport(identifier: str) -> None:
    """Shows data about a specific airport."""
    airport = Airport.find_by_code(identifier.upper(), check_fid=True)
    if airport is None:
        sys.exit(1)
    print(airport)

    flights_gdf = Flight.all()
    flights_gdf = flights_gdf[
        (flights_gdf['origin_airport_fid'] == airport.fid)
        | (flights_gdf['destination_airport_fid'] == airport.fid)
    ]
    print(flights_table(flights_gdf, visit_airport_fid=airport.fid))

def show_tail(tail_number: str) -> None:
    """Shows data about a specific tail number."""
    tail_number = tail_number.upper()
    flights_gdf = Flight.all()
    flights_gdf = flights_gdf[flights_gdf['tail_number'] == tail_number]
    if len(flights_gdf) == 0:
        print(f"No flights found for tail number '{tail_number}'.")
        sys.exit(0)
    print(flights_table(flights_gdf))

def split_at_antimeridian(track_ls: LineString) -> MultiLineString:
    """Split a LineString at the antimeridian."""
    # Find all points where the track crosses the antimeridian.
    crossings = [
        i + 1 for i, (p1, p2)
        in enumerate(zip(track_ls.coords[:-1], track_ls.coords[1:]))
        if abs(p1[0] - p2[0]) > 180
    ]
    if len(crossings) == 0:
        return MultiLineString([track_ls])

    # Split the track at the indices.
    tracks = []
    starts = [0, *crossings]
    ends = [*crossings, len(track_ls.coords)]
    tracks = [
        track_ls.coords[start:end] for start, end in zip(starts, ends)
    ]
    for i, track in enumerate(tracks):
        if i > 0:
            p1 = track[0]
            p2 = tracks[i-1][-1]
            p_cross = _crossing_point(p1, p2)
            if p_cross is not None:
                track.insert(0, p_cross)
        if i < len(crossings):
            p1 = track[-1]
            p2 = tracks[i+1][0]
            p_cross = _crossing_point(p1, p2)
            if p_cross is not None:
                track.append(p_cross)

    # Filter out tracks with only one point.
    tracks = [track for track in tracks if len(track) > 1]
    return MultiLineString(tracks)

def _crossing_point(p1, p2):
    """Return the point where a track crosses the antemeridian.
    Returns None if p1 is already on the antemeridian.

    p1 : tuple(float)
        The point on the current track
    p2 : tuple(float)
        The point on the adjacent track.
    """
    p2 = list(p2)
    if -180 < p1[0] < 0:
        lon = -180
        p2[0] = p2[0] - 360
    elif 0 < p1[0] < 180:
        lon = 180
        p2[0] = p2[0] + 360
    else:
        return None
    x_frac = (lon - p1[0]) / (p2[0] - p1[0])
    return tuple([c1 + (x_frac * (c2 - c1)) for c1, c2 in zip(p1, p2)])

def _flight_from_aeroapi_results(aero_results) -> Flight:
    """Has user select flight from AeroAPI results and gets geometry."""
    if len(aero_results) == 0:
        print("No matching flights found.")
        sys.exit(1)
    aero_flight_info = aero.select_flight_info(aero_results)
    if aero_flight_info is None:
        # No AeroAPI flight selected. Return empty flight.
        return Flight()
    flight = Flight.from_aeroapi(aero_flight_info)
    flight.exit_if_not_complete()
    flight.fetch_aeroapi_track_geometry()
    return flight

def _format_time(time_val):
    """Format time as ISO 8601 with Z."""
    if time_val is None:
        return None
    return time_val.strftime("%Y-%m-%dT%H:%M:%SZ")

def _great_circle_airport_lookup(row, airports):
    """Runs great_circle_route with a GeoDataFrame row."""
    try:
        return great_circle_route(
            airports.loc[row.origin_airport_fid, 'geometry'],
            airports.loc[row.destination_airport_fid, 'geometry'],
        )
    except KeyError:
        return pd.Series([None, None])

def _import_bp_flights(bp: BoardingPass, geojson: Path | None = None) -> None:
    """Builds Flights from a BoardingPass, and saves them."""
    if not bp.valid or len(bp.legs) == 0:
        print("⚠️ The boarding pass data is not valid.")
        sys.exit(1)

    # Build list of boarding pass flights.
    bp_flights: list[Flight] = []
    for leg in bp.legs:
        print(f"Processing leg \"{leg}\"")
        airline = Airline.find_by_code(leg.airline_iata)
        if airline is not None and airline.icao_code is not None:
            airline_code = airline.icao_code
        else:
            airline_code = leg.airline_iata
        ident = f"{airline_code}{leg.flight_number}"
        aero_results = aero.get_flights_ident(ident, "designator")
        flight = _flight_from_aeroapi_results(aero_results)
        flight.airline_fid = airline.fid
        flight.boarding_pass_data = leg.bcbp_str
        trip = Trip.select_by_date(leg.flight_date)
        if trip is not None:
            flight.trip_fid = trip.fid
            if flight.departure_utc is not None:
                flight.trip_section = trip.estimate_trip_section(
                    flight.departure_utc
                )
        bp_flights.append(flight)

    # Save flights.
    if geojson is None:
        for flight in bp_flights:
            flight.save()
    else:
        if len(bp_flights) == 1:
            bp_flights[0].save(geojson=geojson)
        else:
            for i, flight in enumerate(bp_flights):
                gj_path = geojson.with_stem(f"{geojson.stem}_{i}")
                flight.save(geojson=gj_path)

def _import_fa_flight_results(
    aero_results: dict,
    fields: dict = None,
    geojson: Path | None = None,
) -> None:
    """Processes the results of an AeroAPI flights request."""
    flight = _flight_from_aeroapi_results(aero_results)

    # Set provided fields
    if fields is not None:
        for key, value in fields.items():
            setattr(flight, key, value)

    flight.save(geojson=geojson)

def _this_airport_visits(row, fid: int) -> int:
    """Returns number of visits in row of airport with provided fid."""
    count = 0
    if row['count_origin_visits'] and row['origin_airport_fid'] == fid:
        count += 1
    if row['destination_airport_fid'] == fid:
        count += 1
    return count
