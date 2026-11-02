"""User functions for importing flights."""

# Standard imports
import json
from pathlib import Path

# Project imports
import pbtravellog.flight_log as fl

def export_flights_geojson(geojson_file: Path) -> None:
    """Exports flights to a GeoJSON file."""
    flights = fl.FlightTable.from_all().joined()
    geojson_data = flights.geojson(include_airports=False)
    with open(geojson_file, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)
    print(f"Wrote flights to \"{geojson_file}\".")
