"""Extracts metadata from a folder of photos."""

# Standard imports
from datetime import datetime
from pathlib import Path

# Third-party imports
import pandas as pd
from PIL import Image
import simplekml

def extract_photo_metadata(source: Path, output: Path):
    if not source.is_dir():
        raise ValueError("Source must be a directory")
    if not output.is_dir():
        raise ValueError("Output must be a directory")
    kmz_path = output / "photo_data.kmz"
    csv_path = output / "photo_data.csv"
    photos = list(source.glob("*.jpg"))
    if not photos:
        raise ValueError(f"No .jpg files found in {source}")
    records = [
        {'name': photo.name} | _get_exif_jpeg(photo)
        for photo in photos
    ]
    df = pd.DataFrame.from_records(records)
    df.to_csv(csv_path, index=None)
    print(f"Wrote CSV to {csv_path}")

    kml = simplekml.Kml()
    for idx, row in df.iterrows():
        if row.location:
            print(row)
            lat, lon = row.location
            pnt = kml.newpoint(
                name=str(row['name']),
                coords=[(lon, lat)]
            )
    kml.savekmz(kmz_path)
    print(f"Wrote KMZ to {kmz_path}")    
    
def _get_exif_jpeg(photo_path: Path):
    with Image.open(photo_path) as img:
        exif_data = img.getexif()
        output = {
            'taken': _get_exif_dt(exif_data),
            'make': exif_data.get(271),
            'model': exif_data.get(272),
            'location': _get_exif_gps(exif_data),
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