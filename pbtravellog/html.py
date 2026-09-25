"""Builds and runs a static HTML travel log."""

# Standard imports
from collections import defaultdict
from datetime import date
from pathlib import Path
import webbrowser

# Third-party imports
from flask import Flask, current_app, render_template, url_for
import pandas as pd

# Project imports
from pbtravellog.flight_log import (
    Flight, Airport, Airline, AircraftType, SeatClass, Route
)
from pbtravellog.travel_log import Trip

def create_browser_app():
    """Creates a Flask app for the travel log."""
    app = Flask(__name__)

    app.jinja_env.filters["format_date_range"] = _format_date_range
    app.jinja_env.filters["format_dt"] = _format_dt
    app.jinja_env.globals["img_path_airline_icon"] = _img_path_airline_icon

    all_flights = Flight.joined()
    all_trips = Trip.to_dict()

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/flights/")
    def index_flights():
        return render_template("flights/index.html", flights=all_flights)

    @app.route("/flights/<int:flight_fid>/")
    def show_flight(flight_fid: int):
        flight = all_flights[flight_fid]
        return render_template("flights/show.html", flight=flight)

    @app.route("/aircraft_types/")
    def index_aircraft_types():
        aircraft_type_records = _collect_aircraft_type_records(all_flights)
        return render_template(
            "aircraft_types/index.html",
            aircraft_types=aircraft_type_records,
        )

    @app.route("/aircraft_types/<int:aircraft_type_fid>/")
    def show_aircraft_type(aircraft_type_fid: int):
        aircraft_type_records = _collect_aircraft_type_records(all_flights)
        aircraft_type = aircraft_type_records[aircraft_type_fid]
        flights = _filter_flights_by_aircraft_type(
            all_flights, aircraft_type_fid,
        )
        airlines = _collect_airline_records(flights, operators=False)
        operators = _collect_airline_records(flights, operators=True)
        classes = _collect_class_records(flights)
        return render_template(
            "aircraft_types/show.html",
            aircraft_type=aircraft_type,
            airlines=airlines,
            operators=operators,
            classes=classes,
            flights=flights,
        )

    @app.route("/airlines/")
    def index_airlines():
        airline_records = _collect_airline_records(
            all_flights, operators=False,
        )
        operator_records = _collect_airline_records(
            all_flights, operators=True,
        )
        return render_template(
            "airlines/index.html",
            airlines=airline_records,
            operators=operator_records,
        )

    @app.route("/airlines/<int:airline_fid>/")
    def show_airline(airline_fid: int):
        airline_records = _collect_airline_records(
            all_flights, operators=False,
        )
        airline = airline_records[airline_fid]
        flights = _filter_flights_by_airline(
            all_flights, airline_fid, operator=False,
        )
        operators = _collect_airline_records(flights, operators=True)
        aircraft_types = _collect_aircraft_type_records(flights)
        classes = _collect_class_records(flights)
        return render_template(
            "airlines/show.html",
            airline=airline,
            operators=operators,
            aircraft_types=aircraft_types,
            classes=classes,
            flights=flights,
        )

    @app.route("/airlines/operators/<int:operator_fid>/")
    def show_operator(operator_fid: int):
        operator_records = _collect_airline_records(
            all_flights, operators=True,
        )
        operator = operator_records[operator_fid]
        flights = _filter_flights_by_airline(
            all_flights, operator_fid, operator=True,
        )
        airlines = _collect_airline_records(flights, operators=False)
        aircraft_types = _collect_aircraft_type_records(flights)
        classes = _collect_class_records(flights)
        return render_template(
            "airlines/show_operator.html",
            operator=operator,
            airlines=airlines,
            aircraft_types=aircraft_types,
            classes=classes,
            flights=flights,
        )

    @app.route("/airports/")
    def index_airports():
        airport_records = _collect_airport_records(all_flights)
        return render_template("airports/index.html", airports=airport_records)

    @app.route("/airports/<int:airport_fid>/")
    def show_airport(airport_fid: int):
        airport_records = _collect_airport_records(all_flights)
        airport = airport_records[airport_fid]
        flights = _filter_flights_by_airport(all_flights, airport_fid)
        airlines = _collect_airline_records(flights, operators=False)
        operators = _collect_airline_records(flights, operators=True)
        aircraft_types = _collect_aircraft_type_records(flights)
        classes = _collect_class_records(flights)
        return render_template(
            "airports/show.html",
            airport_fid=airport_fid,
            airport=airport,
            airlines=airlines,
            operators=operators,
            aircraft_types=aircraft_types,
            classes=classes,
            flights=flights,
        )

    @app.route("/classes/")
    def index_classes():
        class_records = _collect_class_records(all_flights)
        return render_template("classes/index.html", classes=class_records)

    @app.route("/classes/<int:class_fid>/")
    def show_class(class_fid: int):
        class_records = _collect_class_records(all_flights)
        seat_class = class_records[class_fid]
        flights = _filter_flights_by_class(all_flights, class_fid)
        airlines = _collect_airline_records(flights, operators=False)
        operators = _collect_airline_records(flights, operators=True)
        aircraft_types = _collect_aircraft_type_records(flights)
        return render_template(
            "classes/show.html",
            seat_class=seat_class,
            airlines=airlines,
            operators=operators,
            aircraft_types=aircraft_types,
            flights=flights,
        )

    @app.route("/routes/")
    def index_routes():
        route_records = _collect_route_records(all_flights)
        return render_template("routes/index.html", routes=route_records)

    @app.route(
        "/routes/<int:origin_airport_fid>/<int:destination_airport_fid>/"
    )
    def show_route(origin_airport_fid, destination_airport_fid):
        route_records = _collect_route_records(all_flights)
        fids = (origin_airport_fid, destination_airport_fid)
        route = route_records[fids]
        flights = _filter_flights_by_route(all_flights, *fids)
        airlines = _collect_airline_records(flights, operators=False)
        operators = _collect_airline_records(flights, operators=True)
        aircraft_types = _collect_aircraft_type_records(flights)
        classes = _collect_class_records(flights)
        return render_template(
            "routes/show.html",
            fids=fids,
            route=route,
            airlines=airlines,
            operators=operators,
            aircraft_types=aircraft_types,
            classes=classes,
            flights=flights,
        )

    @app.route("/tail_numbers/")
    def index_tail_numbers():
        tail_number_records = _collect_tail_number_records(all_flights)
        return render_template(
            "/tail_numbers/index.html",
            tail_numbers=tail_number_records,
        )

    @app.route("/tail_numbers/<string:tail_number>/")
    def show_tail_number(tail_number: str):
        tail_number_records = _collect_tail_number_records(all_flights)
        tail_number_record = tail_number_records[tail_number]
        flights = _filter_flights_by_tail_number(all_flights, tail_number)
        airlines = _collect_airline_records(flights, operators=False)
        operators = _collect_airline_records(flights, operators=True)
        aircraft_types = _collect_aircraft_type_records(flights)
        classes = _collect_class_records(flights)
        return render_template(
            "tail_numbers/show.html",
            tail_number_record=tail_number_record,
            airlines=airlines,
            operators=operators,
            aircraft_types=aircraft_types,
            classes=classes,
            flights=flights,
        )

    @app.route("/trips/")
    def index_trips():
        return render_template("trips/index.html", trips=all_trips)

    @app.route("/trips/<int:trip_fid>/")
    def show_trip(trip_fid: int):
        trip = all_trips[trip_fid]
        flights = _filter_flights_by_trip(all_flights, trip_fid)
        return render_template("trips/show.html", trip=trip, flights=flights)

    return app


