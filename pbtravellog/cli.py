"""Travel log command line utilities."""

# Standard imports
import argparse
from pathlib import Path

# Third-party imports

# Project imports
import pbtravellog.extract_photo_metadata as epm
import pbtravellog.html as html
import pbtravellog.flight_log as fl
import pbtravellog.report as report

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tools for managing travel logs"
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    _add_parsers_add(subparsers)
    _add_parsers_build(subparsers)
    _add_parsers_extract_photo_metadata(subparsers)
    _add_parsers_index(subparsers)
    _add_parsers_refresh(subparsers)
    _add_parsers_report(subparsers)
    _add_parsers_run(subparsers)
    _add_parsers_show(subparsers)

    # Parse arguments
    args = parser.parse_args()
    if args.command == "add":
        if args.entity == "flight":
            if args.bcbp is not None:
                fl.add_flight_bcbp(args.bcbp, geojson=args.geojson)
            elif args.fa_flight_id is not None:
                fl.add_flight_fa_flight_id(
                    args.fa_flight_id,
                    geojson=args.geojson,
                )
            elif args.flight_number is not None:
                fl.add_flight_number(*args.flight_number, geojson=args.geojson)
            elif args.pkpasses:
                fl.add_flight_pkpasses(geojson=args.geojson)
    elif args.command == "build":
        html.build()
    elif args.command == "extract-photo-metadata":
        epm.extract_photo_metadata(args.source, args.output)
    elif args.command == "index":
        if args.entity == "airports":
            fl.index_airports(args.year, args.output)
        elif args.entity == "tails":
            fl.index_tails()
    elif args.command == "refresh":
        if args.entity == "routes":
            fl.refresh_routes()
    elif args.command == "report":
        if args.entity == "milestones":
            report.report_milestones()
    elif args.command == "show":
        if args.entity == "airport":
            fl.show_airport(args.id)
        elif args.entity == "tail":
            fl.show_tail(args.tail_number)
    elif args.command == "run":
        html.run(args.port)

def _add_parsers_add(subparsers) -> None:
    """Adds parsers for add command."""
    add_parser = subparsers.add_parser(
        "add",
        help="Add items to travel log",
    )
    add_subparsers = add_parser.add_subparsers(dest="entity", required=True)

    # Add flight
    add_flight_parser = add_subparsers.add_parser(
        "flight",
    )
    add_flight_parser.add_argument("--geojson",
        help="Save flight to GeoJSON file instead of database",
        metavar="GEOJSON_PATH",
        type=Path,
    )
    add_flight_source_group = add_flight_parser.add_mutually_exclusive_group(
        required=True, # Set to false if we create GUI add flight option
    )
    add_flight_source_group.add_argument("--bcbp",
        help="Add flight(s) from a BCBP-coded text string",
        metavar="BCBP_TEXT",
        type=str,
    )
    add_flight_source_group.add_argument("--fa-flight-id",
        help="Add a flight from an FlightAware fa_flight_id",
        type=str,
    )
    add_flight_source_group.add_argument("--number",
        dest="flight_number",
        help=(
            "Add a flight from an airline code (ICAO preferred) and "
            "flight number"
        ),
        nargs=2,
        metavar=("AIRLINE_CODE", "FLIGHT_NUMBER"),
        type=str,
    )
    add_flight_source_group.add_argument("--pkpasses",
        action="store_true",
        help="Add flights from .pkpass files in the import folder"
    )

def _add_parsers_build(subparsers) -> None:
    """Adds parsers for build command."""
    subparsers.add_parser(
        "build",
        help="Build static HTML log"
    )

def _add_parsers_extract_photo_metadata(subparsers) -> None:
    """Adds parsers for extract-photo-metadata command."""
    epm_parser = subparsers.add_parser(
        "extract-photo-metadata",
        help="Extract metadata from a folder of photos"
    )
    epm_parser.add_argument("--source",
        help="Directory of source photos",
        type=Path,
        required=True,
    )
    epm_parser.add_argument("--output",
        help="Directory for output files",
        type=Path,
        required=True,
    )

def _add_parsers_index(subparsers) -> None:
    """Adds parsers for index command."""
    index_parser = subparsers.add_parser(
        "index",
        help="Display indexes",
    )
    index_parser_subparsers = index_parser.add_subparsers(
        dest="entity",
        required=True,
    )

    # Index airports
    index_airports_parser = index_parser_subparsers.add_parser(
        "airports",
        help="Display an airport index",
    )
    index_airports_parser.add_argument("-o", "--output",
        help="Write index to a file (CSV format)",
        metavar="FILE",
        type=Path,
    )
    index_airports_parser.add_argument("-y", "--year",
        help="Filter by departures in a specific year",
        type=int,
    )

    # Index_tails
    index_parser_subparsers.add_parser(
        "tails",
        help="Display a tail number index",
    )


def _add_parsers_refresh(subparsers) -> None:
    """Adds parsers for refresh command."""
    refresh_parser = subparsers.add_parser(
        "refresh",
        help="Refresh flight log data",
    )
    refresh_parser_subparsers = refresh_parser.add_subparsers(
        dest="entity",
        required=True,
    )

    # Refresh routes
    refresh_parser_subparsers.add_parser(
        "routes",
        help="Manually refresh routes layer",
    )

def _add_parsers_report(subparsers) -> None:
    """Adds parsers for report command."""
    report_parser = subparsers.add_parser(
        "report",
        help="Generate reports",
    )
    report_parser_subparsers = report_parser.add_subparsers(
        dest="entity",
        required=True,
    )

    # Report milestones
    report_parser_subparsers.add_parser(
        "milestones",
        help="Generate a report of flying milestones"
    )

def _add_parsers_run(subparsers) -> None:
    """Adds parsers for run command."""
    run_parser = subparsers.add_parser(
        "run",
        help="Launch HTML travel log"
    )
    run_parser.add_argument("--port",
        help="Webserver port (default: %(default)s)",
        type=int,
        default=8000,
    )

def _add_parsers_show(subparsers) -> None:
    """Adds parsers for show command."""
    show_parser = subparsers.add_parser(
        "show",
        help="Show details for specific entities",
    )
    
    show_parser_subparsers = show_parser.add_subparsers(
        dest="entity",
        required=True,
    )

    # Show airport
    show_airport_parser = show_parser_subparsers.add_parser(
        "airport",
        help="Show details about an airport",
    )
    show_airport_parser.add_argument("id",
        help="Airport identifier (fid, IATA, ICAO, or FAA LID)",
        type=str,
    )

    # Show tail
    show_tail_parser = show_parser_subparsers.add_parser(
        "tail",
        help="Show details about a tail number",
    )
    show_tail_parser.add_argument("tail_number",
        help="Tail number",
        type=str,           
    )


