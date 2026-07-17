"""Travel log command line utilities."""

# Standard imports
import argparse
from pathlib import Path

# Project imports
import pbtravellog.extract_photo_metadata as epm

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tools for managing travel logs"
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    epm_parser = subparsers.add_parser(
        "extract-photo-metadata",
        help="Extract metadata from a folder of photos"
    )
    epm_parser.add_argument("source",
        help="Directory of source photos",
        type=Path,
    )
    epm_parser.add_argument("output",
        help="Directory for output files",
        type=Path,
    )
    args = parser.parse_args()
    if args.command == "extract-photo-metadata":
        epm.extract_photo_metadata(args.source, args.output)
