"""User functions for creating reports."""

# Standard imports
from importlib.resources import files
import tomllib

# Project imports
import pbtravellog.flight_log as fl

with open(files("pbtravellog.config").joinpath("config.toml"), "rb") as f:
    CONFIG = tomllib.load(f)

def report_milestones() -> None:
    """Reports flying milestones."""
    ft = fl.FlightTable.from_all().joined().sort("departure_utc")
    flights = list(ft.values())
    mile_distances = CONFIG["milestones"]["distances"]
    cum_distance = 0
    milestone_index = 0
    print("milestone,departure_utc,fid,cum_distance")
    for flight in flights:
        distance = flight.distance() if flight.distance() else 0
        cum_distance += distance
        flight["cum_distance"] = cum_distance
        for i in range(milestone_index, len(mile_distances)):
            if cum_distance >= mile_distances[i]:
                print(",".join([
                    str(mile_distances[i]),
                    str(flight["departure_utc"]),
                    str(flight["fid"]),
                    str(cum_distance)
                ]))
                milestone_index = i + 1

    print(f"Total distance: {ft.total_distance()} mi")
