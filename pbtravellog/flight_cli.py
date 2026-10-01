"""Manages flight data CLI commands."""

# Standard imports
from pathlib import Path
import sys

# Third-party imports
from tabulate import tabulate

# Project imports
from pbtravellog.flight_log import FlightTable

def index_airports(
    year: int | None = None,
    output_file : Path | None = None,
) -> None:
    """Provides an index of all airports."""
    flights = FlightTable.from_all()
    if year is not None:
        flights = flights.filter_by_year(year)
    if len(flights) == 0:
        print("No airport visits found.")
        if year is not None:
            print(
                "Try searching a different year or removing the year filter."
            )
        sys.exit(1)
    airports = flights.collect_airports()
    if output_file is None:
        columns = [
            "rank",
            "name",
            "iata_code",
            "icao_code",
            "faa_lid",
            "visits",
        ]
        rows = (
            [fid, *(r[col] for col in columns)] for fid, r in airports.items()
        )
        print(tabulate(rows, headers=["fid", *columns]))
    else:
        pass
        # TODO: Write CSV export
