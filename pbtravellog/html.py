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

HTML_PATH = os.getenv("PBTRAVELLOG_HTML_PATH")
if HTML_PATH is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_HTML_PATH is missing."
    )

PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH = os.getenv(
    "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH"
)
if PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH is missing."
    )

def build():
    """Builds a directory of static HTML pages."""
    print("Building pbflightlog HTML...")
    html_dir = Path(HTML_PATH)

    # Load travel log data.
    flights_gdf = _load_flights_gdf()
    airlines_gdf = _load_airlines_gdf()
    airports_gdf = _load_airports_gdf()

    # Create joined tables for pages.
    flights_table = _join_flights(flights_gdf, airlines_gdf, airports_gdf)
    airlines_table = _join_airlines(airlines_gdf)
    airports_table = _join_airports(airports_gdf)

    env = _jinja_env()
    _build_structure(html_dir)
    _build_home(html_dir, env)
    _build_flights(html_dir, env, flights_table)
    _build_airlines(html_dir, env, airlines_table)
    _build_airports(html_dir, env, airports_table)

    print(f"Wrote static site to \"{html_dir}\".")

def run(port):
    """Launches a server and browser."""
    print("Launching pbflightlog HTML...")
    if not os.path.exists(HTML_PATH):
        raise FileNotFoundError(
            f"HTML path {HTML_PATH} does not exist. "
            "Did you run `pbflightlog build`?"
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

def _blank_if_na(value):
    """Returns an empty string if a row value is empty."""
    if pd.isna(value):
        return ""
    return value

def _build_airlines(html_dir, env, airlines_table) -> None:
    """Builds airline pages."""
    airlines_dir = html_dir / "airlines"
    airlines_dir.mkdir()
    airline_items = []
    for idx, row in airlines_table.iterrows():
        airline_items.append({
            'fid': idx,
            'name': row['name'],
            'iata_code': _blank_if_na(row['iata_code']),
            'icao_code': _blank_if_na(row['icao_code']),
        })
    index_airlines_html = env.get_template("index_airlines.html") \
        .render(airlines=airline_items)
    (airlines_dir / "index.html").write_text(
        index_airlines_html,
        encoding="utf-8",
    )

def _build_airports(html_dir, env, airports_table) -> None:
    """Builds airport pages."""
    airports_dir = html_dir / "airports"
    airports_dir.mkdir()
    airport_items = []
    for idx, row in airports_table.iterrows():
        airport_items.append({
            'name': row['name'],
            'iata_code': _blank_if_na(row['iata_code']),
            'icao_code': _blank_if_na(row['icao_code']),
            'code': row['code'],
        })
    index_airports_html = env.get_template("index_airports.html") \
        .render(airports=airport_items)
    (airports_dir / "index.html").write_text(
        index_airports_html,
        encoding="utf-8",
    )

def _build_flights(html_dir, env, flights_table) -> None:
    """Builds flight pages."""
    flights_dir = html_dir / "flights"
    flights_dir.mkdir()
    flight_items = []
    for idx, row in flights_table.iterrows():
        flight_items.append({
            'name': _flight_name(row),
            'airline_fid': row['airline_fid'],
            'origin_airport_code': row['origin_airport_code'],
            'destination_airport_code': row['destination_airport_code'],
            'departure_utc': row['departure_utc'],
        })
    index_flights_html = env.get_template("index_flights.html") \
        .render(flights=flight_items)
    (flights_dir / "index.html").write_text(
        index_flights_html,
        encoding="utf-8",
    )

def _build_home(html_dir, env) -> None:
    """Builds home page."""
    home_html = env.get_template("home.html").render()
    (html_dir / "index.html").write_text(home_html, encoding="utf-8")

def _build_structure(html_dir) -> None:
    """Ensures empty HTML folder and copies static files."""
    html_dir.mkdir(parents=True, exist_ok=True)
    for item in html_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    static_dir = files("pbtravellog") / "static"
    with as_file(static_dir) as static_path:
        shutil.copytree(static_path, html_dir, dirs_exist_ok=True)

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

def _jinja_env() -> Environment:
    """Creates a Jinja environment."""
    env = Environment(
        loader=PackageLoader("pbtravellog"),
        autoescape=True,
    )
    env.filters['format_utc'] = _format_utc
    return env

def _join_airlines(airlines_gdf) -> pd.DataFrame:
    airlines_table = pd.DataFrame(airlines_gdf[[
        'name',
        'iata_code',
        'icao_code',
    ]])
    airlines_table = airlines_table.sort_values('name')
    return airlines_table

def _join_airports(airports_gdf) -> pd.DataFrame:
    airports_table = pd.DataFrame(airports_gdf[[
        'name',
        'iata_code',
        'icao_code',
        'code',
    ]])
    airports_table = airports_table.sort_values('name')
    return airports_table

def _join_flights(flights_gdf, airlines_gdf, airports_gdf) -> pd.DataFrame:
    flights_table = pd.DataFrame(flights_gdf[[
        'departure_utc',
        'flight_number',
        'airline_fid',
        'origin_airport_fid',
        'destination_airport_fid',
    ]])
    flights_table = flights_table.join(
        airports_gdf['code'].rename("origin_airport_code"),
        on="origin_airport_fid",
    )
    flights_table = flights_table.join(
        airports_gdf['code'].rename("destination_airport_code"),
        on="destination_airport_fid",
    )
    flights_table = flights_table.join(
        airlines_gdf['name'].rename("airline_name"),
        on="airline_fid",
    )
    return flights_table

def _load_airlines_gdf() -> gpd.GeoDataFrame:
    """Prepares a GeoDataFrame of airline data."""
    airlines_gdf = gpd.read_file(
        PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH,
        layer='airlines',
        fid_as_index=True
    )
    return airlines_gdf

def _load_airports_gdf() -> gpd.GeoDataFrame:
    """Prepares a GeoDataFrame of airport data."""
    airports_gdf = gpd.read_file(
        PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH,
        layer='airports',
        fid_as_index=True
    )
    airports_gdf['code'] = airports_gdf['iata_code'] \
        .fillna(airports_gdf['icao_code']) \
        .fillna(airports_gdf['faa_lid'])
    return airports_gdf

def _load_flights_gdf() -> gpd.GeoDataFrame:
    """Prepares a GeoDataFrame of flight data."""
    flights_gdf = gpd.read_file(
        PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH,
        layer='flights',
        fid_as_index=True,
    )
    flights_gdf['airline_fid'] = flights_gdf['airline_fid'].astype("Int64")
    return flights_gdf.sort_values('departure_utc')
