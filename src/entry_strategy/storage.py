"""Atomic, locked immutable storage and verified backup/restore.

The store validates and persists caller-supplied artifacts. It never performs analysis.
"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from threading import Lock, RLock
from typing import Any, Iterator

from .validation import ValidationError, strict_json_loads

_PROCESS_LOCKS: dict[str, RLock] = {}
_PROCESS_LOCKS_GUARD = Lock()


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _session(self, sid: str) -> Path:
        if not sid or any(char in sid for char in ("/", "\\", "..")):
            raise ValidationError("invalid session identity")
        path = (self.root / sid).resolve()
        if path.parent != self.root:
            raise ValidationError("session path traversal")
        return path

    @contextmanager
    def session_lock(self, sid: str) -> Iterator[None]:
        session = self._session(sid)
        session.mkdir(parents=True, exist_ok=True)
        key = str(session)
        with _PROCESS_LOCKS_GUARD:
            process_lock = _PROCESS_LOCKS.setdefault(key, RLock())
        with process_lock:
            lock_path = session / ".lock"
            with lock_path.open("a+b") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _hashes(raw: bytes, payload: dict[str, Any]) -> tuple[str, str]:
        raw_digest = hashlib.sha256(raw).hexdigest()
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
        return raw_digest, hashlib.sha256(canonical).hexdigest()

    def publish(
        self, sid: str, phase: str, raw: bytes, *, _already_locked: bool = False
    ) -> dict[str, Any]:
        payload = strict_json_loads(raw)
        if not isinstance(payload, dict):
            raise ValidationError("artifact must be an object")
        digest, canonical_digest = self._hashes(raw, payload)
        lock_context = nullcontext() if _already_locked else self.session_lock(sid)
        with lock_context:
            session = self._session(sid)
            generations = session / "generations"
            generations.mkdir(exist_ok=True)
            generation = generations / digest
            if generation.exists():
                verified = self._verify_generation(sid, digest)
                if verified["manifest"]["canonical_sha256"] != canonical_digest:
                    raise ValidationError("generation collision")
                return {
                    "accepted": True,
                    "replay": True,
                    "readback_verified": True,
                    "raw_sha256": digest,
                    "canonical_sha256": canonical_digest,
                }

            tmp = Path(tempfile.mkdtemp(prefix=".publish-", dir=generations))
            manifest = {
                "strategy_identity": sid,
                "phase_identity": phase,
                "artifact_identity": digest,
                "contract_version": "3.0.0",
                "schema_version": "3.0.0",
                "raw_sha256": digest,
                "canonical_sha256": canonical_digest,
                "byte_length": len(raw),
                "inventory": ["artifact.json", "manifest.json"],
            }
            previous_active = (
                (session / "active").read_text() if (session / "active").is_file() else None
            )
            try:
                (tmp / "artifact.json").write_bytes(raw)
                (tmp / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
                os.replace(tmp, generation)
                # Verify the new generation before changing the active pointer.
                self._verify_generation(sid, digest)
                pointer_tmp = session / ".active.tmp"
                pointer_tmp.write_text(digest)
                os.replace(pointer_tmp, session / "active")
                verified = self._verify_unlocked(sid)
                if verified["integrity_verified"] is not True:
                    raise ValidationError("readback verification failed")
            except Exception:
                if previous_active is not None:
                    rollback_tmp = session / ".active.rollback"
                    rollback_tmp.write_text(previous_active)
                    os.replace(rollback_tmp, session / "active")
                if tmp.exists():
                    shutil.rmtree(tmp)
                if generation.exists() and not (session / "active").exists():
                    shutil.rmtree(generation)
                raise
            return {"accepted": True, "replay": False, "readback_verified": True, **manifest}

    def _verify_generation(self, sid: str, digest: str) -> dict[str, Any]:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValidationError("active pointer tamper")
        generation = self._session(sid) / "generations" / digest
        if not generation.is_dir() or generation.is_symlink():
            raise ValidationError("missing artifact or symlink forbidden")
        files = list(generation.iterdir())
        if any(path.is_symlink() for path in files):
            raise ValidationError("symlink forbidden")
        if {path.name for path in files} != {"artifact.json", "manifest.json"}:
            raise ValidationError("publication inventory mismatch")
        raw = (generation / "artifact.json").read_bytes()
        payload = strict_json_loads(raw)
        if not isinstance(payload, dict):
            raise ValidationError("artifact must be an object")
        manifest = strict_json_loads((generation / "manifest.json").read_bytes())
        raw_digest, canonical_digest = self._hashes(raw, payload)
        expected_manifest = {
            "strategy_identity": sid,
            "phase_identity": manifest.get("phase_identity"),
            "artifact_identity": digest,
            "contract_version": "3.0.0",
            "schema_version": "3.0.0",
            "raw_sha256": digest,
            "canonical_sha256": canonical_digest,
            "byte_length": len(raw),
            "inventory": ["artifact.json", "manifest.json"],
        }
        if (
            raw_digest != digest
            or manifest != expected_manifest
            or payload.get("phase_identity") != manifest.get("phase_identity")
        ):
            raise ValidationError("publication hash or canonical mismatch")
        return {"integrity_verified": True, "active": digest, "manifest": manifest}

    def _verify_unlocked(self, sid: str) -> dict[str, Any]:
        pointer = self._session(sid) / "active"
        if pointer.is_symlink() or not pointer.is_file():
            raise ValidationError("active pointer tamper")
        return self._verify_generation(sid, pointer.read_text())

    def verify(self, sid: str) -> dict[str, Any]:
        with self.session_lock(sid):
            return self._verify_unlocked(sid)

    def read_active(self, sid: str) -> Any:
        with self.session_lock(sid):
            info = self._verify_unlocked(sid)
            path = self._session(sid) / "generations" / info["active"] / "artifact.json"
            return strict_json_loads(path.read_bytes())

    def history(self, sid: str) -> list[str]:
        with self.session_lock(sid):
            generations = self._session(sid) / "generations"
            if not generations.exists():
                return []
            return sorted(path.name for path in generations.iterdir() if path.is_dir())

    def backup(self, destination: Path) -> dict[str, Any]:
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with tarfile.open(temporary_path, "w:gz") as archive:
                for session in sorted(self.root.iterdir()):
                    if session.is_dir() and not session.is_symlink():
                        with self.session_lock(session.name):
                            if (session / "active").exists():
                                self._verify_unlocked(session.name)
                            archive.add(session, arcname=session.name, recursive=True)
            digest = hashlib.sha256(temporary_path.read_bytes()).hexdigest()
            os.replace(temporary_path, destination)
            return {"backup": str(destination), "sha256": digest}
        finally:
            temporary_path.unlink(missing_ok=True)

    @classmethod
    def restore(cls, archive_path: Path, destination: Path) -> Store:
        archive_path = archive_path.resolve()
        destination = destination.resolve()
        if destination.exists() and any(destination.iterdir()):
            raise ValidationError("restore destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            staging = Path(temporary) / "restore"
            staging.mkdir()
            with tarfile.open(archive_path, "r:gz") as archive:
                for member in archive.getmembers():
                    member_path = Path(member.name)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise ValidationError("backup path traversal")
                    if member.issym() or member.islnk():
                        raise ValidationError("backup symlink forbidden")
                archive.extractall(staging, filter="data")
            candidate = cls(staging)
            for session in staging.iterdir():
                if session.is_dir():
                    candidate.verify(session.name)
            for item in staging.iterdir():
                os.replace(item, destination / item.name)
        restored = cls(destination)
        return restored
