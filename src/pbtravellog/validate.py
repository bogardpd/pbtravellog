"""User functions for validating travel log data."""

# Project imports
from pbtravellog import flight_log

class Validation():
    """Generic validation."""
    DESCRIPTION = ""

    def __init__(self):
        self.flights = flight_log.FlightTable.from_all().joined()
        self.warnings = []

    def run(self) -> bool:
        """Runs validation."""
        return True

    def report(self) -> None:
        """Prints validation results to the console."""
        warn_len = len(self.warnings)
        if warn_len == 0:
            print(f"✅ Validated \"{self.DESCRIPTION}\".")
        else:
            print(f"⚠️ {warn_len} warning(s) found in \"{self.DESCRIPTION}\":")
            for w in self.warnings:
                print(f"\t⚠️ {w}")

class ValidateFlightUTCTimes(Validation):
    """Validates flights have departure_utc and arrival_utc set."""

    DESCRIPTION = "all flights have departure_utc and arrival_utc"

    def run(self) -> bool:
        for fid, flight in self.flights.items():
            if flight["departure_utc"] is None:
                self.warnings.append(f"Flight {fid} has no departure_utc.")
            if flight["arrival_utc"] is None:
                self.warnings.append(f"Flight {fid} has no arrival_utc.")
        self.report()


def validate():
    """Validates travel log data."""
    validations = [
        ValidateFlightUTCTimes(),
    ]
    for v in validations:
        v.run()
