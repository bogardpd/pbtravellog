"""Manages geometry methods."""

# Standard imports
from math import ceil

# Third-party imports
import pandas as pd
from pyproj import Geod
from shapely.geometry import Point, LineString, MultiLineString

CRS = "EPSG:4326" # WGS-84
ELLPS = "WGS84"
METERS_PER_MILE = 1609.344
METERS_PER_HUNDRED_FEET = 30.48
METERS_BETWEEN_GC_POINTS = 100000
GEOJSON_HEADERS = {
    "Content-Type": "application/geo+json",
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

class GeoJSONMap():
    """Manages GeoJSON map data."""
    def __init__(self, geojson: dict):
        self.geojson: dict = geojson
        self.bounds = self.bounds()

    def bounds(self) -> list:
        """Calculates bounds for the map."""
        default_bounds = [[-180.0, -70.0], [180.0, 80.0]] # WS, EN
        features = [
            f for f in self.geojson["features"]
            if f.get("geometry") is not None
        ]
        airports = [
            f for f in features
            if f["geometry"]["type"] == "Point"
        ]
        if len(airports) == 0:
            return default_bounds
        elif len(airports) == 1:
            coords = list(airports[0]["geometry"]["coordinates"])
            return [coords, coords]
        airport_lons = [a["geometry"]["coordinates"][0] for a in airports]
        airport_lats = [a["geometry"]["coordinates"][1] for a in airports]
        lons_sorted = sorted(airport_lons)
        lons_extended = [*lons_sorted, (lons_sorted[0] + 360.0)]
        lon_widths = [
            b - a for a, b in zip(lons_extended[:-1], lons_extended[1:])
        ]
        biggest_gap_start_index = lon_widths.index(max(lon_widths))
        bound_e = lons_sorted[biggest_gap_start_index]
        bound_w = lons_sorted[(biggest_gap_start_index + 1) % len(lons_sorted)]
        if bound_e < bound_w:
            bound_e += 360.0
        bound_n = max(airport_lats)
        bound_s = min(airport_lats)
        return [[bound_w, bound_s], [bound_e, bound_n]]
        # TODO: Implement route checks
        routes = [
            f for f in features
            if f["geometry"]["type"] == "MultiLineString"
        ]

        return default_bounds


def gc_distance(p1: Point, p2: Point) -> int:
    """Returns the great circle distance between points in miles."""
    if p1 == p2:
        return 0
    geod = Geod(ellps=ELLPS)
    _, _, dist_m = geod.inv(p1.x, p1.y, p2.x, p2.y)
    return int(round(dist_m / METERS_PER_MILE))

def great_circle_route(
        point1: Point,
        point2: Point,
) -> tuple[int, MultiLineString | None]:
    """Returns great circle miles and geometry between points."""
    if point1 == point2:
        # Returned to same airport. Return zero great circle distance
        # and no geometry.
        return (0, None)
    geod = Geod(ellps=ELLPS)
    _, _, dist_m = geod.inv(point1.x, point1.y, point2.x, point2.y)
    dist_mi = gc_distance(point1, point2)

    # Create a great circle LineString.
    num_points = ceil(dist_m / METERS_BETWEEN_GC_POINTS) + 1
    midpoints = geod.npts(
        point1.x, point1.y,
        point2.x, point2.y,
        num_points - 2,
    )
    geom = split_at_antimeridian(
        LineString([point1, *midpoints, point2])
    )
    return (dist_mi, geom)

def great_circle_route_pd(point1, point2) -> pd.Series:
    """Creates a great circle line between points.

    Returns a Pandas series with distance in integer miles and a
    MultiLineString geometry.
    """
    dist_mi, geom = great_circle_route(point1, point2)
    return pd.Series([dist_mi, geom])

def split_at_antimeridian(track_ls: LineString) -> MultiLineString:
    """Split a LineString at the antimeridian."""
    # Find all points where the track crosses the antimeridian.
    crossings = [
        i + 1 for i, (p1, p2)
        in enumerate(zip(track_ls.coords[:-1], track_ls.coords[1:]))
        if abs(p1[0] - p2[0]) > 180
    ]
    if len(crossings) == 0:
        return MultiLineString([track_ls])

    # Split the track at the indices.
    tracks = []
    starts = [0, *crossings]
    ends = [*crossings, len(track_ls.coords)]
    tracks = [
        track_ls.coords[start:end] for start, end in zip(starts, ends)
    ]
    for i, track in enumerate(tracks):
        if i > 0:
            p1 = track[0]
            p2 = tracks[i-1][-1]
            p_cross = _crossing_point(p1, p2)
            if p_cross is not None:
                track.insert(0, p_cross)
        if i < len(crossings):
            p1 = track[-1]
            p2 = tracks[i+1][0]
            p_cross = _crossing_point(p1, p2)
            if p_cross is not None:
                track.append(p_cross)

    # Filter out tracks with only one point.
    tracks = [track for track in tracks if len(track) > 1]
    return MultiLineString(tracks)

def _crossing_point(p1, p2):
    """Return the point where a track crosses the antemeridian.
    Returns None if p1 is already on the antemeridian.

    p1 : tuple(float)
        The point on the current track
    p2 : tuple(float)
        The point on the adjacent track.
    """
    p2 = list(p2)
    if -180 < p1[0] < 0:
        lon = -180
        p2[0] = p2[0] - 360
    elif 0 < p1[0] < 180:
        lon = 180
        p2[0] = p2[0] + 360
    else:
        return None
    x_frac = (lon - p1[0]) / (p2[0] - p1[0])
    return tuple([c1 + (x_frac * (c2 - c1)) for c1, c2 in zip(p1, p2)])
