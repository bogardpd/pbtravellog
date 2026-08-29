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

PBTravelLog can generate a local static HTML website to display travel log data. There are two primary commands, `build` and `run`. `build` compiles travel data into HTML format, and `run` shows this HTML in a browser.

> [!IMPORTANT]
> If travel log data is changed after `build` is used, the `run` command won't show that updated data. Be sure to run `build` again after travel logs are updated.

### `build`

Builds a collection of HTML pages from current travel log data.

You should use the `build` command before using `run`, unless travel data hasn't changed since the last time you used `build`.

#### Example

```bash
pbtravellog build
```

### `run`

Launches a server and web browser to show the HTML travel log.

The HTML pages will show travel data current as of the last time `build` was used. If the travel data changes, use `build` again before using `run`.

#### Options

- `--port NNNN`: The port to run the webserver on. Defaults to 8000 if not set.

#### Examples

```bash
pbtravellog run
```

```bash
pbtravellog run --port 12345
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
