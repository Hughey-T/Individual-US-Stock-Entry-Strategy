import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
from threading import Thread
import unittest
import urllib.error
import urllib.request

from entry_strategy.api import Handler
from entry_strategy.runtime import Runtime


class ApiTests(unittest.TestCase):
    def test_health_auth_and_session_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            Handler.runtime = Runtime(Path(directory))
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = Thread(target=server.serve_forever)
            thread.start()
            connection = HTTPConnection("127.0.0.1", server.server_port)
            try:
                connection.request("GET", "/health")
                self.assertEqual(connection.getresponse().status, 200)
                connection.request("GET", "/sessions/missing/next")
                self.assertEqual(connection.getresponse().status, 401)
                headers = {
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                }
                # Handler is fail-closed and reads the token dynamically.
                os.environ["ENTRY_STRATEGY_TOKEN"] = "test-token"
                connection.request(
                    "POST",
                    "/sessions",
                    json.dumps({"ticker": "ACME", "mode": "standalone_runtime"}),
                    headers,
                )
                response = connection.getresponse()
                self.assertEqual(response.status, 201)
                sid = json.loads(response.read())["session_id"]
                connection.request("GET", f"/sessions/{sid}/next", headers=headers)
                self.assertEqual(connection.getresponse().status, 200)
                artifact = json.dumps({"phase_identity": "initial-1"})
                connection.request("POST", f"/sessions/{sid}/phases/initial-1", artifact, headers)
                self.assertEqual(connection.getresponse().status, 201)
                for operation in ("active", "integrity", "ledger", "resume"):
                    connection.request("GET", f"/sessions/{sid}/{operation}", headers=headers)
                    self.assertEqual(connection.getresponse().status, 200)
            finally:
                server.shutdown()
                thread.join()
                server.server_close()
                connection.close()
                os.environ.pop("ENTRY_STRATEGY_TOKEN", None)

    def test_request_boundaries_use_strict_json_and_restore_is_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            Handler.runtime = Runtime(Path(directory) / "live")
            os.environ["ENTRY_STRATEGY_TOKEN"] = "secret"
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = Thread(target=server.serve_forever)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            headers = {"Authorization": "Bearer secret", "Content-Type": "application/json"}
            try:
                for raw in (
                    b'{"ticker":"A","ticker":"B","mode":"standalone_runtime"}',
                    b'{"ticker":"A","mode":"standalone_runtime","value":NaN}',
                    b"\xff",
                ):
                    request = urllib.request.Request(
                        base + "/sessions", data=raw, headers=headers, method="POST"
                    )
                    with self.subTest(raw=raw), self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(request)
                    self.assertEqual(caught.exception.code, 422)

                request = urllib.request.Request(
                    base + "/restores",
                    data=json.dumps(
                        {
                            "archive": str(Path(directory) / "missing.tar.gz"),
                            "destination": str(Path(directory) / "restore"),
                        }
                    ).encode(),
                    headers=headers,
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code, 422)
            finally:
                server.shutdown()
                thread.join()
                server.server_close()
                os.environ.pop("ENTRY_STRATEGY_TOKEN", None)
