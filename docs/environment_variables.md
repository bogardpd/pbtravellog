# Environment Variables

This package stores some configuration in environment variables which must be set in order for certain capabilities to work.

## Travel Log Paths

This package interacts with a GeoPackage flight log database as described in the [flight log schema](schema/flight_log.md). The path to this file must be set as an environment variable:

```PBFLIGHTLOG_GEOPACKAGE_PATH=/path/to/flight_log.gpkg```

## Import Path

This package can import flights from PKPass boarding passes. The folder these passes will be imported from must be set as an environment variable:

```PBTRAVELLOG_FLIGHT_IMPORT_PATH=/path/to/import/folder```

## HTML Path

This package has the ability to generate static HTML files for travel log data and place them into a folder. The path to this folder must be set as an environment variable:

```PBTRAVELLOG_HTML_PATH=/path/to/html/folder```

## API Keys

This package interacts with [AeroAPI](https://www.flightaware.com/commercial/aeroapi/) to get flight data. You will need to get an AeroAPI API key and set it as an environment variable:

```AEROAPI_API_KEY=yourkey```

> [!IMPORTANT]
> When these scripts call AeroAPI with your API key, you will incur AeroAPI per-query fees as appropriate for your AeroAPI account.