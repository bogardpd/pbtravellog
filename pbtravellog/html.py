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

PBFLIGHTLOG_GEOPACKAGE_PATH = os.getenv("PBFLIGHTLOG_GEOPACKAGE_PATH")
if PBFLIGHTLOG_GEOPACKAGE_PATH is None:
    raise KeyError(
        "Environment variable PBFLIGHTLOG_GEOPACKAGE_PATH is missing."
    )

def build():
    """Builds a directory of static HTML pages."""
    print("Building pbflightlog HTML...")
    html_dir = Path(HTML_PATH)

    # Create root and static folders.
    html_dir.mkdir(parents=True, exist_ok=True)
    for item in html_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    static_dir = files("pbtravellog") / "static"
    with as_file(static_dir) as static_path:
        shutil.copytree(static_path, html_dir, dirs_exist_ok=True)

    # Load Jinja environment.
    env = Environment(
        loader=PackageLoader("pbtravellog"),
        autoescape=True,
    )
    env.filters['format_utc'] = _format_utc
    home_html = env.get_template("home.html").render()
    (html_dir / "index.html").write_text(home_html, encoding="utf-8")

    # Create data tables.

    airports_gdf = gpd.read_file(
        PBFLIGHTLOG_GEOPACKAGE_PATH,
        layer='airports',
        fid_as_index=True
    )
    airports_gdf['code'] = airports_gdf['iata_code'] \
        .fillna(airports_gdf['icao_code']) \
        .fillna(airports_gdf['faa_lid'])
    airlines_gdf = gpd.read_file(
        PBFLIGHTLOG_GEOPACKAGE_PATH,
        layer='airlines',
        fid_as_index=True
    )
    flights_gdf = gpd.read_file(
        PBFLIGHTLOG_GEOPACKAGE_PATH,
        layer='flights',
        fid_as_index=True,
    )
    flights_gdf['airline_fid'] = flights_gdf['airline_fid'].astype("Int64")
    flights_gdf = flights_gdf.sort_values('departure_utc')

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

    # Create Flights.
    flights_dir = html_dir / "flights"
    flights_dir.mkdir()
    flight_items = []
    for idx, row in flights_table.iterrows():
        flight_items.append({
            'name': _flight_name(row),
            'origin_airport_code': row.origin_airport_code,
            'destination_airport_code': row.destination_airport_code,
            'departure_utc': row.departure_utc,
        })

    index_flights_html = env.get_template("index_flights.html").render(
        flights=flight_items
    )
    (flights_dir / "index.html").write_text(
        index_flights_html,
        encoding="utf-8",
    )

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
