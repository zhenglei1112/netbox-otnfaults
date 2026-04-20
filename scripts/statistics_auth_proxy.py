from __future__ import annotations

import argparse
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin

import requests


LOGIN_PATH = "/login/"


def build_session(base_url: str, username: str, password: str, next_path: str) -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    login_page = session.get(base_url, timeout=20)
    login_page.raise_for_status()

    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
    if not match:
        raise RuntimeError("Unable to find CSRF token on login page")

    csrf_token = match.group(1)
    login_url = urljoin(base_url, LOGIN_PATH)
    response = session.post(
        login_url,
        data={
            "csrfmiddlewaretoken": csrf_token,
            "username": username,
            "password": password,
            "next": next_path,
        },
        headers={"Referer": login_url},
        timeout=20,
        allow_redirects=True,
    )
    response.raise_for_status()
    return session


def make_handler(base_url: str, session: requests.Session) -> type[BaseHTTPRequestHandler]:
    class ProxyHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            target_url = urljoin(base_url, self.path)
            response = session.get(target_url, timeout=30)
            self.send_response(response.status_code)

            excluded_headers = {"content-encoding", "transfer-encoding", "connection"}
            for key, value in response.headers.items():
                if key.lower() not in excluded_headers:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.content)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ProxyHandler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--next-path", default="/plugins/otnfaults/statistics/")
    args = parser.parse_args()

    username = os.environ["NETBOX_USERNAME"]
    password = os.environ["NETBOX_PASSWORD"]
    session = build_session(args.base_url, username, password, args.next_path)

    handler = make_handler(args.base_url, session)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
