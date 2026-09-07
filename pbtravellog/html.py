"""Builds and runs a static HTML travel log."""

# Standard imports
from collections import defaultdict
from datetime import datetime, UTC
from functools import partial
import http.server
from importlib.resources import files, as_file
import os
from pathlib import Path
import sys
import shutil
import webbrowser
from zoneinfo import ZoneInfo

# Third-party imports
from jinja2 import Environment, PackageLoader
import pandas as pd

# Project imports
from pbtravellog.flight_log import (
    Flight, Airport, Airline, AircraftType
)

HTML_PATH = os.getenv("PBTRAVELLOG_HTML_PATH")
if HTML_PATH is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_HTML_PATH is missing."
    )

class StaticHTMLBuilder():
    """Manages generation of static HTML travel data."""

    def __init__(self):
        """Initialize the static HTML builder."""
        self.all_flights = self._load_joined_flight_records()
        self.all_airlines = Airline.all()
        self.all_airports = Airport.all()
        self.all_aircraft_types = AircraftType.all()
        self.html_dir = Path(HTML_PATH)
        self.env = self._jinja_env()

    def build(self):
        """Builds a directory of static HTML pages."""
        print("Building PBTravelLog HTML…")

        self._build_structure()
        self._build_home()
        self._build_flights()
        self._build_aircraft()
        self._build_airlines()
        self._build_airports()
        self._build_tails()

        print(f"Wrote static site to \"{self.html_dir}\".")

    def _build_aircraft(self) -> None:
        """Builds aircraft pages."""
        print("- Building aircraft…")
        aircraft_dir = self.html_dir / "aircraft"
        aircraft_dir.mkdir()
        aircraft_types_dir = aircraft_dir / "types"
        aircraft_types_dir.mkdir()
        index_template = self.env.get_template("index_aircraft_families.html")
        show_template = self.env.get_template("show_aircraft_family.html")
        show_type_template = self.env.get_template("show_aircraft_type.html")
        aircraft_family_records = self._collect_aircraft_family_records(
            self.all_flights
        )
        for aircraft_family in aircraft_family_records:
            flights = self._filter_flights_by_aircraft_family(
                self.all_flights, aircraft_family["name"]
            )
            aircraft_types = self._collect_aircraft_type_records(flights)
            airlines = self._collect_airline_records(flights, operators=False)
            operators = self._collect_airline_records(flights, operators=True)
            for aircraft_type in aircraft_types:
                type_flights = self._filter_flights_by_aircraft_type(
                    self.all_flights, aircraft_type["fid"],
                )
                type_airlines = self._collect_airline_records(
                    type_flights, operators=False,
                )
                type_operators = self._collect_airline_records(
                    type_flights, operators=True,
                )
                show_type_html = show_type_template.render(
                    aircraft_type=aircraft_type,
                    aircraft_family=aircraft_family,
                    airlines=type_airlines,
                    operators=type_operators,
                    flights=type_flights,
                )
                type_page_path = (
                    aircraft_types_dir / f"{aircraft_type["fid"]}.html"
                )
                type_page_path.write_text(show_type_html, encoding="utf-8")
            show_html = show_template.render(
                aircraft_family=aircraft_family,
                aircraft_types=aircraft_types,
                airlines=airlines,
                operators=operators,
                flights=flights,
            )
            page_path = (
                aircraft_dir / f"{_slugify(aircraft_family["name"])}.html"
            )
            page_path.write_text(show_html, encoding="utf_8")
        index_html = index_template.render(
            aircraft_families=aircraft_family_records,
        )
        (aircraft_dir / "index.html").write_text(index_html, encoding="utf-8")

    def _build_airlines(self) -> None:
        """Builds airline pages."""
        print("- Building airlines…")
        airlines_dir = self.html_dir / "airlines"
        airlines_dir.mkdir()
        index_template = self.env.get_template("index_airlines.html")
        airline_records = self._collect_airline_records(
            self.all_flights, operators=False,
        )
        operator_records = self._collect_airline_records(
            self.all_flights, operators=True,
        )
        index_html = index_template.render(
            airlines=airline_records,
            operators=operator_records,
        )
        (airlines_dir / "index.html").write_text(index_html, encoding="utf-8")

    def _build_airports(self) -> None:
        """Builds airport pages."""
        print("- Building airports…")
        airports_dir = self.html_dir / "airports"
        airports_dir.mkdir()
        index_template = self.env.get_template("index_airports.html")
        show_template = self.env.get_template("show_airport.html")
        airport_records = self._collect_airport_records(self.all_flights)
        for airport in airport_records:
            flights = self._filter_flights_by_airport(
                self.all_flights, airport["fid"]
            )
            airlines = self._collect_airline_records(flights, operators=False)
            operators = self._collect_airline_records(flights, operators=True)
            aircraft_families = self._collect_aircraft_family_records(flights)
            show_html = show_template.render(
                airport=airport,
                airlines=airlines,
                operators=operators,
                aircraft_families=aircraft_families,
                flights=flights,
            )
            page_path = airports_dir / f"{airport["fid"]}.html"
            page_path.write_text(show_html, encoding="utf-8")
        index_html = index_template.render(airports=airport_records)
        (airports_dir / "index.html").write_text(index_html, encoding="utf-8")

    def _build_flights(self) -> None:
        """Builds flight pages."""
        print("- Building flights…")
        flights_dir = self.html_dir / "flights"
        flights_dir.mkdir()
        index_template = self.env.get_template("index_flights.html")
        index_html = index_template.render(flights=self.all_flights)
        (flights_dir / "index.html").write_text(index_html, encoding="utf-8")

    def _build_home(self) -> None:
        """Builds home page."""
        home_html = self.env.get_template("home.html").render()
        (self.html_dir / "index.html").write_text(home_html, encoding="utf-8")

    def _build_structure(self) -> None:
        """Ensures empty HTML folder and copies static files."""
        self.html_dir.mkdir(parents=True, exist_ok=True)
        for item in self.html_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        static_dir = files("pbtravellog") / "static"
        with as_file(static_dir) as static_path:
            shutil.copytree(static_path, self.html_dir, dirs_exist_ok=True)

    def _build_tails(self) -> None:
        """Builds tail number pages."""
        print("- Building tail numbers…")
        tails_dir = self.html_dir / "tails"
        tails_dir.mkdir()
        index_template = self.env.get_template("index_tails.html")
        tail_records = self._collect_tail_records(self.all_flights)
        index_html = index_template.render(tails=tail_records)
        (tails_dir / "index.html").write_text(index_html, encoding="utf-8")

    def _collect_aircraft_family_records(self, flight_records) -> list[dict]:
        """Builds aircraft family records from flight records."""
        aircraft_family_flight_count = defaultdict(int)
        category = {}
        for flight in flight_records:
            key = flight["aircraft_type_family"]
            aircraft_family_flight_count[key] += 1
            category[key] = flight["aircraft_type_category"]
        aircraft_family_flight_count.pop(None, None) # Remove None count
        ranks = _rank_count(aircraft_family_flight_count)
        aircraft_family_records = []
        for aircraft_family, count in aircraft_family_flight_count.items():
            record = {
                "slug": _slugify(aircraft_family),
                "name": aircraft_family,
                "category": category[aircraft_family].replace("_", " "),
                "count": count,
                "rank": ranks[aircraft_family],
            }
            aircraft_family_records.append(record)
        aircraft_family_records = sorted(
            aircraft_family_records, key=lambda x: (-x["count"], x["name"]),
        )
        return aircraft_family_records

    def _collect_aircraft_type_records(self, flight_records) -> list[dict]:
        """Builds aircraft type records from flight records."""
        aircraft_type_flight_count = defaultdict(int)
        for flight in flight_records:
            aircraft_type_flight_count[flight["aircraft_type_fid"]] += 1
        aircraft_type_flight_count.pop(None, None) # Remove None count
        ranks = _rank_count(aircraft_type_flight_count)
        aircraft_type_records = []
        for aircraft_type_fid, count in aircraft_type_flight_count.items():
            aircraft_type_row = self.all_aircraft_types.loc[aircraft_type_fid]
            record = {
                "fid": aircraft_type_fid,
                "name": aircraft_type_row["name"],
                "iata_code": aircraft_type_row["iata_code"],
                "icao_code": aircraft_type_row["icao_code"],
                "category": aircraft_type_row["category"].replace("_", " "),
                "count": count,
                "rank": ranks[aircraft_type_fid],
            }
            record = {
                k: (None if pd.isna(v) else v) for k, v in record.items()
            }
            aircraft_type_records.append(record)
        aircraft_type_records = sorted(
            aircraft_type_records, key=lambda x: (-x["count"], x["name"])
        )
        return aircraft_type_records

    def _collect_airline_records(
        self, flight_records, operators=False,
    ) -> list[dict]:
        """Builds airline records from flight records."""
        column = "operator_fid" if operators else "airline_fid"
        airline_flight_count = defaultdict(int)
        for flight in flight_records:
            airline_flight_count[flight[column]] += 1
        airline_flight_count.pop(None, None) # Remove None count
        ranks = _rank_count(airline_flight_count)
        airline_records = []
        for _, (airline_fid, count) in enumerate(
            airline_flight_count.items()
        ):
            airline_row = self.all_airlines.loc[airline_fid]
            record = {
                "fid": airline_fid,
                "name": airline_row["name"],
                "iata_code": airline_row["iata_code"],
                "count": count,
                "rank": ranks[airline_fid],
            }
            record = {
                k: (None if pd.isna(v) else v) for k, v in record.items()
            }
            airline_records.append(record)
        airline_records = sorted(
            airline_records, key=lambda x: (-x["count"], x["name"])
        )
        return airline_records

    def _collect_airport_records(self, flight_records) -> list[dict]:
        """Builds airport records from flight records."""
        airport_visit_count = defaultdict(int)
        prev_trip_sec = [None, None]
        for flight in flight_records:
            curr_trip_sec = [flight["trip_fid"], flight["trip_section"]]
            if curr_trip_sec != prev_trip_sec:
                # This is not following a layover, so count the origin.
                airport_visit_count[flight["origin_airport_fid"]] += 1
            airport_visit_count[flight["destination_airport_fid"]] += 1
            prev_trip_sec = curr_trip_sec
        airport_visit_count.pop(None, None) # Remove None count
        ranks = _rank_count(airport_visit_count)
        airport_records = []
        for _, (airport_fid, visits) in enumerate(
            airport_visit_count.items()
        ):
            airport_row = self.all_airports.loc[airport_fid]
            record = {
                "fid": airport_fid,
                "name": airport_row["name"],
                "iata_code": airport_row["iata_code"],
                "icao_code": airport_row["icao_code"],
                "faa_lid": airport_row["faa_lid"],
                "visits": visits,
                "rank": ranks[airport_fid],
            }
            record = {
                k: (None if pd.isna(v) else v) for k, v in record.items()
            }
            airport_records.append(record)

        airport_records = sorted(
            airport_records, key=lambda x: (-x["visits"], x["name"]),
        )
        return airport_records

    def _collect_tail_records(self, flight_records) -> list[dict]:
        """Builds tail records from flight records."""
        tail_flight_count = defaultdict(int)
        equipment = {}
        for flight in flight_records:
            tail_flight_count[flight["tail_number"]] += 1
            equipment[flight["tail_number"]] = flight["aircraft_type_name"]
        tail_flight_count.pop(None, None) # Remove None count
        ranks = _rank_count(tail_flight_count)
        tail_records = []
        for idx, (tail_number, count) in enumerate(tail_flight_count.items()):
            record = {
                "index_id": idx,
                "tail_number": tail_number,
                "aircraft_type_name": equipment[tail_number],
                "count": count,
                "rank": ranks[tail_number],
            }
            tail_records.append(record)
        tail_records = sorted(
            tail_records, key=lambda x: (-x["count"], x["tail_number"]),
        )
        return tail_records

    def _filter_flights_by_aircraft_family(
        self, flight_records, aircraft_family_name,
    ) -> list[dict]:
        """Filters flight records by an aircraft family."""
        records = [
            r for r in flight_records
            if r["aircraft_type_family"] == aircraft_family_name
        ]
        return records

    def _filter_flights_by_aircraft_type(
            self, flight_records, aircraft_type_fid,
    ) -> list[dict]:
        """Filters flight records by an aircraft type."""
        records = [
            r for r in flight_records
            if r["aircraft_type_fid"] == aircraft_type_fid
        ]
        return records

    def _filter_flights_by_airport(
        self, flight_records, airport_fid,
    ) -> list[dict]:
        """Filters flight records by an airport."""
        records = [
            r for r in flight_records
            if (
                r["origin_airport_fid"] == airport_fid
                or r["destination_airport_fid"] == airport_fid
            )
        ]
        return records

    def _jinja_env(self) -> Environment:
        """Creates a Jinja environment."""
        env = Environment(
            loader=PackageLoader("pbtravellog"),
            autoescape=True,
        )
        env.filters["format_dt"] = _format_dt
        env.globals["build_time"] = datetime.now(UTC)
        return env

    def _load_joined_flight_records(self) -> list[dict]:
        """Loads records from Flight.joined()."""
        gdf = Flight.joined()
        output = [
            self._recordize_flight_row(idx, row)
            for idx, row in gdf.iterrows()
        ]
        output = sorted(output, key=lambda x: x["departure_utc"])
        return output

    def _recordize_flight_row(self, flight_fid, row) -> dict:
        """Turns a flight row into a record."""
        airport_codes = _airport_codes(row)
        departure_utc = row["departure_utc"].to_pydatetime()
        record = {
            "fid": flight_fid,
            "departure_utc": departure_utc,
            "departure_local": departure_utc.astimezone(
                ZoneInfo(row["origin_airport_time_zone"])
            ),
            "name": _flight_name(row),
            "tail_number": row["tail_number"],
            "aircraft_type_fid": row["aircraft_type_fid"],
            "aircraft_type_name": row["aircraft_type_name"],
            "aircraft_type_family": row["aircraft_type_family"],
            "aircraft_type_category": row["aircraft_type_category"],
            "airline_fid": row["airline_fid"],
            "operator_fid": row["operator_fid"],
            "origin_airport_fid": row["origin_airport_fid"],
            "origin_airport_code": airport_codes[0],
            "destination_airport_fid": row["destination_airport_fid"],
            "destination_airport_code": airport_codes[1],
            "trip_fid": row["trip_fid"],
            "trip_section": row["trip_section"],
        }
        record = {
            k: (None if pd.isna(v) else v) for k, v in record.items()
        }
        return record


