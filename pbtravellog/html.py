"""Builds and runs a static HTML travel log."""

# Standard imports
from collections import defaultdict
from datetime import datetime, UTC
import filecmp
from functools import partial
import http.server
from importlib.resources import files
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

    def __init__(self, force_refresh=False):
        """Initialize the static HTML builder."""
        self.all_flights = self._load_joined_flight_records()
        self.all_airlines = Airline.all()
        self.all_airports = Airport.all()
        self.all_aircraft_types = AircraftType.all()
        self.html_dir = Path(HTML_PATH)
        self.env = self._jinja_env()
        self.file_count = {"new": 0, "updated": 0, "unchanged": 0}
        self.force_refresh = force_refresh

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
        print(
            f"{sum(self.file_count.values())} files "
            f"({self.file_count["new"]} new, "
            f"{self.file_count["updated"]} updated, "
            f"{self.file_count["unchanged"]} unchanged)"
        )

    def _build_aircraft(self) -> None:
        """Builds aircraft pages."""
        print("- Building aircraft…")
        aircraft_dir = self.html_dir / "aircraft"
        aircraft_dir.mkdir(exist_ok=True)
        index_template = self.env.get_template("index_aircraft_types.html")
        show_template = self.env.get_template("show_aircraft_type.html")
        aircraft_type_records = self._collect_aircraft_type_records(
            self.all_flights,
        )
        for aircraft_type in aircraft_type_records:
            flights = self._filter_flights_by_aircraft_type(
                self.all_flights, aircraft_type["fid"],
            )
            airlines = self._collect_airline_records(
                flights, operators=False,
            )
            operators = self._collect_airline_records(
                flights, operators=True,
            )
            show_type_html = show_template.render(
                aircraft_type=aircraft_type,
                airlines=airlines,
                operators=operators,
                flights=flights,
            )
            show_path = aircraft_dir / f"{aircraft_type["fid"]}.html"
            self._write(show_path, show_type_html)
        index_html = index_template.render(
            aircraft_types=aircraft_type_records,
        )
        self._write(aircraft_dir / "index.html", index_html)

    def _build_airlines(self) -> None:
        """Builds airline pages."""
        print("- Building airlines…")
        airlines_dir = self.html_dir / "airlines"
        airlines_dir.mkdir(exist_ok=True)
        operators_dir = airlines_dir / "operators"
        operators_dir.mkdir(exist_ok=True)
        index_template = self.env.get_template("index_airlines.html")
        show_airline_template = self.env.get_template("show_airline.html")
        show_operator_template = self.env.get_template("show_operator.html")
        airline_records = self._collect_airline_records(
            self.all_flights, operators=False,
        )
        operator_records = self._collect_airline_records(
            self.all_flights, operators=True,
        )
        for airline in airline_records:
            airline_flights = self._filter_flights_by_airline(
                self.all_flights, airline["fid"], operator=False,
            )
            airline_operators = self._collect_airline_records(
                airline_flights, operators=True,
            )
            airline_aircraft_types = self._collect_aircraft_type_records(
                airline_flights,
            )
            show_airline_html = show_airline_template.render(
                airline=airline,
                operators=airline_operators,
                aircraft_types=airline_aircraft_types,
                flights=airline_flights,
            )
            show_airline_path = airlines_dir / f"{airline["fid"]}.html"
            self._write(show_airline_path, show_airline_html)
        for operator in operator_records:
            operator_flights = self._filter_flights_by_airline(
                self.all_flights, operator["fid"], operator=True,
            )
            operator_airlines = self._collect_airline_records(
                operator_flights, operators=False,
            )
            operator_aircraft_types = self._collect_aircraft_type_records(
                operator_flights,
            )
            show_operator_html = show_operator_template.render(
                operator=operator,
                airlines=operator_airlines,
                aircraft_types=operator_aircraft_types,
                flights=operator_flights,
            )
            show_operator_path = operators_dir / f"{operator["fid"]}.html"
            self._write(show_operator_path, show_operator_html)
        index_html = index_template.render(
            airlines=airline_records,
            operators=operator_records,
        )
        self._write(airlines_dir / "index.html", index_html)

    def _build_airports(self) -> None:
        """Builds airport pages."""
        print("- Building airports…")
        airports_dir = self.html_dir / "airports"
        airports_dir.mkdir(exist_ok=True)
        index_template = self.env.get_template("index_airports.html")
        show_template = self.env.get_template("show_airport.html")
        airport_records = self._collect_airport_records(self.all_flights)
        for airport in airport_records:
            flights = self._filter_flights_by_airport(
                self.all_flights, airport["fid"]
            )
            airlines = self._collect_airline_records(flights, operators=False)
            operators = self._collect_airline_records(flights, operators=True)
            aircraft_types = self._collect_aircraft_type_records(flights)
            show_html = show_template.render(
                airport=airport,
                airlines=airlines,
                operators=operators,
                aircraft_types=aircraft_types,
                flights=flights,
            )
            show_path = airports_dir / f"{airport["fid"]}.html"
            self._write(show_path, show_html)
        index_html = index_template.render(airports=airport_records)
        self._write(airports_dir / "index.html", index_html)

    def _build_flights(self) -> None:
        """Builds flight pages."""
        print("- Building flights…")
        flights_dir = self.html_dir / "flights"
        flights_dir.mkdir(exist_ok=True)
        index_template = self.env.get_template("index_flights.html")
        show_template = self.env.get_template("show_flight.html")
        for flight in self.all_flights:
            show_html = show_template.render(flight=flight)
            show_path = flights_dir / f"{flight["fid"]}.html"
            self._write(show_path, show_html)
        index_html = index_template.render(flights=self.all_flights)
        self._write(flights_dir / "index.html", index_html)

    def _build_home(self) -> None:
        """Builds home page."""
        print("- Building home…")
        home_html = self.env.get_template("home.html").render()
        self._write(self.html_dir / "index.html", home_html)

    def _build_structure(self) -> None:
        """Ensures HTML folder exists and copies static files."""
        print("- Building structure…")
        if self.force_refresh:
            # Delete all contents of html_dir.
            shutil.rmtree(self.html_dir, ignore_errors=True)
        self.html_dir.mkdir(parents=True, exist_ok=True)
        static_dir = files("pbtravellog") / "static"
        for src in static_dir.rglob("*"):
            if src.is_dir():
                continue
            dest = self.html_dir / src.relative_to(static_dir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if filecmp.cmp(src, dest, shallow=False):
                    self.file_count["unchanged"] += 1
                else:
                    shutil.copy2(src, dest)
                    self.file_count["updated"] += 1
                    print(f"  - Updated \"{src}\".")
            else:
                shutil.copy2(src, dest)
                self.file_count["new"] += 1
                print(f"  - Created \"{src}\".")

    def _build_tails(self) -> None:
        """Builds tail number pages."""
        print("- Building tail numbers…")
        tails_dir = self.html_dir / "tails"
        tails_dir.mkdir(exist_ok=True)
        index_template = self.env.get_template("index_tails.html")
        show_template = self.env.get_template("show_tail.html")
        tail_records = self._collect_tail_records(self.all_flights)
        for tail in tail_records:
            flights = self._filter_flights_by_tail(
                self.all_flights, tail["tail_number"],
            )
            airlines = self._collect_airline_records(
                flights, operators=False,
            )
            operators = self._collect_airline_records(
                flights, operators=True,
            )
            aircraft_types = self._collect_aircraft_type_records(
                flights,
            )
            show_html = show_template.render(
                tail=tail,
                airlines=airlines,
                operators=operators,
                aircraft_types=aircraft_types,
                flights=flights,
            )
            show_path = tails_dir / f"{tail["tail_number"]}.html"
            self._write(show_path, show_html)
        index_html = index_template.render(tails=tail_records)
        self._write(tails_dir / "index.html", index_html)

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
                "manufacturer": aircraft_type_row["manufacturer"],
                "name": aircraft_type_row["name"],
                "iata_code": aircraft_type_row["iata_code"],
                "icao_code": aircraft_type_row["icao_code"],
                "count": count,
                "rank": ranks[aircraft_type_fid],
            }
            record = {
                k: (None if pd.isna(v) else v) for k, v in record.items()
            }
            aircraft_type_records.append(record)
        aircraft_type_records = sorted(
            aircraft_type_records,
            key=lambda x: (-x["count"], x["manufacturer"], x["name"])
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
                "icao_code": airline_row["icao_code"],
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

    def _filter_flights_by_aircraft_type(
            self, flight_records, aircraft_type_fid: int,
    ) -> list[dict]:
        """Filters flight records by an aircraft type."""
        records = [
            r for r in flight_records
            if r["aircraft_type_fid"] == aircraft_type_fid
        ]
        return records

    def _filter_flights_by_airline(
        self, flight_records, airline_fid: int, operator=False,
    ) -> list[dict]:
        """Filters flight records by an airline."""
        column = "operator_fid" if operator else "airline_fid"
        records = [
            r for r in flight_records
            if r[column] == airline_fid
        ]
        return records

    def _filter_flights_by_airport(
        self, flight_records, airport_fid: int,
    ) -> list[dict]:
        """Filters flight records by an airport."""
        records = [
            r for r in flight_records
            if airport_fid in [
                r["origin_airport_fid"],
                r["destination_airport_fid"],
            ]
        ]
        return records

    def _filter_flights_by_tail(
        self, flight_records, tail_number: str,
    ) -> list[dict]:
        """Filters flight records by a tail number."""
        records = [
            r for r in flight_records
            if r["tail_number"] == tail_number
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
        departure_local = _local_dt(
            departure_utc,
            row["origin_airport_time_zone"]
        )
        if pd.isna(row["arrival_utc"]):
            arrival_utc = None
            arrival_local = None
            duration_h_m = None
        else:
            arrival_utc = row["arrival_utc"].to_pydatetime()
            arrival_local = _local_dt(
                arrival_utc,
                row["destination_airport_time_zone"]
            )
            dur_s = (arrival_utc-departure_utc).total_seconds()
            hours, remainder = divmod(dur_s, 3600)
            minutes = remainder // 60
            duration_h_m = (int(hours), int(minutes))
        record = {
            "fid": flight_fid,
            "departure_utc": departure_utc,
            "departure_local": departure_local,
            "arrival_utc": arrival_utc,
            "arrival_local": arrival_local,
            "duration_h_m": duration_h_m,
            "name": _flight_name(row),
            "aircraft_name": row["aircraft_name"],
            "tail_number": row["tail_number"],
            "aircraft_type_fid": row["aircraft_type_fid"],
            "aircraft_type_manufacturer": row["aircraft_type_manufacturer"],
            "aircraft_type_name": row["aircraft_type_name"],
            "airline_fid": row["airline_fid"],
            "airline_name": row["airline_name"],
            "codeshare_airline_fid": row["codeshare_airline_fid"],
            "codeshare_airline_name": row["codeshare_airline_name"],
            "codeshare_flight_number": row["codeshare_flight_number"],
            "operator_fid": row["operator_fid"],
            "operator_name": row["operator_name"],
            "origin_airport_fid": row["origin_airport_fid"],
            "origin_airport_code": airport_codes[0],
            "origin_airport_name": row["origin_airport_name"],
            "destination_airport_fid": row["destination_airport_fid"],
            "destination_airport_code": airport_codes[1],
            "destination_airport_name": row["destination_airport_name"],
            "trip_fid": row["trip_fid"],
            "trip_section": row["trip_section"],
            "boarding_pass_data": row["boarding_pass_data"],
            "comments": row["comments"],
        }
        record = {
            k: (None if pd.isna(v) else v) for k, v in record.items()
        }
        return record

    def _write(self, file_path: Path, contents: str) -> None:
        """Writes a generated file if the file is new or changed."""
        if file_path.exists():
            if (
                self.force_refresh
                or file_path.read_text(encoding="utf-8") != contents
            ):
                file_path.write_text(contents, encoding="utf-8", newline="\n")
                self.file_count["updated"] += 1
                print(f"  - Updated \"{file_path}\".")
            else:
                self.file_count["unchanged"] += 1
        else:
            file_path.write_text(contents, encoding="utf-8", newline="\n")
            self.file_count["new"] += 1
            print(f"  - Created \"{file_path}\".")


def build(force_refresh=False):
    """Builds a directory of static HTML pages."""
    b = StaticHTMLBuilder(force_refresh=force_refresh)
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

def _format_dt(dt, include_time=True, include_tz=False) -> str:
    """Formats a datetime."""
    if dt is None:
        return ""
    parts = ["%d %b %Y"]
    if include_time:
        parts.append("%H:%M")
    if include_tz:
        parts.append("%Z")
    return dt.strftime(" ".join(parts))

def _local_dt(dt_utc, tz):
    """Converts a UTC datetime to local time."""
    if pd.isna(dt_utc) or pd.isna(tz):
        return None
    return dt_utc.astimezone(ZoneInfo(tz))

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
