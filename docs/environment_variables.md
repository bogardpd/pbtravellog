# Environment Variables

This package stores some configuration in environment variables which must be set in order for certain capabilities to work.

## Travel Log Paths

This package interacts with a GeoPackage flight log database as described in the [flight log schema](schema/flight_log.md). The path to this file must be set as an environment variable:

```PBTRAVELLOG_FLIGHT_GEOPACKAGE_PATH=/path/to/flight_log.gpkg```

## Boarding Pass Paths

This package can import flights from PKPass boarding passes. The folder these passes will be imported from must be set as an environment variable:

```PBTRAVELLOG_FLIGHT_IMPORT_PATH=/path/to/import/folder```

When the flight log is done parsing a PKPass, it stores it in a folder which must be set as an environment variable:

```PBTRAVELLOG_PKPASS_ARCHIVE_PATH=/path/to/archive/folder```

## API Keys

This package interacts with [AeroAPI](https://www.flightaware.com/commercial/aeroapi/) to get flight data. You will need to get an AeroAPI API key and set it as an environment variable:

```AEROAPI_API_KEY=yourkey```

> [!IMPORTANT]
> When these scripts call AeroAPI with your API key, you will incur AeroAPI per-query fees as appropriate for your AeroAPI account.