def build():
    """Builds a directory of static HTML pages."""
    b = StaticHTMLBuilder()
    b.build()

def run(port):
    """Launches a server and browser."""
    print("Launching PBTravelLog HTML…")
    if not os.path.exists(HTML_PATH):
        raise FileNotFoundError(
            f"HTML path {HTML_PATH} does not exist. "
            "Did you run `pbtravellog build`?"
        )

    # Launch web server.
    handler = partial(
        http.server.SimpleHTTPRequestHandler, directory=HTML_PATH
    )
    with http.server.ThreadingHTTPServer(
        ("127.0.0.1", port), handler
    ) as httpd:
        url = f"http://localhost:{port}"
        print(f"Serving directory \"{HTML_PATH}\" at {url}.")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            sys.exit(0)

def _airport_codes(row) -> tuple[str]:
    """Returns a default origin and destination code."""
    orig = [
        row["origin_airport_iata_code"],
        row["origin_airport_icao_code"],
        row["origin_airport_faa_lid"],
    ]
    orig = [v for v in orig if pd.notna(v)][0]
    dest = [
        row["destination_airport_iata_code"],
        row["destination_airport_icao_code"],
        row["destination_airport_faa_lid"],
    ]
    dest = [v for v in dest if pd.notna(v)][0]
    return (orig, dest)

def _flight_name(row) -> str:
    """Formats a flight name."""
    if pd.notna(row.airline_name):
        if pd.notna(row.flight_number):
            return f"{row.airline_name} {row.flight_number}"
        return row.airline_name
    return "Unnamed Flight"

def _format_dt(dt, include_time=True) -> str:
    """Formats a datetime."""
    if dt is None:
        return ""
    parts = ["%d %b %Y"]
    if include_time:
        parts.append("%H:%M")
    return dt.strftime(" ".join(parts))

def _rank_count(count_dict: dict) -> dict:
    """Ranks a dictionary of item counts."""
    sorted_count = sorted(count_dict.items(), key=lambda x: -x[1])
    ranks = dict()
    prev_count = None
    prev_rank = 0
    for idx, (key, count) in enumerate(sorted_count):
        rank = prev_rank if count == prev_count else idx + 1
        ranks[key] = rank
        prev_count = count
        prev_rank = rank
    return ranks

def _slugify(input_str) -> str:
    """Converts a string to a filename and URL safe string."""
    return input_str.replace(" ", "_")
