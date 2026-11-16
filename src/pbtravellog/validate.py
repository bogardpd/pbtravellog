"""User functions for validating travel log data."""

# Standard imports
from datetime import timedelta

# Project imports
from pbtravellog import flight_log

GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
OK = f"{GREEN}[OK]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"

class Validation():
    """Generic validation."""
    DESCRIPTION = ""

    def __init__(self):
        self.flights = flight_log.FlightTable.from_all().joined()
        self.warnings = []

    def run(self) -> None:
        """Runs validation."""
        return None

    def report(self) -> None:
        """Prints validation results to the console."""
        warn_len = len(self.warnings)
        if warn_len == 0:
            print(f"{OK} Validated \"{self.DESCRIPTION}\".")
        else:
            print(
                f"{WARN} {warn_len} warning(s) found in "
                f"\"{self.DESCRIPTION}\":")
            for w in self.warnings:
                print(f"\t{WARN} {w}")

class ValidateFlightOverlaps(Validation):
    """Validates that flights don't overlap each other."""
    DESCRIPTION = "flights don't overlap"
    MAX_LAYOVER_HOURS = 1

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
    MAX_LAYOVER_HOURS = 12

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


def validate():
    """Validates travel log data."""
    validations = [
        ValidateFlightTimes(),
        ValidateFlightOverlaps(),
        ValidateLayoverLength(),
    ]
    for v in validations:
        v.run()
