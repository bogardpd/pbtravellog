"""Builds and runs a static HTML travel log."""

# Standard imports
import http.server
import os
import sys
import webbrowser
from functools import partial

# Third-party imports

PORT = 8000
HTML_PATH = os.getenv("PBTRAVELLOG_HTML_PATH")
if HTML_PATH is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_HTML_PATH is missing."
    )

def build():
    """Builds a directory of static HTML pages."""
    print("Building pbflightlog HTML...")

def run():
    """Launches a server and browser."""
    print("Launching pbflightlog HTML...")
    if not os.path.exists(HTML_PATH):
        raise FileNotFoundError(
            f"HTML path {HTML_PATH} does not exist. "
            "Did you run `pbflightlog build`?"
        )

    # Launch web server
    handler = partial(
        http.server.SimpleHTTPRequestHandler, directory=HTML_PATH
    )
    with http.server.ThreadingHTTPServer(
        ("127.0.0.1", PORT), handler
    ) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"Serving {HTML_PATH} at {url}.")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            sys.exit(0)
