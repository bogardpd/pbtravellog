# Changelog

## [Unreleased]

### Changed

- `run` now uses a [Flask](https://flask.palletsprojects.com/en/stable/) backend instead of a static site.
- The static site now uses the command `run-static`.

## [0.3.0]

### Added

- Merged [PBFlightLog](https://github.com/bogardpd/pbflightlog) functionality into PBTravelLog.
- Added `build` and `run` command to build and launch static HTML.

## [0.2.0]

### Added

- Added GeoPackage output to `extract-photo-metadata`.

## [0.1.0]

### Added

- Initial release of PBTravelLog.
- `extract-photo-metadata` command for getting metadata from a directory of photos.
- Initial documentation.