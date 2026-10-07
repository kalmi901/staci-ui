"""Isolated Caddy integration fixture; never mount/run against production data."""
import json
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from flask import Flask, request
from src.logging_setup import configure_logging


def serve():
    configure_logging()

    class Auth(BaseHTTPRequestHandler):
        def do_GET(self):
            identities = {"fixture=alice": ("41", "alice"), "fixture=bob": ("42", "bob")}
            identity = identities.get(self.headers.get("Cookie"))
            self.send_response(204 if identity else 401)
            if identity:
                self.send_header("X-Staci-Access", "allowed")
                self.send_header("X-Staci-User-Id", identity[0])
                self.send_header("X-Staci-User-Login", identity[1])
            self.end_headers()

        def log_message(self, *args):
            pass

    threading.Thread(target=ThreadingHTTPServer(("0.0.0.0", 80), Auth).serve_forever,
                     daemon=True).start()
    app = Flask(__name__)

    @app.route("/staci-app/", methods=["GET", "POST"])
    def workflow():
        logging.getLogger("workflow").info("Proxy identity integration test")
        return {
            "id": request.headers.get("X-Staci-User-Id"),
            "login": request.headers.get("X-Staci-User-Login"),
            "cookie": request.headers.get("Cookie"),
            "authorization": request.headers.get("Authorization"),
            "access": request.headers.get("X-Staci-Access"),
        }

    app.run(host="0.0.0.0", port=8050, use_reloader=False)


def verify():
    headers = {"Host": "verification.test", "X-Staci-Access": "allowed",
               "X-Staci-User-Id": "999", "X-Staci-User-Login": "forged",
               "Authorization": "fixture-only"}
    try:
        urlopen(Request("http://proxy/staci-app/", headers=headers), timeout=10)
        raise AssertionError("Anonymous forged identity was accepted")
    except HTTPError as error:
        assert error.code == 401, error.code
    for name, user_id in [("alice", "41"), ("bob", "42")]:
        for method in ["GET", "POST"]:
            query = Request("http://proxy/staci-app/", method=method,
                            headers={**headers, "Cookie": f"fixture={name}"})
            with urlopen(query, timeout=10) as response:
                result = json.load(response)
            assert result == {"id": user_id, "login": name, "cookie": None,
                              "authorization": None, "access": None}, result
    print("PASS: anonymous denial, two identities, forged headers replaced, credentials stripped")


if __name__ == "__main__":
    serve() if sys.argv[1] == "serve" else verify()
