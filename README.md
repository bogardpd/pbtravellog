# pbtravellog

PBFlightLog is a Python command-line interface (CLI) tool for managing personal travel logs stored in GeoPackage files.

## Setup

### Installation

Navigate to the module's folder and install it with pipx:

```bash
cd path/to/module
pipx install .
```

If you want to allow the scripts to be editable after install, perform a pipx editable installation instead:

```bash
cd path/to/module
pipx install --editable .
```

After installation, the `pbtravellog` command is available on the command line.

### GeoPackage Files

The travel log is stored in a collection of GeoPackage files. Currently, the travel log only interacts with flight data, as described in the following schema:

- [Flight Log schema](docs/schema/flight_log.md)

### Environment Variables

Environment variables must be set as described in the [Environment Variables documentation](docs/environment_variables.md).

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

## Travel Log Data Commands

### `add flight`

Create a new flight (or new flights) in the flight log.

> [!IMPORTANT]
> Flight data is pulled from [AeroAPI](https://www.flightaware.com/commercial/aeroapi/), so an API key must be set in [environment variables](docs/environment_variables.md).

#### Options (mutually exclusive)

- `--bcbp <bcbp_text>`: Parse a string coded in the IATA Bar-Coded Boarding Pass (BCBP) format, and add the flight(s) it represents to the log.

    You can get this string by scanning the 2-D barcode on a boarding pass with a barcode reader app.

    **Example**
    ```bash
    pbtravellog add flight --bcbp "M1DOE/JOHN            EABC123 BOSJFKB6 0717 345P014C0010 147>3180 M6344BB6              29279          0 B6 B6 1234567890          ^108abcdefgh"
    ```

    Since BCBP data contains spaces, be sure to place the BCBP string in quotes. Do not trim trailing spaces from the string, as spaces have meaning in the BCBP format.

- `--fa-flight-id <fa_flight_id>`: Look up a flight on [AeroAPI](https://www.flightaware.com/commercial/aeroapi/) by `fa_flight_id` and add it to the flight log.

    **Example**
    ```bash
    pbtravellog add flight --fa-flight-id UAL1234-1234567890-airline-0123
    ```

- `--number <airline_code> <flight_number>`: Look up an airline and flight number on [AeroAPI](https://www.flightaware.com/commercial/aeroapi/) and add it to the flight log.

  To reduce ambiguity, ICAO airline codes (three letter codes, like `AAL`) are preferred. However, this will attempt to look up IATA airline codes (two character codes, like `AA`).

  **Example**
    ```bash
    pbtravellog add flight --number AAL 1234
    ```

- `--pkpasses`: Fetch all PKPass (Apple Wallet) files from the [import folder](#environment-variables) and add them to the flight log.

    **Example**
    ```bash
    pbtravellog add flight --pkpasses
    ```

### `index airports`

Generates an index of airports visited, sorted by number of visits. ([Layovers count as a single visit.](https://paulbogard.net/flight-historian/counting-visits-to-airports-the-significance-of-trip-sections/))

#### Options

- `--year <year>` (`-y <year>`): Filter the flights that airport visits are calculated from to those whose UTC departure is in the provided year. If this option is not used, airport visits will be calculated on all flights.

- `--output <file>` (`-o <file>`): Save the index table in CSV format to the provided filename.

#### Examples

Show 2015 airport visits:

```bash
pbtravellog index airports --year 2015
```

```
  fid    Rank  Name                          IATA    ICAO    FAA      Visits
                                             Code    Code    LID
-----  ------  ----------------------------  ------  ------  -----  --------
    5       1                  Dayton       DAY      KDAY     DAY         42
   10       2        Chicago (O’Hare)       ORD      KORD     ORD         16
   15       3 Orlando (International)       MCO      KMCO     MCO         12
   20       4       Dallas/Fort Worth       DFW      KDFW     DFW         10
   25       4                   Tulsa       TUL      KTUL     TUL         10
   30       6               Baltimore       BWI      KBWI     BWI          5
   35       6               Charlotte       CLT      KCLT     CLT          5
   40       6            Columbus, OH       CMH      KCMH     CMH          5
   45       9          Seattle/Tacoma       SEA      KSEA     SEA          4
   50       9               St. Louis       STL      KSTL     STL          4
10 airport(s) visited
```
Save 2015 airport visits to airports.csv:

```bash
pbtravellog index airports --year 2015 --output airports.csv
```

### `index tails`

Generates an index of tail numbers flown, sorted by number of flights.

#### Examples

```bash
pbtravellog index tails
```

```
Tail    Type                         Count
------  -------------------------  -------
N123AA  McDonnell Douglas MD-82          2
N456BB  Embraer ERJ-145                  1
N789CC  Embraer ERJ-145                  1
3 tails(s) flown
```

### `show airport`

Shows a flight table for a specific airport.

#### Examples

```bash
pbtravellog show airports LGA
```

```
  fid    #  Departure    Flight    Orig    Dest      Cumulative
                                                         Visits
-----  ---  -----------  --------  ------  ------  ------------
   10    1  2009-01-02   FL 327    LGA     MKE                1
   20    2  2014-04-09   WN 651    MDW     LGA                2
   30    3  2016-12-02   DL 746    MCO     LGA                3
   31    4  2016-12-02   DL 3977   LGA     DAY                3
   40    5  2017-06-08   DL 2646   TPA     LGA                4
   41    6  2017-06-08   DL 3496   LGA     DAY                4
   50    7  2019-10-18   AA 1556   MIA     LGA                5
   51    8  2019-10-18   AA 5432   LGA     DAY                5
   60    9  2022-11-14   AA 2119   DCA     LGA                6
   70   10  2022-11-17   AA 2950   LGA     DCA                7
   80   11  2023-03-06   AA 4383   DCA     LGA                8
   90   12  2023-03-09   AA 473    LGA     DCA                9
  100   13  2024-01-09   DL 5186   DAY     LGA               10
  101   14  2024-01-09   DL 5843   LGA     RDU               10
 ```

### `show tail`

Shows a flight table for a particular tail number.

#### Examples

```bash
pbtravellog show tail N123AA
```

```
  fid    #  Departure    Flight    Orig    Dest
-----  ---  -----------  --------  ------  ------
  100    1  2012-03-16   AA 1000   DFW     ORD
  200    2  2012-07-23   AA 1100   ORD     LAX
```

### `refresh routes`

Regenerates the routes table based on all origin and destination airport pairs present in the flights table. Generates great circle geometry for these routes.

> [!WARNING]
> This will overwrite the routes table, including removing routes that no longer have flights. Do not manually edit the routes table, as any edits will be lost when routes are refreshed.

#### Example
```bash
pbtravellog refresh routes
```
### `report milestones`

Shows flights that include cumulative distance milestones.

> [!NOTE]
> By default, milestones are set at 50 000, 100 000, 200 000, 500 000, 1 000 000, 2 000 000, 5 000 000, 10 000 000, 20 000 000, and 50 000 000 miles. Milestones can be configured in `config/config.toml`.

#### Example

```bash
pbtravellog report milestones
```

```
  fid    #  Departure    Flight    Orig    Dest      Milestone    Cumulative
                                                                       Miles
-----  ---  -----------  --------  ------  ------  -----------  ------------
   40    1  2009-04-03   AA 1042   DFW     DAY           50000         50642
   80    2  2010-03-04   AA 3597   DFW     CMH          100000        100089
  160    3  2012-12-03   UA 3485   CMH     IAD          200000        200125
  320    4  2018-03-02   AA 82     AKL     LAX          500000        502473
```

## Utility Commands

### `extract-photo-metadata`

Takes a folder of JPEG images, and returns an HTML file with a table of photo metadata, and a GeoPackage and KMZ file of photo locations (for photos with location data).

#### Options

- `--source` (required): The path for a directory of photos to extract metadata from.
- `--output` (required): The path for a directory to save output data to. Three files will be saved in this directory: `photo_data.html`, `timeline.gpkg`, and `photo_data.kmz`.

#### Example

```bash
pbtravellog extract-photo-metadata --source ~/source_photos_dir --output ~/output_dir
```
