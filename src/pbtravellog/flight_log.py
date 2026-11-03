"""Domain logic for flight log records."""

# Standard imports
from collections import defaultdict
from datetime import datetime, timedelta
from importlib.resources import files
import os
import re
import tomllib
from typing import Self
from zoneinfo import ZoneInfo

# Third-party imports
from dateutil.parser import isoparse

# Project imports
from pbtravellog.geometry import gc_distance, geo_interface, great_circle_route
from pbtravellog.record import Record, RecordTable, RecordLayerTable
from pbtravellog.travel_log import TripTable

FLIGHT_DATA_FILE_ENV = "PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH"
with open(files("pbtravellog.config").joinpath("config.toml"), "rb") as f:
    CONFIG = tomllib.load(f)

def _get_flight_log():
    """Gets current value of flight log path.

    Needed to ensure tests aren't using stale environment variables.
    """
    flight_log = os.getenv("PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH")
    if flight_log is None:
        raise KeyError(
            "Environment variable PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH is "
            "missing."
        )
    return flight_log

class AircraftType(Record):
    """Represents an aircraft type record."""
    LOG_TYPE = "flight"
    LAYER = "aircraft_types"
    FIND_BY_CODES = ["icao_code"]
    DTYPES = {
        "iata_code": "string",
        "icao_code": "string",
    }

    def full_name(self) -> str:
        """Returns manufacturer and name."""
        mfr = self.get("manufacturer")
        name = self.get("name")
        if mfr is None or name.startswith(mfr):
            return name
        return f"{mfr} {name}"

class AircraftTypeTable(RecordLayerTable):
    """Represents a dict of AircraftType instances."""
    RECORD_CLASS = AircraftType

class Airline(Record):
    """Represents an airline record."""
    LOG_TYPE = "flight"
    LAYER = "airlines"
    FIND_BY_CODES = ["icao_code", "iata_code"]
    DTYPES = {
        "iata_code": "string",
        "icao_code": "string",
        "numeric_code": "string",
    }

class AirlineTable(RecordLayerTable):
    """Represents a dict of Airline instances."""
    RECORD_CLASS = Airline

class Airport(Record):
    """Represents an airport record."""
    LOG_TYPE="flight"
    LAYER = "airports"
    FIND_BY_CODES = ["icao_code", "iata_code", "faa_lid"]
    GEOM_FIELD = "geometry"
    DTYPES = {
        "iata_code": "string",
        "icao_code": "string",
        "faa_lid": "string",
    }

    def code(self) -> str:
        """Returns the best code for the airport."""
        return self.get("iata_code") or self.get("icao_code") \
            or self.get("faa_lid")

    def geojson_feature(self) -> dict:
        """Returns airport as a dict in GeoJSON feature structure."""
        gj = {
            "type": "Feature",
            "geometry": self["geometry"].__geo_interface__,
            "properties": {
                "airport_fid": self["fid"],
                "airport_name": self["name"],
                "airport_code": self.code(),
            }
        }
        return gj

    def iata_or_name(self) -> str:
        """Returns IATA code, or name if no IATA code."""
        return self.get("iata_code") or self.get("name")

class AirportTable(RecordLayerTable):
    """Represents a dict of Airport instances."""
    RECORD_CLASS = Airport
    PRINT_COLS = {
        "name": "name",
        "iata": "iata_code",
        "icao": "icao_code",
        "faa": "faa_lid",
        "visits": "visits",
        "rank": "rank",
    }

    def geojson(self) -> dict:
        """Returns airport records as a dict in GeoJSON structure."""
        gj = {
            "type": "FeatureCollection",
            "features": [a.geojson_feature() for a in self.values()]
        }
        return gj

