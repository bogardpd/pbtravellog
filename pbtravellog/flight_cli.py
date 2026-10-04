"""Manages flight data CLI commands."""

# Standard imports
from pathlib import Path
import sys

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
        print("No matching records found.")
        sys.exit(1)
    airports = flights.collect_airports()
    if output_file is None:
        airports.print()
        print(f"{len(airports)} airport(s) flown")
    else:
        pass
        # TODO: Write CSV export
