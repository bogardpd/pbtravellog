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
    DEFAULT_BOUNDS = [[-180.0, -70.0], [180.0, 80.0]] # WS, EN

    def __init__(self, geojson: dict):
        self.geojson: dict = geojson
        self.bounds: list[list] = self.calc_bounds()

    def calc_bounds(self) -> list:
        """Calculates bounds for the map."""
        features = [
            f for f in self.geojson["features"]
            if f.get("geometry") is not None
        ]
        routes = [
            f for f in features
            if f["geometry"]["type"] == "MultiLineString"
        ]
        if len(routes) > 0:
            return self._route_bounds(routes)
        airports = [
            f for f in features
            if f["geometry"]["type"] == "Point"
        ]
        if len(airports) > 0:
            return self._airport_bounds(airports)
        return GeoJSONMap.DEFAULT_BOUNDS

    def _airport_bounds(self, airports) -> list[list]:
        """Returns bounds for a collection of airport features."""
        if len(airports) == 1:
            coords = list(airports[0]["geometry"]["coordinates"])
            return [coords, coords]
        lons = [a["geometry"]["coordinates"][0] for a in airports]
        lats = [a["geometry"]["coordinates"][1] for a in airports]
        lons_sorted = sorted(lons)
        lons_extended = [*lons_sorted, (lons_sorted[0] + 360.0)]
        lon_widths = [
            b - a for a, b in zip(lons_extended[:-1], lons_extended[1:])
        ]
        biggest_gap_start_index = lon_widths.index(max(lon_widths))
        bounds_e = lons_sorted[biggest_gap_start_index]
        bounds_w = lons_sorted[(biggest_gap_start_index + 1) % len(lons_sorted)]
        if bounds_w > bounds_e:
            bounds_e += 360
        return [
            [bounds_w, min(lats)],
            [bounds_e, max(lats)]
        ]

    def _route_bounds(self, routes) -> list[list]:
        """Returns bounds for a collection of route features."""
        min_lats = []
        max_lats = []
        lon_ranges = []
        airport_at_180 = False
        for route in routes:
            multiline = route["geometry"]["coordinates"]
            for line in multiline:
                if len(line) > 0:
                    lats = [p[1] for p in line]
                    min_lats.append(min(lats))
                    max_lats.append(max(lats))
                    lon_ranges.append(sorted([line[0][0], line[-1][0]]))
            if len(multiline) > 0:
                ends = (multiline[0][0][0], multiline[-1][-1][0])
                if abs(ends[0]) == 180.0 or abs(ends[1]) == 180.0:
                    airport_at_180 = True
        changes = [(-180,0), (180, 0)]
        for w, e in lon_ranges:
            # +1 at start of line (west), -1 at end of line (east).
            changes.extend([(w, 1), (e, -1)])
        changes.sort()
        # Build longitude bins of route counts.
        prev = -180
        count = 0
        bins = []
        for lon, change in changes:
            if lon > prev:
                bins.append((prev, lon, count))
            count += change
            prev = lon
        if not airport_at_180:
            # Merge first and last segment.
            bins.append((bins[-1][0], bins[0][1] + 360, bins[-1][2]))
            bins.pop(0)
        # Find all segments with the lowest route count.
        min_count = min([c for _, _, c in bins])
        candidates = [(w, e, e - w) for w, e, c in bins if c == min_count]
        gap_w, gap_e, gap_angle = max(candidates, key=lambda x: x[2])
        bounds_s, bounds_n = (min(min_lats), max(max_lats))
        if min_count == 0:
            # No routes cross this gap.
            bounds_w, bounds_e = (gap_e, gap_w)
            if bounds_w > bounds_e:
                bounds_e += 360
            return [[bounds_w, bounds_s], [bounds_e, bounds_n]]
        # Map goes around the world, so set east and west to the center
        # of biggest lowest gap region.
        split_lon = normalize_angle(gap_w + (gap_angle / 2))
        return [[split_lon, bounds_s], [split_lon + 360, bounds_n]]


def gc_distance(p1: Point, p2: Point) -> int:
    """Returns the great circle distance between points in miles."""
    if p1 == p2:
        return 0
    geod = Geod(ellps=ELLPS)
    _, _, dist_m = geod.inv(p1.x, p1.y, p2.x, p2.y)
    return int(round(dist_m / METERS_PER_MILE))

def geo_interface(geom) -> dict | None:
    """Returns a GeoJSON geometry."""
    if geom is None:
        return None
    return geom.__geo_interface__

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

def normalize_angle(angle: float):
    """Returns an angle in the -180 to 180 range."""
    return (angle + 180) % 360 - 180
