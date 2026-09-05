"""Builds and runs a static HTML travel log."""

# Standard imports
from functools import partial
import http.server
from importlib.resources import files, as_file
import os
from pathlib import Path
import sys
import shutil
import webbrowser

# Third-party imports
import geopandas as gpd
from jinja2 import Environment, PackageLoader
import pandas as pd

# Project imports
from pbtravellog.flight_log import (
    Flight, Airport, Airline, airport_visits
)

HTML_PATH = os.getenv("PBTRAVELLOG_HTML_PATH")
if HTML_PATH is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_HTML_PATH is missing."
    )

class FlightsTable(gpd.GeoDataFrame):
    """Contains a fully joined table of flights."""

    def __init__(self, gdf):
        super().__init__(gdf)

    def airport_records(self, fid) -> list[dict]:
        """Returns records matching an airport."""
        ft = self.copy()
        ft = ft[
            (ft["origin_airport_fid"] == fid)
            | (ft["destination_airport_fid"] == fid)
        ]
        ft = self._calculate_layovers(ft)
        return [_recordify_flight(_, r) for _, r in ft.iterrows()]

    def flight_records(self) -> list[dict]:
        """Returns records for all flights in table."""
        ft = self._calculate_layovers(self.copy())
        return [_recordify_flight(_, r) for _, r in ft.iterrows()]

    def _calculate_layovers(self, gdf):
        """Normalizes flights for Jinja output."""
        gdf = gdf.sort_values(by="departure_utc")
        gdf["continues_via_layover"] = (
            gdf["trip_fid"].notna()
            & gdf["trip_section"].notna()
            & (gdf["trip_fid"] == gdf["trip_fid"].shift(-1))
            & (gdf["trip_section"] == gdf["trip_section"].shift(-1))
        ).fillna(False)
        return gdf

