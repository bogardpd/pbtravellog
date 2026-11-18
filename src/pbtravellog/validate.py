"""User functions for validating travel log data."""

# Standard imports
from datetime import timedelta
from importlib.resources import files
import tomllib

# Project imports
from pbtravellog import flight_log

with open(files("pbtravellog.config").joinpath("config.toml"), "rb") as f:
    CONFIG = tomllib.load(f)

_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"
_OK = f"{_GREEN}[OK]{_RESET}"
_WARN = f"{_YELLOW}[WARN]{_RESET}"

class Validation():
    """Generic validation."""
    DESCRIPTION = ""

    def __init__(self, flights=None):
        self.warnings = []
        self.flights = flights

    def run(self) -> None:
        """Runs validation."""
        return None

    def report(self) -> None:
        """Prints validation results to the console."""
        warn_len = len(self.warnings)
        if warn_len == 0:
            print(f"{_OK} Validated \"{self.DESCRIPTION}\".")
        else:
            print(
                f"{_WARN} {warn_len} warning(s) found in "
                f"\"{self.DESCRIPTION}\":")
            for w in self.warnings:
                print(f"\t{_WARN} {w}")

class ValidateFlightDistances(Validation):
    """Validates flight distances are reasonable."""
    DESCRIPTION = "flight distances are reasonable"

    def run(self) -> None:
        max_dist_mi = CONFIG["validation"]["max_flight_distance_mi"]
        max_speed_mph = CONFIG["validation"]["max_flight_speed_mph"]
        for fid, flight in self.flights.items():
            dist_mi = flight["distance_mi"]
            if dist_mi is None:
                continue
            if dist_mi == 0:
                self.warnings.append(
                    f"Flight {fid} has a distance of 0 miles."
                )
            if dist_mi > max_dist_mi:
                self.warnings.append(
                    f"Flight {fid} has a distance of {dist_mi} miles, which "
                    f"exceeds the maximum of {max_dist_mi} miles."
                )
            dep = flight["departure_utc"]
            arr = flight["arrival_utc"]
            if arr is not None and dep is not None:
                dur_hours = (arr - dep).seconds // 3600
                if dur_hours != 0:
                    speed_mph = dist_mi // dur_hours
                    if speed_mph > max_speed_mph:
                        self.warnings.append(
                            f"Flight {fid} has a speed of {speed_mph} mph, "
                            f"which exceeds the maximum of {max_speed_mph} "
                            "mph."
                        )
        self.report()

class ValidateFlightOverlaps(Validation):
    """Validates that flights don't overlap each other."""
    DESCRIPTION = "flights don't overlap"

    def run(self) -> None:
        flights = self.flights.sort("departure_utc")
        fids = list(flights.keys())
        for fid0, fid1 in zip(fids[:-1], fids[1:]):
            arr0 = flights[fid0]["arrival_utc"]
            dep1 = flights[fid1]["departure_utc"]
            if arr0 is not None and dep1 is not None and dep1 < arr0:
                self.warnings.append(
                    f"Flights {fid0} and {fid1} overlap."
                )
        self.report()

class ValidateFlightTimes(Validation):
    """Validates flights have departure_utc and arrival_utc set."""
    DESCRIPTION = "all flights have departure_utc and arrival_utc"

    def run(self) -> None:
        for fid, flight in self.flights.items():
            dep = flight["departure_utc"]
            arr = flight["arrival_utc"]
            if dep is None:
                self.warnings.append(f"Flight {fid} has no departure_utc.")
            if arr is None:
                self.warnings.append(f"Flight {fid} has no arrival_utc.")
            if dep is not None and arr is not None and dep >= arr:
                self.warnings.append(
                    f"Flight {fid} arrival_utc is not after departure_utc."
                )
        self.report()

class ValidateLayoverLength(Validation):
    """Validates layovers aren't too long."""
    DESCRIPTION = "flight layovers are reasonable"
    MAX_LAYOVER_HOURS = CONFIG["validation"]["max_layover_hours"]

    def run(self) -> None:
        flights = self.flights.sort("departure_utc")
        fids = list(flights.keys())
        for fid0, fid1 in zip(fids[:-1], fids[1:]):
            arr0 = flights[fid0]["arrival_utc"]
            dep1 = flights[fid1]["departure_utc"]
            if arr0 is None or dep1 is None:
                continue
            trip_sec0 = (
                flights[fid0]["trip_fid"],
                flights[fid0]["trip_section"],
            )
            trip_sec1 = (
                flights[fid1]["trip_fid"],
                flights[fid1]["trip_section"],
            )
            if None in trip_sec0 or None in trip_sec1:
                continue
            if trip_sec0 == trip_sec1:
                if (dep1 - arr0) > timedelta(hours=self.MAX_LAYOVER_HOURS):
                    self.warnings.append(
                        f"Layover {fid0} → {fid1} greater than "
                        f"{self.MAX_LAYOVER_HOURS} hours ({dep1 - arr0})"
                    )
        self.report()

class ValidateTripDates(Validation):
    """Validates local times fall within trip dates."""
    DESCRIPTION = "travel falls within trip dates"

    def run(self) -> None:
        for fid, flight in self.flights.items():
            if flight["trip_fid"] is None:
                continue
            dep_local_time = flight.local_time("departure")
            arr_local_time = flight.local_time("arrival")
            if dep_local_time is None or arr_local_time is None:
                continue
            dep_local_date = dep_local_time.date()
            arr_local_date = arr_local_time.date()
            trip_start = (flight.get("trip") or {}).get("start_date")
            trip_end = (flight.get("trip") or {}).get("end_date")
            if trip_start is None or trip_end is None:
                continue
            if not trip_start <= dep_local_date <= trip_end:
                self.warnings.append(
                    f"Flight {fid} has a local departure of {dep_local_date}, "
                    "which is not within its trip dates of "
                    f"{trip_start} to {trip_end}."
                )
            if not trip_start <= arr_local_date <= trip_end:
                self.warnings.append(
                    f"Flight {fid} has a local arrival of {arr_local_date}, "
                    "which is not within its trip dates of "
                    f"{trip_start} to {trip_end}."
                )
        self.report()


def validate() -> bool:
    """Validates travel log data."""
    flights = flight_log.FlightTable.from_all().joined()
    validations = [
        ValidateTripDates(flights=flights),
        ValidateFlightTimes(flights=flights),
        ValidateFlightOverlaps(flights=flights),
        ValidateLayoverLength(flights=flights),
        ValidateFlightDistances(flights=flights),
    ]
    warning_count = 0
    for v in validations:
        v.run()
        warning_count += len(v.warnings)
    if warning_count > 0:
        print(f"{warning_count} total warning(s) found.")
    return warning_count == 0
