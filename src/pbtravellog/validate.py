"""User functions for validating travel log data."""

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


def validate():
    """Validates travel log data."""
    validations = [
        ValidateFlightTimes(),
        ValidateFlightOverlaps(),
    ]
    for v in validations:
        v.run()