class StaticHTMLBuilder():
    """Manages generation of static HTML travel data."""

    def __init__(self):
        """Initialize the static HTML builder."""
        self.all_flights = FlightsTable(Flight.joined_table())
        self.all_airlines = Airline.all()
        self.all_airports = Airport.all()
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

        aircraft_families_table = self._tabulate_aircraft_families(
            self.all_flights
        )
        aircraft_family_items = []
        for idx, row in aircraft_families_table.iterrows():
            aircraft_family_items.append({
                "rank": row["rank"],
                "name": idx,
                "count": row["count"],
            })
        index_aircraft_families_html = self.env.get_template(
            "index_aircraft_families.html"
        ).render(aircraft_families=aircraft_family_items)
        (aircraft_dir / "index.html").write_text(
            index_aircraft_families_html,
            encoding="utf-8",
        )

    def _build_airlines(self) -> None:
        """Builds airline pages."""
        print("- Building airlines…")
        airlines_dir = self.html_dir / "airlines"
        airlines_dir.mkdir()

        tables = {
            "airlines": self._tabulate_airlines(
                self.all_flights,
                column="airline_fid",
            ),
            "operators": self._tabulate_airlines(
                self.all_flights,
                column="operator_fid",
            ),
        }
        items = {
            "airlines": [],
            "operators": [],
        }
        for airline_type, airline_table in tables.items():
            for idx, row in airline_table.iterrows():
                items[airline_type].append({
                    "fid": idx,
                    "rank": row["rank"],
                    "name": row["name"],
                    "iata_code": _blank_if_na(row["iata_code"]),
                    "count": row["count"],
                })
        index_airlines_html = self.env.get_template("index_airlines.html") \
            .render(airlines=items["airlines"], operators=items["operators"])
        (airlines_dir / "index.html").write_text(
            index_airlines_html,
            encoding="utf-8",
        )

    def _build_airports(self) -> None:
        """Builds airport pages."""
        print("- Building airports…")
        airports_dir = self.html_dir / "airports"
        airports_dir.mkdir()

        airports = []
        for idx, row in self._tabulate_airports(self.all_flights).iterrows():
            airport = _recordify_airport(idx, row)
            airport_flights = self.all_flights.airport_records(idx)
            show_airport_html = self.env.get_template("show_airport.html") \
                .render(
                    airport=airport,
                    flights=airport_flights,
                )
            (airports_dir / f"{airport["id"]}.html").write_text(
                show_airport_html,
                encoding="utf-8",
            )
            airports.append(airport)
        index_airports_html = self.env.get_template("index_airports.html") \
            .render(airports=airports)
        (airports_dir / "index.html").write_text(
            index_airports_html,
            encoding="utf-8",
        )

    def _build_flights(self) -> None:
        """Builds flight pages."""
        print("- Building flights…")
        flights_dir = self.html_dir / "flights"
        flights_dir.mkdir()
        flight_items = self.all_flights.flight_records()
        index_flights_html = self.env.get_template("index_flights.html") \
            .render(flights=flight_items)
        (flights_dir / "index.html").write_text(
            index_flights_html,
            encoding="utf-8",
        )

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

        tails_table = self._tabulate_tails(self.all_flights)
        tail_items = []
        for idx, row in tails_table.iterrows():
            tail_items.append({
                "rank": row["rank"],
                "tail_number": idx,
                "aircraft_type_name": _blank_if_na(row["equipment"]),
                "count": row["count"],
            })
        index_tails_html = self.env.get_template("index_tails.html") \
            .render(tails=tail_items)
        (tails_dir / "index.html").write_text(
            index_tails_html,
            encoding="utf-8",
        )

    def _jinja_env(self) -> Environment:
        """Creates a Jinja environment."""
        env = Environment(
            loader=PackageLoader("pbtravellog"),
            autoescape=True,
        )
        env.filters["format_utc"] = _format_utc
        return env

    def _tabulate_aircraft_families(self, flights_table) -> pd.DataFrame:
        """Creates a table of aircraft families from a table of flights."""
        ft = flights_table.copy()
        df = ft.groupby("aircraft_type_family").agg(
            count=("aircraft_type_family", "count"),
        )
        df = df.sort_values(
            by=["count", "aircraft_type_family"],
            ascending=[False, True],
        )
        df["rank"] = df["count"].rank(method="min", ascending=False) \
            .astype("Int64")
        return df

    def _tabulate_airlines(
        self, flights_table, column="airline_fid"
    ) -> pd.DataFrame:
        """Creates a table of airlines from a table of flights."""
        df = pd.DataFrame(self.all_airlines.copy())
        count = flights_table[column].value_counts()
        df = df.join(count, how="right")
        df = df.sort_values(
            by=["count", "name"],
            ascending=[False, True],
        )
        df["rank"] = df["count"].rank(method="min", ascending=False)
        return df

    def _tabulate_airports(self, flights_table) -> gpd.GeoDataFrame:
        """Creates a table of airports from a table of flights."""
        gdf = self.all_airports.copy()
        visits = airport_visits(flights_table)
        gdf = gdf.join(visits)
        gdf = gdf.rename(columns={"count": "visits"})
        gdf = gdf.dropna(subset=["visits"])
        gdf = gdf.sort_values(
            by=["visits", "name"],
            ascending=[False, True],
        )
        gdf["rank"] = gdf["visits"].rank(method="min", ascending=False)
        return gdf

    def _tabulate_flights(self, flights_table) -> gpd.GeoDataFrame:
        """Normalizes a table of flights for Jinja output."""
        gdf = flights_table.copy()
        gdf["continues_via_layover"] = (
            gdf["trip_fid"].notna()
            & gdf["trip_section"].notna()
            & (gdf["trip_fid"] == gdf["trip_fid"].shift(-1))
            & (gdf["trip_section"] == gdf["trip_section"].shift(-1))
        ).fillna(False)
        return gdf

    def _tabulate_tails(self, flights_table) -> pd.DataFrame:
        """Create a table of tail numbers from a table of flights."""
        ft = flights_table.copy().sort_values("departure_utc")
        df = ft.groupby("tail_number").agg(
            count=("tail_number", "count"),
            equipment=("aircraft_type_name", "last")
        )
        df = df.sort_values(
            by=["count", "tail_number"],
            ascending=[False, True],
        )
        df["rank"] = df["count"].rank(method="min", ascending=False) \
            .astype("Int64")
        return df

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

    # Launch web server
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

def _blank_if_na(value):
    """Returns an empty string if a row value is empty."""
    if pd.isna(value):
        return ""
    return value

def _flight_name(row) -> str:
    """Formats a flight name."""
    if pd.notna(row.airline_name):
        if pd.notna(row.flight_number):
            return f"{row.airline_name} {row.flight_number}"
        return row.airline_name
    return "Unnamed Flight"

def _format_utc(dt) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")

def _recordify_airport(idx, row) -> dict:
    """Turns an airport row into a record."""
    return {
        "id": str(idx),
        "rank": row["rank"],
        "name": row["name"],
        "iata_code": _blank_if_na(row["iata_code"]),
        "icao_code": _blank_if_na(row["icao_code"]),
        "faa_lid": _blank_if_na(row["faa_lid"]),
        "visits": row["visits"],
    }

def _recordify_flight(_, row) -> dict:
    """Turns a flight row into a record."""
    airport_codes = _airport_codes(row)
    return {
        "name": _flight_name(row),
        "airline_fid": row["airline_fid"],
        "origin_airport_code": airport_codes[0],
        "destination_airport_code": airport_codes[1],
        "departure_utc": row["departure_utc"],
        "continues_via_layover": row["continues_via_layover"],
    }
