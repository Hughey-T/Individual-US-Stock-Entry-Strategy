import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from entry_strategy.storage import Store
from entry_strategy.validation import ValidationError, strict_json_loads


class StrictPublicationTests(unittest.TestCase):
    def test_strict_json_mutations(self):
        cases = {
            "malformed_utf8": b'\xff{"x":1}',
            "duplicate_key": b'{"x":1,"x":2}',
            "nan": b'{"x":NaN}',
            "infinity": b'{"x":Infinity}',
        }
        for name, raw in cases.items():
            with self.subTest(name=name), self.assertRaises(ValidationError):
                strict_json_loads(raw)

    def test_missing_raw_hash_canonical_and_active_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = ("missing", "raw", "canonical", "active")
            for case in cases:
                case_root = root / case
                store = Store(case_root)
                raw = b'{"phase_identity":"initial-1","x":1}'
                store.publish("s", "initial-1", raw)
                active_path = case_root / "s" / "active"
                digest = active_path.read_text()
                generation = case_root / "s" / "generations" / digest
                if case == "missing":
                    (generation / "artifact.json").unlink()
                elif case == "raw":
                    (generation / "artifact.json").write_bytes(b"{}")
                elif case == "canonical":
                    manifest_path = generation / "manifest.json"
                    manifest = json.loads(manifest_path.read_text())
                    manifest["canonical_sha256"] = hashlib.sha256(b"wrong").hexdigest()
                    manifest_path.write_text(json.dumps(manifest))
                else:
                    active_path.write_text("0" * 64)
                with self.subTest(case=case), self.assertRaises(ValidationError):
                    store.verify("s")

    def test_failed_new_publication_preserves_previous_active(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            raw = b'{"phase_identity":"initial-1"}'
            store.publish("s", "initial-1", raw)
            active = store.verify("s")["active"]
            with self.assertRaises(ValidationError):
                store.publish("s", "initial-2", b'{"x":NaN}')
            self.assertEqual(store.verify("s")["active"], active)

    def test_manifest_identity_and_contract_tamper(self):
        for field, value in (
            ("strategy_identity", "another-session"),
            ("phase_identity", "initial-2"),
            ("contract_version", "2.0.0"),
            ("schema_version", "2.0.0"),
            ("artifact_identity", "0" * 64),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                store = Store(Path(directory))
                store.publish("session", "initial-1", b'{"phase_identity":"initial-1"}')
                active = store.verify("session")["active"]
                manifest_path = (
                    Path(directory) / "session" / "generations" / active / "manifest.json"
                )
                manifest = json.loads(manifest_path.read_text())
                manifest[field] = value
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValidationError, "hash or canonical"):
                    store.verify("session")