class Flight(Record):
    """Represents a flight record."""
    LOG_TYPE = "flight"
    LAYER = "flights"
    FIND_BY_CODES = []
    DTYPES = {
        "fh_id": "Int64",
        "airline_fid": "Int64",
        "origin_airport_fid": "Int64",
        "destination_airport_fid": "Int64",
        "class_fid": "Int64",
        "operator_fid": "Int64",
        "codeshare_airline_fid": "Int64",
        "trip_fid": "Int64",
        "trip_section": "Int64",
        "distance_mi": "Int64",
        "tail_number": "string",
        "boarding_pass_data": "string",
        "geom_source": "string",
    }
    GEOM_FIELD = "geometry"
    GPKG_FORMAT_FIELDS = {
        "departure_utc": "datetime",
        "arrival_utc": "datetime",
        "fa_json": "json",
    }

    def alert_prior_flown_tail(self) -> int:
        """Prints alert if this flight's tail has been flown before.

        Returns count of flights using the tail number, or 0 if this
        flight has no tail number.
        """
        tail_number = self.get("tail_number")
        if tail_number is None:
            return 0
        all_flights = FlightTable.from_all()
        matching_tail = all_flights.filter_by_tail_number(tail_number)
        tail_count = len(matching_tail)
        if tail_count > 1:
            print(f"You've had {tail_count} flights on tail {tail_number}!")
        return tail_count

    def distance(self) -> int | None:
        """Returns flight distance or great circle distance in miles."""
        flown_distance = self.get("distance_mi")
        if flown_distance is not None:
            return flown_distance
        orig_airport = self.get("origin_airport")
        dest_airport = self.get("destination_airport")
        if orig_airport is None or dest_airport is None:
            return None
        orig_point = orig_airport.get("geometry")
        dest_point = dest_airport.get("geometry")
        if orig_point is None or dest_point is None:
            return None
        return gc_distance(orig_point, dest_point)

    def duration(self) -> int | None:
        """Returns flight duration in seconds."""
        if self["arrival_utc"] is None:
            return None
        return (self["arrival_utc"] - self["departure_utc"]).total_seconds()

    def geojson(self) -> dict:
        """Returns a single flight as a dict in GeoJSON structure."""
        airports = [
            self.get(a) for a in ["origin_airport", "destination_airport"]
            if a is not None
        ]
        airport_features = {a["fid"]: a.geojson_feature() for a in airports}
        gj = {
            "type": "FeatureCollection",
            "features": [*airport_features.values(), self.geojson_feature()]
        }
        return gj

    def geojson_feature(self) -> dict:
        """Returns flight as a dict in GeoJSON feature structure."""
        dist_mi, geom = (self.get("dist_mi"), self.get("geometry"))
        if geom is None or dist_mi is None:
            orig = self.get("origin_airport")
            dest = self.get("destination_airport")
            if orig is not None and dest is not None:
                gc_dist_mi, gc_geom = great_circle_route(
                    orig["geometry"], dest["geometry"]
                )
                if geom is None:
                    geom = gc_geom
                if dist_mi is None:
                    dist_mi = gc_dist_mi
        gj = {
            "type": "Feature",
            "geometry": geo_interface(geom),
            "properties": {
                "flight_fid": self["fid"],
                "flight_name": self.name(),
                "flight_origin_airport_fid": self["origin_airport_fid"],
                "flight_destination_airport_fid": self[
                    "destination_airport_fid"
                ],
                "flight_dist_mi": dist_mi,
                "flight_departure_utc": self["departure_utc"],
            }
        }
        return gj

    def local_time(self, loc) -> datetime:
        """Returns local departure or arrival time.

        Calculates the time in the local time zone for the departure or
        arrival airport.

        Args:
            loc (str): "departure" or "arrival".
        """
        fields = {"departure": "origin", "arrival": "destination"}
        if loc not in fields:
            raise ValueError("Location must be 'departure' or 'arrival'.")
        dt = self.get(f"{loc}_utc")
        airport = self.get(f"{fields[loc]}_airport")
        if airport is None:
            column = f"{fields[loc]}_airport_fid"
            airport = AirportTable.from_all().get(self.get(column))
        if dt is None or airport is None:
            return None
        tz = airport.get("time_zone")
        if tz is None:
            return None
        return dt.astimezone(ZoneInfo(tz))

    def name(self) -> str:
        """Returns a name for the flight."""
        if self.get("airline") is None or self["airline"].get("name") is None:
            return "Unnamed flight"
        if self["flight_number"] is None:
            return self["airline"]["name"]
        return f"{self["airline"]["name"]} {self["flight_number"]}"

    def tail_number_formatted(self) -> str:
        """Returns the flight's formatted tail number."""
        return self.format_tail_number(self.get("tail_number"))

    def _arr_utc(self) -> datetime | None:
        """Gets the actual arrival time of a flight."""
        if self.get("actual_in") is None:
            # Flights diverted to a different airport use estimated_in.
            if self.get("progress") == 100:
                return self.get("estimated_in")
            return None
        return self.get("actual_in")

    def _dep_utc(self) -> datetime | None:
        """Gets the actual departure time of a flight."""
        return self.get("actual_out")

    @classmethod
    def format_tail_number(cls, tail: str | None) -> str | None:
        """Formats a tail number in its country format."""
        if tail is None:
            return None
        if re.match(r"N", tail): # United States
            return tail
        if re.match(r"C", tail): # Canada
            return f"{tail[0]}-{tail[1:]}"
        if re.match(r"D", tail): # Germany
            return f"{tail[0]}-{tail[1:]}"
        if re.match(r"G", tail): # United Kingdom
            return f"{tail[0]}-{tail[1:]}"
        if re.match(r"J[AR]", tail): # Japan
            return tail
        if re.match(r"OH", tail): # Finland
            return f"{tail[0:2]}-{tail[2:]}"
        if re.match(r"TF", tail): # Iceland
            return f"{tail[0:2]}-{tail[2:]}"
        if re.match(r"VH", tail): # Australia
            return f"{tail[0:2]}-{tail[2:]}"
        if re.match(r"Z[KLM]", tail): # New Zealand
            return f"{tail[0:2]}-{tail[2:]}"
        return tail

    @classmethod
    def from_aeroapi(cls, fa_json: dict) -> Self:
        """Loads flight values from an AeroAPI response."""
        flight = cls()
        try:
            flight["progress"] = int(fa_json.get("progress_percent"))
        except TypeError, ValueError:
            pass
        # Store fa_json as list containing dict because some flight
        # records (such as diverts) may require more than one AeroAPI
        # JSON result stored in the database.
        flight["fa_json"] = [fa_json]
        flight["ident"] = fa_json.get("ident")
        flight["scheduled_out"] = cls.parse_dt(fa_json.get("scheduled_out"))
        flight["estimated_out"] = cls.parse_dt(fa_json.get("estimated_out"))
        flight["actual_out"] = cls.parse_dt(fa_json.get("actual_out"))
        flight["scheduled_in"] = cls.parse_dt(fa_json.get("scheduled_in"))
        flight["estimated_in"] = cls.parse_dt(fa_json.get("estimated_in"))
        flight["actual_in"] = cls.parse_dt(fa_json.get("actual_in"))
        flight["departure_utc"] = flight._dep_utc()
        flight["arrival_utc"] = flight._arr_utc()
        flight["flight_number"] = fa_json.get("flight_number")
        flight["tail_number"] = fa_json.get("registration")
        flight["fa_flight_id"] = fa_json.get("fa_flight_id")
        # Joined airports
        orig = fa_json.get("origin", {})
        orig_airport = AirportTable.find_by_code(orig.get("code"))
        flight["origin_airport_fid"] = (orig_airport or {}).get("fid")
        flight["origin_code"] = orig.get("code_iata") or orig.get("code")
        flight["origin_tz"] = orig.get("timezone")
        dest = fa_json.get("destination", {})
        dest_airport = AirportTable.find_by_code(dest.get("code"))
        flight["destination_airport_fid"] = (dest_airport or {}).get("fid")
        flight["destination_code"] = dest.get("code_iata") or dest.get("code")
        flight["destination_tz"] = dest.get("timezone")
        # Joined aircraft
        aircraft = AircraftTypeTable.find_by_code(fa_json.get("aircraft_type"))
        flight["aircraft_type_fid"] = (aircraft or {}).get("fid")
        # Joined operator
        operator = AirlineTable.find_by_code(fa_json.get("operator"))
        flight["operator_fid"] = (operator or {}).get("fid")
        return flight

    @staticmethod
    def parse_dt(dt_str) -> datetime | None:
        """Parses a datetime string."""
        if dt_str is None:
            return None
        return isoparse(dt_str)