def run(port):
    """Launches the travel log web interface."""
    app = create_browser_app()
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port)

def _collect_aircraft_type_records(flight_records) -> dict[dict]:
    """Builds aircraft type records from flight records."""
    aircraft_type_flight_count = defaultdict(int)
    for _, flight in flight_records.items():
        aircraft_type_flight_count[flight["aircraft_type_fid"]] += 1
    aircraft_type_flight_count.pop(None, None) # Remove None count
    ranks = _rank_count(aircraft_type_flight_count)
    aircraft_type_records = {}
    all_aircraft_types = AircraftType.all()
    for aircraft_type_fid, count in aircraft_type_flight_count.items():
        aircraft_type_row = all_aircraft_types.loc[aircraft_type_fid]
        record = {
            "manufacturer": aircraft_type_row["manufacturer"],
            "name": aircraft_type_row["name"],
            "iata_code": aircraft_type_row["iata_code"],
            "icao_code": aircraft_type_row["icao_code"],
            "count": count,
            "rank": ranks[aircraft_type_fid],
        }
        record = {
            k: (None if pd.isna(v) else v) for k, v in record.items()
        }
        aircraft_type_records[aircraft_type_fid] = record
    aircraft_type_records = dict(sorted(
        aircraft_type_records.items(),
        key=lambda x: (-x[1]["count"], x[1]["manufacturer"], x[1]["name"])
    ))
    return aircraft_type_records

