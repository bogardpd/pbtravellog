"""User functions for importing flights."""

# Standard imports
from datetime import date, datetime, timezone
import os
from pathlib import Path

# Third-party imports
from shapely import LineString, MultiLineString, Point

# Project imports
from pbtravellog.aeroapi import (
    get_flights_ident, get_flights_ident_track, select_flight_info
)
from pbtravellog.boarding_pass import BoardingPass, PKPass
from pbtravellog.flight_log import (
    AirlineTable, Flight, estimate_trip_section, refresh_routes
)
from pbtravellog.geometry import METERS_PER_HUNDRED_FEET, split_at_antimeridian
from pbtravellog.travel_log import Trip

def import_flight_bcbp(bcbp_str, geojson: Path | None = None) -> None:
    """Parses a BCBP string and saves flight to log."""
    bp = BoardingPass(bcbp_str)
    bp_flights = _collect_flights_from_bp(bp)
    # Save flights.
    _save_flights(bp_flights, geojson=geojson)

def import_flight_fa_flight_id(
    fa_flight_id: str,
    geojson: Path | None = None
) -> None:
    """Gets info for a fa_flight_id and saves flight to log."""
    flight = _fetch_flight_from_ident(fa_flight_id, ident_type="fa_flight_id")
    _save_flights([flight], geojson=geojson)

def import_flight_number(
    airline_code: str,
    flight_number: str,
    geojson: Path | None = None
) -> None:
    """Gets info for a flight number and saves flight to log."""
    airline = AirlineTable.find_by_code(airline_code)
    # If airline is IATA, try to look up ICAO.
    if len(airline_code) == 2:
        if airline is not None and airline.get("icao_code") is not None:
            airline_code = airline.get("icao_code")
    flight_number = flight_number.lstrip("0") or "0"
    ident = f"{airline_code}{flight_number}"
    flight = _fetch_flight_from_ident(
        ident,
        ident_type="designator",
        airline_fid=(airline or {}).get("fid"),
    )
    _save_flights([flight], geojson=geojson)

def import_flight_pkpasses(geojson: Path | None = None) -> None:
    """Imports digital boarding passes."""

    import_folder_env = os.getenv("PBTRAVELLOG_FLIGHT_IMPORT_PATH")
    if import_folder_env is None:
        raise KeyError(
            "Environment variable PBTRAVELLOG_FLIGHT_IMPORT_PATH is missing."
        )
    import_folder = Path(import_folder_env)
    if not import_folder.is_dir():
        raise KeyError(
            "Environment variable PBTRAVELLOG_FLIGHT_IMPORT_PATH is not a "
            + "directory."
        )
    archive_folder_env = os.getenv("PBTRAVELLOG_PKPASS_ARCHIVE_PATH")
    if archive_folder_env is None:
        raise KeyError(
            "Environment variable PBTRAVELLOG_PKPASS_ARCHIVE_PATH is missing."
        )
    archive_folder = Path(archive_folder_env)
    if not archive_folder.is_dir():
        raise KeyError(
            "Environment variable PBTRAVELLOG_PKPASS_ARCHIVE_PATH is not a "
            + "directory."
        )

    print(f"Importing digital boarding passes from \"{import_folder}\"")
    pkpasses = {
        f: PKPass(f) for f in import_folder.glob("*.pkpass") if f.is_file()
    }
    if len(pkpasses) == 0:
        print("⚠️ No .pkpass files found.")

    # Sort passes by relevant_date.
    pkpasses = dict(
        sorted(
            pkpasses.items(),
            key=lambda item: item[1].relevant_date or datetime.max.replace(
                tzinfo=timezone.utc
            )
        )
    )

    # Process passes.
    flights = []
    for pkpass_file, pkpass in pkpasses.items():
        bp = pkpass.boarding_pass
        flights.extend(_collect_flights_from_bp(bp))
        archive_file_path = archive_folder / pkpass.archive_filename
        pkpass_file.move(archive_file_path)
        print(f"Archived PKPass to \"{archive_file_path}\"")
    _save_flights(flights, geojson=geojson)