class FlightTable(RecordLayerTable):
    """Represents a dict of Flight instances."""
    RECORD_CLASS = Flight
    PRINT_COLS = {
        "departure": lambda f: f.local_time("departure"),
        "name": lambda f: f.name(),
        "orig": lambda f: f["origin_airport"].code(),
        "dest": lambda f: f["destination_airport"].code(),
    }

    def collect_aircraft_types(self) -> AircraftTypeTable:
        """Builds aircraft type records from this FlightTable."""
        aircraft_type_flight_count = defaultdict(int)
        for _, flight in self.sort("departure_utc").items():
            aircraft_type_flight_count[flight["aircraft_type_fid"]] += 1
        aircraft_type_flight_count.pop(None, None) # Remove None count
        ranks = _rank_count(aircraft_type_flight_count)
        aircraft_types = AircraftTypeTable.from_fids(
            aircraft_type_flight_count.keys()
        )
        for aircraft_type_fid, aircraft_type in aircraft_types.items():
            aircraft_type["count"] = aircraft_type_flight_count[aircraft_type_fid]
            aircraft_type["rank"] = ranks[aircraft_type_fid]
        aircraft_types = aircraft_types.sort("name").sort("manufacturer") \
            .sort("count", ascending=False)
        return aircraft_types

    def collect_airlines(self, operators: bool = False) -> AirlineTable:
        """Builds airline records from this FlightTable."""
        column = "operator_fid" if operators else "airline_fid"
        airline_flight_count = defaultdict(int)
        for _, flight in self.sort("departure_utc").items():
            airline_flight_count[flight[column]] += 1
        airline_flight_count.pop(None, None) # Remove None count
        ranks = _rank_count(airline_flight_count)
        airlines = AirlineTable.from_fids(airline_flight_count.keys())
        for airline_fid, airline in airlines.items():
            airline["count"] = airline_flight_count[airline_fid]
            airline["rank"] = ranks[airline_fid]
        airlines = airlines.sort("name").sort("count", ascending=False)
        return airlines

    def collect_airports(self) -> AirportTable:
        """Builds airport records from this FlightTable."""
        airport_visit_count = defaultdict(int)
        # Start with an empty list. [None, None] would cause miscounts
        # if the first flight had no trip or section.
        prev_trip_sec = []
        for _, flight in self.sort("departure_utc").items():
            curr_trip_sec = [flight["trip_fid"], flight["trip_section"]]
            if curr_trip_sec != prev_trip_sec:
                # This is not following a layover, so count the origin.
                airport_visit_count[flight["origin_airport_fid"]] += 1
            airport_visit_count[flight["destination_airport_fid"]] += 1
            prev_trip_sec = curr_trip_sec
        airport_visit_count.pop(None, None) # Remove None count
        ranks = _rank_count(airport_visit_count)
        airports = AirportTable.from_fids(airport_visit_count.keys())
        for airport_fid, airport in airports.items():
            airport["visits"] = airport_visit_count[airport_fid]
            airport["rank"] = ranks[airport_fid]
        airports = airports.sort("name").sort("visits", ascending=False)
        return airports

    def collect_classes(self) -> SeatClassTable:
        """Builds flight class records from this FlightTable."""
        seat_class_flight_count = defaultdict(int)
        for _, flight in self.sort("departure_utc").items():
            seat_class_flight_count[flight["class_fid"]] += 1
        seat_class_flight_count.pop(None, None) # Remove none count
        # Classes are always sorted by quality, so no need to rank.
        seat_classes = SeatClassTable.from_fids(seat_class_flight_count.keys())
        for seat_class_fid, seat_class in seat_classes.items():
            seat_class["count"] = seat_class_flight_count[seat_class_fid]
        seat_classes = seat_classes.sort("quality", ascending=False)
        return seat_classes

    def collect_routes(self) -> RouteTable:
        """Builds route records from this FlightTable.

        Although routes already store their flight_count, the value is
        only good for all flights. This method calculates routes for
        whatever flights are passed into it.
        """
        route_flight_count = defaultdict(int)
        for _, flight in self.sort("departure_utc").items():
            airport_fids = (
                flight["origin_airport_fid"],
                flight["destination_airport_fid"],
            )
            route_flight_count[airport_fids] += 1
        ranks = _rank_count(route_flight_count)
        airports = AirportTable.from_all()
        route_records = {}
        for airport_fids, count in route_flight_count.items():
            orig_airport = airports[airport_fids[0]]
            dest_airport = airports[airport_fids[1]]
            record = {
                "origin_airport": orig_airport,
                "destination_airport": dest_airport,
                "origin_airport_code": orig_airport.code(),
                "destination_airport_code": dest_airport.code(),
                "distance_mi": gc_distance(
                    orig_airport["geometry"], dest_airport["geometry"]
                ),
                "count": count,
                "rank": ranks[airport_fids]
            }
            route_records[airport_fids] = record
        routes = RouteTable(route_records)
        routes = routes.sort("destination_airport_code") \
            .sort("origin_airport_code").sort("count", ascending=False)
        return routes

    def collect_tail_numbers(self) -> TailNumberTable:
        """Builds tail number records from flight records."""
        tail_flight_count = defaultdict(int)
        aircraft_types = {}
        for _, flight in self.sort("departure_utc").items():
            tn = flight["tail_number"]
            tail_flight_count[tn] += 1
            aircraft_types[tn] = flight.get("aircraft_type")
        tail_flight_count.pop(None, None) # Remove None count
        ranks = _rank_count(tail_flight_count)
        tail_number_records = {}
        for tail_number, count in tail_flight_count.items():
            record = {
                "formatted": Flight.format_tail_number(tail_number),
                "aircraft_type": aircraft_types[tail_number],
                "count": count,
                "rank": ranks[tail_number],
            }
            tail_number_records[tail_number] = record
        tail_number_records = TailNumberTable(sorted(
            tail_number_records.items(),
            key=lambda x: (-x[1]["count"], x[0]),
        ))
        return tail_number_records

    def count_by_year(self) -> dict:
        """Counts flights departing in each year."""
        year_flight_count = defaultdict(int)
        for _, flight in self.items():
            year_flight_count[flight["departure_utc"].year] += 1
        return year_flight_count

    def filter_by_aircraft_type(self, aircraft_type_fid: int) -> Self:
        """Filters flight records by a trip."""
        records = {
            k: v for k, v in self.items()
            if v["aircraft_type_fid"] == aircraft_type_fid
        }
        return self.__class__(records)

    def filter_by_airline(self,
        airline_fid: int,
        operator: bool = False,
    ) -> Self:
        """Filters flight records by an airline."""
        column = "operator_fid" if operator else "airline_fid"
        records = {
            k: v for k, v in self.items()
            if v[column] == airline_fid
        }
        return self.__class__(records)

    def filter_by_airport(self,
        airport_fid: int,
        count_cumulative: bool = False,
    ) -> Self:
        """Filters flight records by an airport."""
        records = {
            k: v for k, v in self.items()
            if airport_fid in [
                v["origin_airport_fid"],
                v["destination_airport_fid"],
            ]
        }
        if count_cumulative:
            cumulative_visits = 0
            prev_trip_sec = []
            for v in records.values():
                curr_trip_sec = [v['trip_fid'], v['trip_section']]
                if v["origin_airport_fid"] == airport_fid:
                    if v["trip_fid"] is None or curr_trip_sec != prev_trip_sec:
                        cumulative_visits += 1
                if v["destination_airport_fid"] == airport_fid:
                    cumulative_visits += 1
                v["cumulative_visits"] = cumulative_visits
                prev_trip_sec = curr_trip_sec

        return self.__class__(records)

    def filter_by_class(self, class_fid: int) -> Self:
        """Filters flight records by a flight class."""
        records = {
            k: v for k, v in self.items()
            if v["class_fid"] == class_fid
        }
        return self.__class__(records)

    def filter_by_route(self, orig_fid: int, dest_fid: int) -> Self:
        """Filters flight records by a route."""
        records = {
            k: v for k, v in self.items()
            if v["origin_airport_fid"] == orig_fid
            and v["destination_airport_fid"] == dest_fid
        }
        return self.__class__(records)

    def filter_by_tail_number(self, tail_number: str) -> Self:
        """Filters flight records by a tail number."""
        records = {
            k: v for k, v in self.items()
            if v["tail_number"] == tail_number
        }
        return self.__class__(records)

    def filter_by_trip(self, trip_fid: int) -> Self:
        """Filters flight records by a trip."""
        records = {
            k: v for k, v in self.items()
            if v["trip_fid"] == trip_fid
        }
        return self.__class__(records)

    def filter_by_year(self, year: int) -> Self:
        """Filters flight records by UTC departure year."""
        records = {
            k: v for k, v in self.items()
            if v["departure_utc"].year == year
        }
        return self.__class__(records)

    def geojson(self,
        group_routes: bool = True,
        include_airports: bool = True,
    ) -> dict:
        """Returns flight records as a dict in GeoJSON structure.

        Args:
            group_routes (bool, optional): If True, consolidates flights
                which share routes into single features with great
                circle geometry. If False, individual flights are added
                as features with actual geometry if available, or great
                circle paths if actual geometry is not available.
            include_airports (bool, optional): If true, includes point
                geometry for the airports associated with these flights
                or routes.
        """
        airports = {}
        routes = {}
        count_total = defaultdict(int)
        count_forward = defaultdict(int)
        count_reverse = defaultdict(int)
        for idx, flight in enumerate(self.values()):
            orig_fid = flight["origin_airport_fid"]
            dest_fid = flight["destination_airport_fid"]
            orig = flight["origin_airport"]
            dest = flight["destination_airport"]
            flight_airports = [(orig_fid, orig), (dest_fid, dest)]
            if include_airports:
                for a_fid, a in flight_airports:
                    if a_fid not in airports:
                        airports[a_fid] = a.geojson_feature()
            if group_routes:
                route_key = tuple(sorted([orig_fid, dest_fid]))
                count_total[route_key] += 1
                if route_key == tuple([orig_fid, dest_fid]):
                    count_forward[route_key] += 1
                else:
                    count_reverse[route_key] += 1
                if route_key not in routes:
                    dist_mi, geom = great_circle_route(
                        orig["geometry"], dest["geometry"]
                    )
                    feature = {
                        "type": "Feature",
                        "geometry": geo_interface(geom),
                        "properties": {
                            "route_airport0": route_key[0],
                            "route_airport1": route_key[1],
                            "route_dist_mi": dist_mi,
                        }
                    }
                    routes[route_key] = feature
                for k, v in routes.items():
                    v["properties"]["count_total"] = count_total[k]
                    v["properties"]["count_forward"] = count_forward[k]
                    v["properties"]["count_reverse"] = count_reverse[k]
            else:
                routes[idx] = flight.geojson_feature()
        gj = {
            "type": "FeatureCollection",
            "features": [*airports.values(), *routes.values()],
        }
        return gj

    def joined(self) -> Self:
        """Joins other classes on fid fields."""
        airports = AirportTable.from_all()
        airlines = AirlineTable.from_all()
        aircraft_types = AircraftTypeTable.from_all()
        classes = SeatClassTable.from_all()
        trips = TripTable.from_all()
        joins = [
            (airports, "origin_airport_fid", "origin_airport"),
            (airports, "destination_airport_fid", "destination_airport"),
            (airlines, "airline_fid", "airline"),
            (airlines, "operator_fid", "operator"),
            (airlines, "codeshare_airline_fid", "codeshare_airline"),
            (aircraft_types, "aircraft_type_fid", "aircraft_type"),
            (classes, "class_fid", "class"),
            (trips, "trip_fid", "trip"),
        ]
        for _, v in self.items():
            for j in joins:
                if v.get(j[1]) is None:
                    v[j[2]] = {}
                else:
                    v[j[2]] = j[0][v[j[1]]]
                    v[j[2]]["fid"] = v[j[1]]
        return self

    def total_distance(self) -> int:
        """Returns the total distance of all flights in miles."""
        dists = [f.distance() if f.distance() else 0 for f in self.values()]
        return int(sum(dists))

    def total_duration(self) -> int:
        """Returns the total duration of all flights in seconds."""
        durs = [f.duration() if f.duration() else 0 for f in self.values()]
        return int(sum(durs))

    @classmethod
    def milestone_distances(cls) -> dict:
        """Returns a dict of Flights clearing milestone distances."""
        ft = cls.from_all().joined().sort("departure_utc")
        flights = list(ft.values())
        ms_distances = CONFIG["milestones"]["distances"]
        cum_distance = 0
        ms_index = 0
        output = {}
        for flight in flights:
            distance = flight.distance() if flight.distance() else 0
            cum_distance += distance
            flight["cum_distance"] = cum_distance
            for i in range(ms_index, len(ms_distances)):
                if cum_distance >= ms_distances[i]:
                    output[ms_distances[i]] = flight
                    ms_index = i + 1
        return output