def _collect_airline_records(
    flight_records, operators=False,
) -> dict[dict]:
    """Builds airline records from flight records."""
    column = "operator_fid" if operators else "airline_fid"
    airline_flight_count = defaultdict(int)
    for _, flight in flight_records.items():
        airline_flight_count[flight[column]] += 1
    airline_flight_count.pop(None, None) # Remove None count
    all_airlines = Airline.all()
    ranks = _rank_count(airline_flight_count)
    airline_records = {}
    for airline_fid, count in airline_flight_count.items():
        airline_row = all_airlines.loc[airline_fid]
        record = {
            "name": airline_row["name"],
            "iata_code": airline_row["iata_code"],
            "icao_code": airline_row["icao_code"],
            "count": count,
            "rank": ranks[airline_fid],
        }
        record = {
            k: (None if pd.isna(v) else v) for k, v in record.items()
        }
        airline_records[airline_fid] = record
    airline_records = dict(sorted(
        airline_records.items(), key=lambda x: (-x[1]["count"], x[1]["name"])
    ))
    return airline_records

def _collect_airport_records(flight_records) -> dict[dict]:
    """Builds airport records from flight records."""
    airport_visit_count = defaultdict(int)
    prev_trip_sec = [None, None]
    for _, flight in flight_records.items():
        curr_trip_sec = [flight["trip_fid"], flight["trip_section"]]
        if curr_trip_sec != prev_trip_sec:
            # This is not following a layover, so count the origin.
            airport_visit_count[flight["origin_airport_fid"]] += 1
        airport_visit_count[flight["destination_airport_fid"]] += 1
        prev_trip_sec = curr_trip_sec
    airport_visit_count.pop(None, None) # Remove None count
    ranks = _rank_count(airport_visit_count)
    airport_records = {}
    all_airports = Airport.all()
    for airport_fid, visits in airport_visit_count.items():
        airport_row = all_airports.loc[airport_fid]
        record = {
            "name": airport_row["name"],
            "iata_code": airport_row["iata_code"],
            "icao_code": airport_row["icao_code"],
            "faa_lid": airport_row["faa_lid"],
            "visits": visits,
            "rank": ranks[airport_fid],
        }
        record = {
            k: (None if pd.isna(v) else v) for k, v in record.items()
        }
        airport_records[airport_fid] = record
    airport_records = dict(sorted(
        airport_records.items(), key=lambda x: (-x[1]["visits"], x[1]["name"]),
    ))
    return airport_records

def _collect_class_records(flight_records) -> dict[dict]:
    """Builds flight class records from flight records."""
    class_flight_count = defaultdict(int)
    for _, flight in flight_records.items():
        class_flight_count[flight["class_fid"]] += 1
    class_flight_count.pop(None, None) # Remove none count
    # Classes are always sorted by quality, so no need to rank.
    class_records = {}
    all_classes = SeatClass.all()
    for class_fid, count in class_flight_count.items():
        class_row = all_classes.loc[class_fid]
        record = {
            "quality": class_row["quality"],
            "name": class_row["name"],
            "description": class_row["description"],
            "count": count,
        }
        record = {
            k: (None if pd.isna(v) else v) for k, v in record.items()
        }
        class_records[class_fid] = record
    class_records = dict(sorted(
        class_records.items(), key=lambda x: -x[1]["quality"],
    ))
    return class_records

def _collect_route_records(flight_records) -> dict[dict]:
    """Builds route records from flight records.

    Although routes already store their flight_count, the value is
    only good for all flights. This method calculates routes for
    whatever flights are passed into it.
    """
    route_flight_count = defaultdict(int)
    route_codes = {}
    for _, flight in flight_records.items():
        airport_fids = (
            flight["origin_airport_fid"],
            flight["destination_airport_fid"],
        )
        route_flight_count[airport_fids] += 1
        route_codes[airport_fids] = (
            flight["origin_airport_code"],
            flight["destination_airport_code"],
        )
    ranks = _rank_count(route_flight_count)
    route_lookup = Route.all().copy() \
        .set_index(["origin_airport_fid", "destination_airport_fid"])
    route_records = {}
    for route_fids, count in route_flight_count.items():
        route_row = route_lookup.loc[route_fids]
        if pd.isna(route_row["distance_mi"]):
            distance = None
        else:
            distance = int(route_row["distance_mi"])
        record = {
            "origin_airport_code": route_codes[route_fids][0],
            "destination_airport_code": route_codes[route_fids][1],
            "distance_mi": distance,
            "count": count,
            "rank": ranks[route_fids],
        }
        route_records[route_fids] = record
    route_records = dict(sorted(
        route_records.items(),
        key=lambda x: (
            -x[1]["count"],
            x[1]["origin_airport_code"],
            x[1]["destination_airport_code"]
        )
    ))
    return route_records