def _collect_flights_from_bp(bp: BoardingPass) -> list[Flight]:
    """Builds Flights from a BoardingPass."""
    if not bp.valid or len(bp.legs) == 0:
        print("⚠️ The boarding pass data is not valid.")
        return []

    # Build list of boarding pass flights.
    bp_flights: list[Flight] = []
    for leg in bp.legs:
        print(f"Processing leg \"{leg}\"")
        airline = AirlineTable.find_by_code(leg.airline_iata)
        if airline is not None and airline.get("icao_code") is not None:
            airline_code = airline.get("icao_code")
        else:
            airline_code = leg.airline_iata
        ident = f"{airline_code}{leg.flight_number}"
        flight = _fetch_flight_from_ident(
            ident,
            ident_type="designator",
            airline_fid=(airline or {}).get("fid"),
            boarding_pass_data=bp.bcbp_str,
        )
        bp_flights.append(flight)
    return bp_flights

def _fetch_flight_from_ident(
    ident: str,
    ident_type: str | None = None,
    airline_fid: int | None = None,
    boarding_pass_data: str | None = None,
    flight_date: date | None = None,
) -> Flight | None:
    """Looks up and returns a Flight record from an ident."""
    flight_results = get_flights_ident(ident, ident_type=ident_type)
    if len(flight_results) == 0:
        search_type = "" if ident_type is None else f"{ident_type} "
        print(f"No flights matched{search_type} \"{ident}\" on AeroAPI.")
        return None
    result = select_flight_info(flight_results)
    if result is None:
        return None
    progress = result.get("progress_percent")
    if progress is None or progress < 100:
        print(
            f"⚠️ Flight is not complete ({progress}% complete). Flight was "
            "not added to log."
        )
        return None
    flight = Flight.from_aeroapi(result)
    flight["airline_fid"] = airline_fid
    flight["boarding_pass_data"] = boarding_pass_data
    geometry, distance_mi = _fetch_track_geometry(flight.get("fa_flight_id"))
    if geometry is not None:
        flight["geometry"] = geometry
        flight["geom_source"] = "FlightAware"
    flight["distance_mi"] = distance_mi
    if flight_date is None:
        flight_local_dep = flight.local_time("departure")
        if flight_local_dep is not None:
            flight_date = flight_local_dep.date()
    trip = Trip.select_by_date(flight_date)
    if trip is not None:
        flight["trip_fid"] = trip.get("fid")
        if flight.get("departure_utc") is not None:
            flight["trip_section"] = estimate_trip_section(
                trip.get("fid"), flight["departure_utc"],
            )
    return flight

def _fetch_track_geometry(fa_flight_id: str) -> tuple(
    MultiLineString | None,
    int | None
):
    """Gets geometry and distance for an fa_flight_id."""
    if fa_flight_id is None:
        print("⚠️ Cannot get track: fa_flight_id is not set.")
        return (None, None)
    fa_json = get_flights_ident_track(fa_flight_id)
    if fa_json is None:
        print(f"⚠️ No track found for {fa_flight_id}.")
        return (None, None)
    positions = fa_json.get("positions")
    if len(positions) == 0:
        print(f"⚠️ No positions found for {fa_flight_id}.")
        return (None, None)
    track_ls = LineString([Point(
        p.get("longitude"),
        p.get("latitude"),
        p.get("altitude") * METERS_PER_HUNDRED_FEET,
    ) for p in positions])
    geometry = split_at_antimeridian(track_ls)
    try:
        distance_mi = int(fa_json.get("actual_distance"))
    except TypeError, ValueError:
        distance_mi = None
        print(f"⚠️ No distance found for {fa_flight_id}.")
    return (geometry, distance_mi)

def _save_flights(flights: list[Flight], geojson: Path | None = None):
    """Saves a list of flights."""
    if geojson is None:
        for flight in flights:
            flight.save()
            flight.alert_prior_flown_tail()
    else:
        if len(flights) == 1:
            flights[0].save(geojson=geojson)
        else:
            for i, flight in enumerate(flights):
                gj_path = geojson.with_stem(f"{geojson.stem}_{i}")
                flight.save(geojson=gj_path)
    refresh_routes()
