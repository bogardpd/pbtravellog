"""Manages flight data CLI commands."""

# Standard imports
from pathlib import Path
import sys

# Project imports
from pbtravellog.flight_log import FlightTable, Airport

def index_airports(
    output_file: Path | None = None,
    year: int | None = None,
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
        print(f"{len(airports)} airport(s) visited")
    else:
        airports.write_csv(output_file)

def show_airport(identifier: str) -> None:
    """Shows flights for a specific airport."""
    airport = Airport.find_by_code(identifier.upper(), check_fid=True)
    if airport is None:
        sys.exit(1)
    flights = FlightTable.from_all().joined().filter_by_airport(airport.fid)
    flights.print()
    print(f"{len(flights)} matching flight(s)")

def index_tails(output_file: Path | None = None) -> None:
    """Provides an index of all tails."""
    flights = FlightTable.from_all().joined()
    tail_numbers = flights.collect_tail_numbers()
    for tn in tail_numbers.values():
        if tn.get("aircraft_type") is not None:
            tn["aircraft_type"] = tn["aircraft_type"].full_name()
    if output_file is None:
        tail_numbers.print()
        print(f"{len(tail_numbers)} unique tail(s) flown")
    else:
        tail_numbers.write_csv(output_file)

def show_tail(tail_number: str) -> None:
    """Shows flights for a specific tail number."""
    flights = FlightTable.from_all().joined().filter_by_tail_number(
        tail_number.upper()
    )
    if len(flights) == 0:
        print("No matching flights found.")
        sys.exit(1)
    flights.print()
    print(f"{len(flights)} matching flight(s)")
