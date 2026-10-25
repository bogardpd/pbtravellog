# PBTravelLog

PBTravelLog is a Python command-line interface (CLI) tool for managing personal travel logs stored in GeoPackage files.

This package assumes that the majority of travel log keeping will be done via applications like [QGIS](https://www.qgis.org/). This package is intended as a supplement to such a travel log, providing utilities and automation that aren't easy to accomplish in QGIS.

## Features

- **Travel Log Browser:** runs a local website to interactively show travel log data and maps.
- **Command Line Travel Data Viewer:** lets users view aggregated travel log data from the command line.
- **Flight Importer:** can automatically add flights to the flight log from digital boarding passes, paper boarding pass barcode scans, and more.

## Setup

### Install PBTravelLog

Navigate to the module's folder and install it with [pipx](https://pipx.pypa.io/stable/):

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

### Set Environment Variables

Environment variables must be set as described in the [Environment Variables documentation](docs/environment_variables.md).

### Initialize GeoPackage Files

The travel log is stored in a collection of GeoPackage files, as described in the [schema documentation](docs/schema/schema.md). To create new empty GeoPackage files in the locations specified by the environment variables, use the `init` command:

```bash
pbtravellog init
```

If a GeoPackage file already exists, the `init` command will skip it.

If you'd prefer to manually download the empty GeoPackage files, they are available in [/src/pbtravellog/data/gpkg/](/src/pbtravellog/data/gpkg/).


## Command Reference

### Basic usage

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

### `browse`

PBTravelLog can locally run a website to show travel log data. By default, this website will be run at http://localhost:5000. To launch a server and a browser, use the `browse` command:

```bash
pbtravellog browse
```

If you need to run the server on a particular port, use the `--port NNNN` flag:

```bash
pbtravellog browse --port 12345
```

### `extract photo-metadata`

Takes a folder of JPEG images, and returns an HTML file with a table of photo metadata, and a GeoPackage and KMZ file of photo locations (for photos with location data).

#### Options

- `--source` (required): The path for a directory of photos to extract metadata from.
- `--output` (required): The path for a directory to save output data to. Three files will be saved in this directory: `photo_data.html`, `timeline.gpkg`, and `photo_data.kmz`.

#### Example

```bash
pbtravellog extract photo-metadata --source ~/source_photos_dir --output ~/output_dir
```

### `import flight`

Flights have a lot of fields to fill out, and a lot of this data is already available in FlightAware's [AeroAPI](https://www.flightaware.com/commercial/aeroapi/). To create flights with AeroAPI data, use the import flight command:

```bash
pbtravellog import flight [options]
```

> [!NOTE]
> This command uses AeroAPI, so your AeroAPI API key must be set as an [environment variable](/docs/environment_variables.md). Using this command will incur API usage fees against your API key.

There are four ways to import a flight, and exactly one of these options must be used (`import flight` won't work without using an option).

#### Options

- `--bcbp <bcbp_text>`: Parse a string coded in the IATA Bar-Coded Boarding Pass (BCBP) format, and import the flight(s) it represents into the flight log.

    You can get this string by scanning the 2-D barcode on a boarding pass with a barcode reader app.

    **Example**
    ```bash
    pbtravellog import flight --bcbp "M1DOE/JOHN            EABC123 BOSJFKB6 0717 345P014C0010 147>3180 M6344BB6              29279          0 B6 B6 1234567890          ^108abcdefgh"
    ```

    Since BCBP data contains spaces, be sure to place the BCBP string in quotes. Do not trim trailing spaces from the string, as spaces have meaning in the BCBP format.

- `--fa-flight-id <fa_flight_id>`: Look up a flight on [AeroAPI](https://www.flightaware.com/commercial/aeroapi/) by `fa_flight_id` and import it into the flight log.

    **Example**
    ```bash
    pbtravellog import flight --fa-flight-id UAL1234-1234567890-airline-0123
    ```

- `--number <airline_code> <flight_number>`: Look up an airline and flight number on [AeroAPI](https://www.flightaware.com/commercial/aeroapi/) and import it into the flight log.

  To reduce ambiguity, ICAO airline codes (three letter codes, like `AAL`) are preferred. However, this will attempt to look up IATA airline codes (two character codes, like `AA`).

    **Example**
    ```bash
    pbtravellog import flight --number AAL 1234
    ```

- `--pkpasses`: Fetch all PKPass (Apple Wallet) files from the [import folder](#environment-variables) and import them into the flight log.

    **Example**
    ```bash
    pbtravellog import flight --pkpasses
    ```

### `index airports`

Generates an index of airports visited, sorted by number of visits. ([Layovers count as a single visit.](https://paulbogard.net/flight-historian/counting-visits-to-airports-the-significance-of-trip-sections/))

#### Options

- `--output <file>` (`-o <file>`): Save the index table in CSV format to the provided filename.

- `--year <year>` (`-y <year>`): Filter the flights that airport visits are calculated from to those whose UTC departure is in the provided year. If this option is not used, airport visits will be calculated on all flights.

#### Examples

Show 2015 airport visits:

```bash
pbtravellog index airports --year 2015
```

```
  fid  name                     iata_code    icao_code    faa_lid      visits    rank
-----  -----------------------  -----------  -----------  ---------  --------  ------
    5  Dayton                   DAY          KDAY         DAY              42       1
   10  Chicago (O’Hare)         ORD          KORD         ORD              16       2
   15  Orlando (International)  MCO          KMCO         MCO              12       3
   20  Dallas/Fort Worth        DFW          KDFW         DFW              10       4
   25  Tulsa                    TUL          KTUL         TUL              10       4
   30  Baltimore                BWI          KBWI         BWI               5       6
   35  Charlotte                CLT          KCLT         CLT               5       6
   40  Columbus, OH             CMH          KCMH         CMH               5       6
   45  Seattle/Tacoma           SEA          KSEA         SEA               4       9
   50  St. Louis                STL          KSTL         STL               4       9
10 airport(s) visited
```
Save 2015 airport visits to airports.csv:

```bash
pbtravellog index airports --output airports.csv --year 2015
```

### `index tails`

Generates an index of tail numbers flown, sorted by number of flights.

#### Options

- `--output <file>` (`-o <file>`): Save the index table in CSV format to the provided filename.

#### Examples

```bash
pbtravellog index tails
```

```
tail_number    aircraft_type                count    rank
-------------  -------------------------  -------  ------
N123AA         McDonnell Douglas MD-82          2       1
N456BB         Embraer ERJ-145                  1       2
N789CC         Embraer ERJ-145                  1       2
3 tails(s) flown
```

Save tail numbers to tails.csv:

```bash
pbtravellog index airports --output tails.csv
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

### `show airport`

Shows a flight table for a specific airport.

#### Examples

```bash
pbtravellog show airports LGA
```

```
  fid  departure                  name           orig    dest
-----  -------------------------  -------------  ------  ------
   10  2009-01-02 18:04:00-05:00  AirTran 327    LGA     MKE
   20  2014-04-09 07:50:00-05:00  Southwest 651  MDW     LGA
   30  2016-12-02 15:50:00-05:00  Delta 746      MCO     LGA
   31  2016-12-02 20:29:00-05:00  Delta 3977     LGA     DAY
   40  2017-06-08 15:25:00-04:00  Delta 2646     TPA     LGA
   41  2017-06-08 20:30:00-04:00  Delta 3496     LGA     DAY
   50  2019-10-18 12:42:00-04:00  American 1556  MIA     LGA
   51  2019-10-18 18:09:00-04:00  American 5432  LGA     DAY
   60  2022-11-14 11:53:00-05:00  American 2119  DCA     LGA
   70  2022-11-17 19:24:00-05:00  American 2950  LGA     DCA
   80  2023-03-06 12:51:00-05:00  American 4383  DCA     LGA
   90  2023-03-09 15:54:00-05:00  American 473   LGA     DCA
  100  2024-01-09 07:00:00-05:00  Delta 5186     DAY     LGA
  101  2024-01-09 11:10:00-05:00  Delta 5843     LGA     RDU
14 matching flight(s)
 ```

### `show tail`

Shows a flight table for a particular tail number.

#### Examples

```bash
pbtravellog show tail N123AA
```

```
  fid  departure                  name           orig    dest
-----  -------------------------  -------------  ------  ------
  100  2012-05-16 12:00:00-05:00  American 1000  DFW     ORD
  200  2012-07-23 12:00:00-05:00  American 1100  ORD     LAX
2 matching flight(s)
```

## Testing

PBTravelLog includes [pytest](https://docs.pytest.org/en/stable/index.html) tests. Before running any tests, install pytest in PBTravelLog's venv:

`python -m pip install -U pytest`

To run tests:

`python -m pytest`
