"""Runs a local server for browsing flight data."""

# Standard imports
from datetime import date, datetime, UTC
import os
from pathlib import Path
import webbrowser

# Third-party imports
from flask import Flask, current_app, render_template, url_for

# Project imports
from pbtravellog.flight_log import FlightTable
from pbtravellog.travel_log import TripTable
from pbtravellog.geometry import GEOJSON_HEADERS, GeoJSONMap

def create_browser_app():
    """Creates a Flask app for the travel log."""
    app = Flask(__name__)

    MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
    if MAPBOX_API_KEY is None:
        raise KeyError("Environment variable MAPBOX_API_KEY is missing.")

    app.jinja_env.filters["format_date_range"] = _format_date_range
    app.jinja_env.filters["format_dt"] = _format_dt
    app.jinja_env.filters["format_duration"] = _format_duration
    app.jinja_env.filters["format_thousands"] = _format_thousands
    app.jinja_env.globals["img_path_airline_icon"] = _img_path_airline_icon
    app.jinja_env.globals["mapbox_api_key"] = MAPBOX_API_KEY

    all_flights = FlightTable.from_all().joined().sort("departure_utc")
    all_trips = TripTable.from_all()

    @app.route("/")
    def home():
        return render_template("home.html.jinja")

    @app.route("/flights/")
    def index_flights():
        return render_template(
            "flights/index.html.jinja",
            flights=all_flights,
            flights_map=GeoJSONMap(all_flights.geojson())
        )

    @app.route("/flights/flights.geojson")
    def geojson_flights():
        return all_flights.geojson(), 200, GEOJSON_HEADERS

    @app.route("/flights/<int:flight_fid>/")
    def show_flight(flight_fid: int):
        flight = all_flights[flight_fid]
        return render_template("flights/show.html.jinja", flight=flight)

    @app.route("/aircraft_types/")
    def index_aircraft_types():
        return render_template(
            "aircraft_types/index.html.jinja",
            aircraft_types=all_flights.collect_aircraft_types(),
        )

    @app.route("/aircraft_types/<int:aircraft_type_fid>/")
    def show_aircraft_type(aircraft_type_fid: int):
        aircraft_type_records = all_flights.collect_aircraft_types()
        flights = all_flights.filter_by_aircraft_type(aircraft_type_fid)
        return render_template(
            "aircraft_types/show.html.jinja",
            aircraft_type=aircraft_type_records[aircraft_type_fid],
            airlines=flights.collect_airlines(operators=False),
            operators=flights.collect_airlines(operators=True),
            classes=flights.collect_classes(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    @app.route("/airlines/")
    def index_airlines():
        return render_template(
            "airlines/index.html.jinja",
            airlines=all_flights.collect_airlines(operators=False),
            operators=all_flights.collect_airlines(operators=True),
        )

    @app.route("/airlines/<int:airline_fid>/")
    def show_airline(airline_fid: int):
        airline_records = all_flights.collect_airlines(operators=False)
        flights = all_flights.filter_by_airline(airline_fid, operator=False)
        return render_template(
            "airlines/show.html.jinja",
            airline=airline_records[airline_fid],
            operators=flights.collect_airlines(operators=True),
            aircraft_types=flights.collect_aircraft_types(),
            classes=flights.collect_classes(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    @app.route("/airlines/operators/<int:operator_fid>/")
    def show_operator(operator_fid: int):
        operator_records = all_flights.collect_airlines(operators=True)
        flights = all_flights.filter_by_airline(operator_fid, operator=True)
        return render_template(
            "airlines/show_operator.html.jinja",
            operator=operator_records[operator_fid],
            airlines=flights.collect_airlines(operators=False),
            aircraft_types=flights.collect_aircraft_types(),
            classes=flights.collect_classes(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    @app.route("/airports/")
    def index_airports():
        airport_records = all_flights.collect_airports()
        return render_template(
            "airports/index.html.jinja",
            airports=airport_records,
        )

    @app.route("/airports/<int:airport_fid>/")
    def show_airport(airport_fid: int):
        airport_records = all_flights.collect_airports()
        flights = all_flights.filter_by_airport(
            airport_fid,
            count_cumulative=True,
        )
        return render_template(
            "airports/show.html.jinja",
            airport_fid=airport_fid,
            airport=airport_records[airport_fid],
            airlines=flights.collect_airlines(operators=False),
            operators=flights.collect_airlines(operators=True),
            aircraft_types=flights.collect_aircraft_types(),
            classes=flights.collect_classes(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    @app.route("/classes/")
    def index_classes():
        class_records = all_flights.collect_classes()
        return render_template(
            "classes/index.html.jinja",
            classes=class_records,
        )

    @app.route("/classes/<int:class_fid>/")
    def show_class(class_fid: int):
        class_records = all_flights.collect_classes()
        flights = all_flights.filter_by_class(class_fid)
        return render_template(
            "classes/show.html.jinja",
            seat_class=class_records[class_fid],
            airlines=flights.collect_airlines(operators=False),
            operators=flights.collect_airlines(operators=True),
            aircraft_types=flights.collect_aircraft_types(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    @app.route("/routes/")
    def index_routes():
        route_records = all_flights.collect_routes()
        return render_template("routes/index.html.jinja", routes=route_records)

    @app.route(
        "/routes/<int:origin_airport_fid>/<int:destination_airport_fid>/"
    )
    def show_route(origin_airport_fid, destination_airport_fid):
        route_records = all_flights.collect_routes()
        fids = (origin_airport_fid, destination_airport_fid)
        flights = all_flights.filter_by_route(*fids)
        return render_template(
            "routes/show.html.jinja",
            fids=fids,
            route=route_records[fids],
            airlines=flights.collect_airlines(operators=False),
            operators=flights.collect_airlines(operators=True),
            aircraft_types=flights.collect_aircraft_types(),
            classes=flights.collect_classes(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    @app.route("/tail_numbers/")
    def index_tail_numbers():
        return render_template(
            "tail_numbers/index.html.jinja",
            tail_numbers=all_flights.collect_tail_numbers(),
        )

    @app.route("/tail_numbers/<string:tail_number>/")
    def show_tail_number(tail_number: str):
        tail_number_records = all_flights.collect_tail_numbers()
        flights = all_flights.filter_by_tail_number(tail_number)
        return render_template(
            "tail_numbers/show.html.jinja",
            tail_number_record=tail_number_records[tail_number],
            airlines=flights.collect_airlines(operators=False),
            operators=flights.collect_airlines(operators=True),
            aircraft_types=flights.collect_aircraft_types(),
            classes=flights.collect_classes(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    @app.route("/trips/")
    def index_trips():
        trip_records = all_trips.sort("end_date", ascending=False) \
            .sort("start_date", ascending=False)
        return render_template("trips/index.html.jinja", trips=trip_records)

    @app.route("/trips/<int:trip_fid>/")
    def show_trip(trip_fid: int):
        trip = all_trips[trip_fid]
        flights = all_flights.filter_by_trip(trip_fid)
        return render_template(
            "trips/show.html.jinja",
            trip=trip,
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson(group_routes=False)),
        )

    @app.route("/years/")
    def index_years():
        flight_counts = all_flights.count_by_year()
        year_range = range(
            min([
               min(flight_counts),
            ]),
            max([
                max(flight_counts),
                datetime.now(UTC).year,
            ]) + 1,
        )
        years = {
            y: {"flights": flight_counts.get(y, 0)}
            for y in year_range
        }
        return render_template(
            "/years/index.html.jinja",
            years=years,
        )

    @app.route("/years/<int:year>/")
    def show_year(year: int):
        flights = all_flights.filter_by_year(year)
        return render_template(
            "years/show.html.jinja",
            year=year,
            airlines=flights.collect_airlines(operators=False),
            operators=flights.collect_airlines(operators=True),
            aircraft_types=flights.collect_aircraft_types(),
            classes=flights.collect_classes(),
            flights=flights,
            flights_map=GeoJSONMap(flights.geojson()),
        )

    return app


def launch(port):
    """Launches the travel log web interface."""
    app = create_browser_app()
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port)


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

def _format_duration(seconds: int | None) -> str | None:
    """Returns a flight duration string."""
    if seconds is None or seconds < 0:
        return None
    days, remainder = divmod(int(seconds), 3600*24)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    if days > 0:
        return f"{days}d {hours:02}h {minutes:02}m"
    if hours > 0:
        return f"{hours}h {minutes:02}m"
    return f"{minutes}m"

def _format_thousands(num: int | float) -> str:
    return f"{num:,}"

def _img_path_airline_icon(airline_fid: int):
    """Returns the path for an airline icon or none."""
    icon = Path(f"images/airlines/icons/{airline_fid}.png")
    full_path = Path(current_app.static_folder) / icon
    if not full_path.exists():
        return None
    return url_for("static", filename=icon.as_posix())
