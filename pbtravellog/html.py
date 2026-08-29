"""Builds and runs a static HTML travel log."""

# Standard imports
import http.server
import os
import sys
import shutil
import webbrowser
from functools import partial
from importlib.resources import files, as_file
from pathlib import Path

# Third-party imports
from jinja2 import Environment, PackageLoader

HTML_PATH = os.getenv("PBTRAVELLOG_HTML_PATH")
if HTML_PATH is None:
    raise KeyError(
        "Environment variable PBTRAVELLOG_HTML_PATH is missing."
    )

def build():
    """Builds a directory of static HTML pages."""
    print("Building pbflightlog HTML...")
    html_path = Path(HTML_PATH)

    # Create root and static folders.
    html_path.mkdir(parents=True, exist_ok=True)
    static_dir = files("pbtravellog") / "static"
    with as_file(static_dir) as static_path:
        shutil.copytree(static_path, html_path, dirs_exist_ok=True)

    env = Environment(
        loader=PackageLoader("pbtravellog"),
        autoescape=True,
    )
    site_index = env.get_template('site_index.html')
    site_index_html = site_index.render()
    (html_path / "index.html").write_text(site_index_html, encoding="utf-8")

    print(f"Wrote static site to \"{html_path}\".")

def run(port):
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
        ("127.0.0.1", port), handler
    ) as httpd:
        url = f"http://localhost:{port}"
        print(f"Serving directory \"{HTML_PATH}\" at {url}.")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            sys.exit(0)
