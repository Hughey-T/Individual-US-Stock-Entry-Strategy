"""Dependency-free authenticated REST interface for the optional runtime."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .runtime import Runtime
from .validation import require_object


class Handler(BaseHTTPRequestHandler):
    runtime: Runtime | None = None

    @classmethod
    def _get_runtime(cls) -> Runtime:
        if cls.runtime is None:
            cls.runtime = Runtime(Path(os.environ.get("ENTRY_STRATEGY_DATA", "/data")))
        return cls.runtime

    def _send(self, status: int, data: object) -> None:
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _auth(self) -> bool:
        expected = os.environ.get("ENTRY_STRATEGY_TOKEN")
        if not expected or self.headers.get("Authorization") != f"Bearer {expected}":
            self._send(401, {"error": "unauthorized"})
            return False
        return True

    def _raw(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", "0")))

    def _json(self) -> dict[str, Any]:
        return require_object(self._raw(), context="request body")

    def do_GET(self) -> None:
        runtime = self._get_runtime()
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, runtime.health())
            return
        if not self._auth():
            return
        parts = path.strip("/").split("/")
        try:
            if len(parts) == 3 and parts[0] == "sessions":
                session_id, operation = parts[1], parts[2]
                operations = {
                    "next": runtime.next_contract,
                    "active": runtime.active_plan,
                    "superseded": runtime.superseded,
                    "ledger": runtime.ledger,
                    "integrity": runtime.integrity,
                    "resume": runtime.resume,
                }
                if operation in operations:
                    self._send(200, operations[operation](session_id))
                    return
            self._send(404, {"error": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._send(400, {"error": str(exc)})

    def do_POST(self) -> None:
        runtime = self._get_runtime()
        if not self._auth():
            return
        parts = urlparse(self.path).path.strip("/").split("/")
        try:
            if parts == ["sessions"]:
                body = self._json()
                self._send(201, runtime.create_session(body["ticker"], body["mode"]))
                return
            if len(parts) >= 3 and parts[0] == "sessions":
                session_id, operation = parts[1], parts[2]
                if operation == "phases" and len(parts) == 4:
                    self._send(201, runtime.submit_phase(session_id, self._raw(), parts[3]))
                    return
                if operation == "entry-gate":
                    body = self._json()
                    self._send(
                        200,
                        runtime.freeze_entry_gate(session_id, body["gate"], body["evidence"]),
                    )
                    return
                if operation == "reconciliation":
                    self._send(200, runtime.disclose_reconciliation(session_id))
                    return
                if operation == "terminal":
                    body = self._json()
                    self._send(
                        200,
                        runtime.terminal_stop(
                            session_id,
                            body["gate"],
                            reason=body["reason"],
                            missing_evidence=body["missing_evidence"],
                            required_next_action=body["required_next_action"],
                            reactivation_condition=body["reactivation_condition"],
                            monitoring_condition=body["monitoring_condition"],
                        ),
                    )
                    return
                if operation == "updates":
                    self._send(201, runtime.start_update(session_id))
                    return
            if parts == ["backups"]:
                body = self._json()
                self._send(201, runtime.backup(Path(body["destination"])))
                return
            if parts == ["restores"]:
                body = self._json()
                restored = runtime.restore(Path(body["archive"]), Path(body["destination"]))
                self._send(201, {"restored": True, "root": str(restored.store.root)})
                return
            self._send(404, {"error": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._send(422, {"error": str(exc)})


def main() -> None:
    Handler.runtime = Runtime(Path(os.environ.get("ENTRY_STRATEGY_DATA", "/data")))
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()


if __name__ == "__main__":
    main()