def _collect_tail_number_records(flight_records) -> dict[dict]:
    """Builds tail number records from flight records."""
    tail_flight_count = defaultdict(int)
    equipment = {}
    for _, flight in flight_records.items():
        tail_flight_count[flight["tail_number"]] += 1
        equipment[flight["tail_number"]] = flight["aircraft_type_name"]
    tail_flight_count.pop(None, None) # Remove None count
    ranks = _rank_count(tail_flight_count)
    tail_number_records = {}
    for tail_number, count in tail_flight_count.items():
        record = {
            "formatted": Flight.format_tail_number(tail_number),
            "aircraft_type_name": equipment[tail_number],
            "count": count,
            "rank": ranks[tail_number],
        }
        tail_number_records[tail_number] = record
    tail_number_records = dict(sorted(
        tail_number_records.items(),
        key=lambda x: (-x[1]["count"], x[0]),
    ))
    return tail_number_records

def _filter_flights_by_aircraft_type(
    flight_records, aircraft_type_fid: int,
) -> dict[dict]:
    """Filters flight records by an aircraft type."""
    records = {
        k: v for k, v in flight_records.items()
        if v["aircraft_type_fid"] == aircraft_type_fid
    }
    return records

def _filter_flights_by_airline(
    flight_records, airline_fid: int, operator=False,
) -> dict[dict]:
    """Filters flight records by an airline."""
    column = "operator_fid" if operator else "airline_fid"
    records = {
        k: v for k, v in flight_records.items()
        if v[column] == airline_fid
    }
    return records

def _filter_flights_by_airport(flight_records, airport_fid: int) -> dict[dict]:
    """Filters flight records by an airport."""
    records = {
        k: v for k, v in flight_records.items()
        if airport_fid in [
            v["origin_airport_fid"],
            v["destination_airport_fid"],
        ]
    }
    return records

def _filter_flights_by_class(flight_records, class_fid: int) -> dict[dict]:
    """Filters flight records by a flight class."""
    records = {
        k: v for k, v in flight_records.items()
        if v["class_fid"] == class_fid
    }
    return records

def _filter_flights_by_route(
    flight_records, orig_fid: int, dest_fid: int
) -> dict[dict]:
    """Filters flight records by a route."""
    records = {
        k: v for k, v in flight_records.items()
        if v["origin_airport_fid"] == orig_fid
        and v["destination_airport_fid"] == dest_fid
    }
    return records

def _filter_flights_by_tail_number(
    flight_records, tail_number: str,
) -> dict[dict]:
    """Filters flight records by a tail number."""
    records = {
        k: v for k, v in flight_records.items()
        if v["tail_number"] == tail_number
    }
    return records

def _filter_flights_by_trip(flight_records, trip_fid: int) -> dict[dict]:
    """Filters flight records by a trip."""
    records = {
        k: v for k, v in flight_records.items()
        if v["trip_fid"] == trip_fid
    }
    return records

def _format_date_range(dates: list[date]) -> str:
    """Formats a date range."""
    if dates[0].year != dates[1].year:
        return "–".join([
            dates[0].strftime("%d %b %Y"), dates[1].strftime("%d %b %Y"),
        ])
    if dates[0].month != dates[1].month:
        return "–".join([
            dates[0].strftime("%d %b"), dates[1].strftime("%d %b %Y"),
        ])
    if dates[0].day != dates[1].day:
        return "–".join([
            dates[0].strftime("%d"), dates[1].strftime("%d %b %Y"),
        ])
    return dates[1].strftime("%d %b %Y")

def _format_dt(dt, include_time=True, include_tz=False) -> str:
    """Formats a datetime."""
    if dt is None:
        return ""
    parts = ["%d %b %Y"]
    if include_time:
        parts.append("%H:%M")
    if include_tz:
        parts.append("%Z")
    return dt.strftime(" ".join(parts))

def _img_path_airline_icon(airline_fid: int):
    """Returns the path for an airline icon or none."""
    icon = Path(f"images/airlines/icons/{airline_fid}.png")
    full_path = Path(current_app.static_folder) / icon
    if not full_path.exists():
        return None
    return url_for("static", filename=icon.as_posix())

def _rank_count(count_dict: dict) -> dict:
    """Ranks a dictionary of item counts."""
    sorted_count = sorted(count_dict.items(), key=lambda x: -x[1])
    ranks = dict()
    prev_count = None
    prev_rank = 0
    for idx, (key, count) in enumerate(sorted_count):
        rank = prev_rank if count == prev_count else idx + 1
        ranks[key] = rank
        prev_count = count
        prev_rank = rank
    return ranks
