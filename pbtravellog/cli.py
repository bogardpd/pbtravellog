"""Travel log command line utilities."""

# Standard imports
import argparse
from pathlib import Path

# Project imports
import pbtravellog.extract_photo_metadata as epm
import pbtravellog.html as html

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
    epm_parser.add_argument("--source",
        help="Directory of source photos",
        type=Path,
        required=True,
    )
    epm_parser.add_argument("--output",
        help="Directory for output files",
        type=Path,
        required=True,
    )
    run_parser = subparsers.add_parser(
        "run",
        help="Launch HTML travel log"
    )
    args = parser.parse_args()
    if args.command == "extract-photo-metadata":
        epm.extract_photo_metadata(args.source, args.output)
    if args.command == "run":
        html.run()
