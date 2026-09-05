"""Extracts metadata from a folder of photos."""

# Standard imports
from datetime import datetime
from pathlib import Path
import html

# Third-party imports
import pandas as pd
import geopandas as gpd
from PIL import Image
import simplekml

def extract_photo_metadata(source: Path, output: Path):
    """Gets metadata from JPG photos in a folder."""
    if not source.is_dir():
        raise ValueError("Source must be a directory")
    if not output.is_dir():
        raise ValueError("Output must be a directory")
    kmz_path = output / "photo_data.kmz"
    gpkg_path = output / "timeline.gpkg"
    html_path = output / "photo_data.html"
    photos = [
        f for f in source.iterdir()
        if f.suffix.lower() in ['.jpg', '.jpeg']
    ]
    if not photos:
        raise ValueError(f"No .jpg files found in {source}")
    records = [
        {"name": photo.name} | _get_exif_jpeg(photo)
        for photo in photos
    ]
    df = pd.DataFrame.from_records(records)
    df = df.sort_values("taken")

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["lon", "lat"]),
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs='EPSG:4326',
    )
    gdf.to_file(
        gpkg_path,
        layer="photos",
        driver="gpkg",
        mode="a",
    )

    kml = simplekml.Kml()
    for _, row in df.iterrows():
        if row.lat and row.lon:
            name = str(row["taken"])
            if pd.notna(row["desc"]):
                name += " " + str(row["desc"])
            kml.newpoint(
                name=name,
                coords=[(row.lon, row.lat)]
            )
    kml.savekmz(kmz_path)
    print(f"Wrote KMZ to {kmz_path}")

    df["time"] = df["taken"].dt.strftime('%H:%M')
    df["location"] = df.apply(_format_location, axis=1)
    print(df)
    df["event"] = df.apply(_format_event, axis=1)
    df_output = df[["time", "event"]]
    df_output.to_html(html_path, index=None, escape=False)
    print(f"Wrote HTML to {html_path}")

def _format_event(row):
    output = [
        row["desc"],
        row["name"],
        row["model"],
        row["location"],
    ]
    output = [
        html.escape(str(s)) for s in output
        if (pd.notna(s) and not str(s).isspace())
    ]
    return "📸 " + " &middot; ".join(output)

def _format_location(row):
    if row["lat"] is None or row["lon"] is None:
        return pd.NA
    return f"({str(row.lat)}, {str(row.lon)})"

def _get_exif_jpeg(photo_path: Path):
    with Image.open(photo_path) as img:
        exif_data = img.getexif()
        loc = _get_exif_gps(exif_data)
        if loc is not None:
            lat = loc[0]
            lon = loc[1]
        else:
            lat = None
            lon = None
        output = {
            "desc": exif_data.get(270),
            "taken": _get_exif_dt(exif_data),
            "make": exif_data.get(271),
            "model": exif_data.get(272),
            "lat": lat,
            "lon": lon,
        }
        return output

def _get_exif_gps(exif_data) -> tuple | None:
    """Gets latitude, longitude from EXIF data."""
    gps_data = exif_data.get_ifd(34853)
    if not gps_data:
        return None
    lat_dir = gps_data.get(1)
    lat_raw = gps_data.get(2)
    lon_dir = gps_data.get(3)
    lon_raw = gps_data.get(4)
    if not (lat_dir and lat_raw and lon_dir and lon_raw):
        return None
    lat = float(lat_raw[0] + (lat_raw[1] / 60) + (lat_raw[2] / 3600))
    if lat_dir != "N":
        lat = -lat
    lon = float(lon_raw[0] + (lon_raw[1] / 60) + (lon_raw[2] / 3600))
    if lon_dir != "E":
        lon = -lon
    return (round(lat, 6), round(lon, 6))

def _get_exif_dt(exif_data):
    exif_photo_settings = exif_data.get_ifd(34665)
    # Try DateTimeOriginal and fall back to DateTime
    time_str = exif_photo_settings.get(36867) or exif_data.get(306) # Fallback to DateTime
    if not time_str:
        return None
    photo_time = datetime.strptime(str(time_str), "%Y:%m:%d %H:%M:%S")
    return photo_time
