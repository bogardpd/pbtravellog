# pbtravellog

Utilities for managing travel logs.

## Setup

### Installation

Navigate to the module's folder and install it with pip or pipx:

```bash
cd path/to/module
python -m pip install .
```

```bash
cd path/to/module
pipx install .
```

If you want to allow the scripts to be editable after install, perform a pip or pipx editable installation instead:

```bash
cd path/to/module
python -m pip install -e .
```

```bash
cd path/to/module
pipx install --editable .
```

After installation, the `pbtravellog` command is available on the command line.

## Basic usage

```bash
pbtravellog <command> [options]
```

To see available commands:

```bash
pbtravellog --help
```

To see help for a specific command:

```bash
pbtravellog <command> --help
```

## HTML Commands

PBTravelLog can generate a local static HTML website to display travel log data.

### `run`

Launches a server and web browser to show the HTML travel log.

#### Example

```bash
pbtravellog run
```

## Additional Commands

### `extract-photo-metadata`

Takes a folder of JPEG images, and returns an HTML file with a table of photo metadata, and a GeoPackage and KMZ file of photo locations (for photos with location data).

#### Options

- `--source` (required): The path for a directory of photos to extract metadata from.
- `--output` (required): The path for a directory to save output data to. Three files will be saved in this directory: `photo_data.html`, `timeline.gpkg`, and `photo_data.kmz`.

#### Example

```bash
pbtravellog extract-photo-metadata --source ~/source_photos_dir --output ~/output_dir
```