class SeatClass(Record):
    """Represents a flight class record."""
    LOG_TYPE = "flight"
    LAYER = "classes"
    FIND_BY_CODES = []
    DTYPES = {"quality": "Int64"}

class SeatClassTable(RecordLayerTable):
    """Represents a dict of SeatClass instances."""
    RECORD_CLASS = SeatClass

class Route(Record):
    """Represents a route record."""

class RouteTable(RecordTable):
    """Represents a dict of Route instances."""
    RECORD_CLASS = Route

class TailNumber(Record):
    """Represents a tail number."""

class TailNumberTable(RecordTable):
    """Represents a dict of tail numbers."""
    RECORD_CLASS = TailNumber
    FID_LABEL = "tail_number"
    PRINT_COLS = {
        "aircraft_type": "aircraft_type",
        "count": "count",
        "rank": "rank",
    }

def estimate_trip_section(trip_fid: int, departure_dt: datetime) -> int | None:
    """Suggests a trip section number based on departure time."""
    flights = FlightTable.from_all().filter_by_trip(trip_fid).values()
    if len(flights) == 0:
        # No flights in trip.
        return 1
    unusable_flights = [
        f for f in flights
        if f.get("trip_section") is None or f.get("departure_utc") is None
    ]
    if len(unusable_flights) > 0:
        return None
    flights = sorted(flights, key=lambda f: f.get("departure_utc"))
    latest_flight = flights[-1]
    if departure_dt <= latest_flight["departure_utc"]:
        # New flight occurs before latest flight.
        return None
    if departure_dt < latest_flight["departure_utc"] + timedelta(days=1):
        # New flight is within 24 hours of latest flight.
        return int(latest_flight["trip_section"])
    # New flight is more than 24 hours after latest flight.
    return int(latest_flight["trip_section"]) + 1

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
