"""Manages flight data CLI commands."""

# Standard imports
from pathlib import Path

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
    airports = flights.collect_airports()
    if output_file is None:
        airports.print()
    else:
        pass
        # TODO: Write CSV export
