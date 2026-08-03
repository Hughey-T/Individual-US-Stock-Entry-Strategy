import io
import json
from pathlib import Path
import tarfile
import tempfile
from threading import Thread
import unittest

from entry_strategy.runtime import Runtime
from entry_strategy.storage import Store
from entry_strategy.validation import ValidationError


class RuntimeCompletionTests(unittest.TestCase):
    def _artifact(self, phase: str, marker: int = 0) -> bytes:
        return json.dumps({"phase_identity": phase, "marker": marker}).encode()

    def test_standalone_runtime_full_initial_update_resume_and_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            created = runtime.create_session("ACME", "standalone_runtime")
            sid = created["session_id"]
            self.assertEqual(created["next_contract"]["phase"], 1)
            for phase in range(1, 13):
                if phase == 2:
                    runtime.freeze_entry_gate(sid, "ENTRY_PLANNING_ALLOWED", ["evidence"])
                receipt = runtime.submit_phase(
                    sid, self._artifact(f"initial-{phase}"), f"initial-{phase}"
                )
                self.assertTrue(receipt["accepted"])
            resumed = runtime.resume(sid)
            self.assertTrue(resumed["state"]["initial_complete"])
            self.assertEqual(runtime.active_plan(sid)["phase_identity"], "initial-12")
            self.assertEqual(len(runtime.ledger(sid)["generations"]), 12)
            update = runtime.start_update(sid)
            self.assertEqual(update["phase"], 1)
            for phase in range(1, 6):
                runtime.submit_phase(sid, self._artifact(f"update-{phase}"), f"update-{phase}")
            self.assertEqual(runtime.active_plan(sid)["phase_identity"], "update-5")
            self.assertEqual(len(runtime.superseded(sid)), 16)

    def test_pipeline_gate_and_reconciliation_e2e(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            sid = runtime.create_session("ACME", "pipeline")["session_id"]
            with self.assertRaises(ValueError):
                runtime.disclose_reconciliation(sid)
            runtime.submit_phase(sid, self._artifact("initial-1"), "initial-1")
            frozen = runtime.freeze_entry_gate(
                sid, "ENTRY_PLANNING_CONDITIONAL", ["blind-evidence"]
            )
            self.assertTrue(frozen["frozen"])
            with self.assertRaises(ValueError):
                runtime.freeze_entry_gate(sid, "NO_ENTRY", ["overwrite"])
            runtime.submit_phase(sid, self._artifact("initial-2"), "initial-2")
            self.assertTrue(runtime.disclose_reconciliation(sid)["disclosed"])
            self.assertEqual(
                runtime.resume(sid)["state"]["independent_entry_gate"],
                "ENTRY_PLANNING_CONDITIONAL",
            )

    def test_runtime_terminal_stop_has_complete_metadata_and_no_next_progression(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            sid = runtime.create_session("ACME", "standalone_runtime")["session_id"]
            result = runtime.terminal_stop(
                sid,
                "INSUFFICIENT_EVIDENCE",
                reason="missing current price",
                missing_evidence=["current price"],
                required_next_action="refresh sources",
                reactivation_condition="price available",
                monitoring_condition="source status",
            )
            self.assertTrue(result["terminal"])
            self.assertEqual(result["terminal_state"], "INSUFFICIENT_EVIDENCE")
            self.assertTrue(runtime.resume(sid)["state"]["terminal"])

    def test_static_runtime_boundary_and_phase_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            with self.assertRaises(ValidationError):
                runtime.create_session("ACME", "standalone_static")
            sid = runtime.create_session("ACME", "standalone_runtime")["session_id"]
            with self.assertRaisesRegex(ValidationError, "current contract"):
                runtime.submit_phase(sid, self._artifact("initial-2"), "initial-2")

    def test_concurrent_submission_only_one_current_phase_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            sid = runtime.create_session("ACME", "standalone_runtime")["session_id"]
            outcomes: list[str] = []

            def submit(marker: int) -> None:
                try:
                    runtime.submit_phase(sid, self._artifact("initial-1", marker), "initial-1")
                    outcomes.append("accepted")
                except ValidationError:
                    outcomes.append("rejected")

            threads = [Thread(target=submit, args=(marker,)) for marker in (1, 2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(sorted(outcomes), ["accepted", "rejected"])
            self.assertEqual(runtime.resume(sid)["state"]["current_phase"], 2)
            self.assertIn(runtime.active_plan(sid)["marker"], (1, 2))
            generations = runtime.ledger(sid)["generations"]
            self.assertEqual(len(generations), 1, (outcomes, generations, runtime.resume(sid)))

    def test_backup_restore_round_trip_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = Runtime(root / "live")
            sid = runtime.create_session("ACME", "standalone_runtime")["session_id"]
            runtime.submit_phase(sid, self._artifact("initial-1"), "initial-1")
            backup = root / "backup.tar.gz"
            receipt = runtime.backup(backup)
            self.assertEqual(len(receipt["sha256"]), 64)
            restored = runtime.restore(backup, root / "restored")
            self.assertTrue(restored.integrity(sid)["integrity_verified"])
            self.assertEqual(restored.active_plan(sid)["phase_identity"], "initial-1")

            tampered = root / "tampered.tar.gz"
            with tarfile.open(backup, "r:gz") as source, tarfile.open(tampered, "w:gz") as target:
                for member in source.getmembers():
                    extracted = source.extractfile(member) if member.isfile() else None
                    if member.name.endswith("artifact.json"):
                        payload = io.BytesIO(b"{}")
                        member.size = 2
                        target.addfile(member, payload)
                    else:
                        target.addfile(member, extracted)
            with self.assertRaises(ValidationError):
                Runtime(root / "other").restore(tampered, root / "rejected")

    def test_publication_inventory_pointer_symlink_and_rollback_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root)
            first = json.dumps({"phase_identity": "initial-1"}).encode()
            store.publish("session", "initial-1", first)
            active = store.verify("session")["active"]
            generation = root / "session" / "generations" / active
            (generation / "extra.json").write_text("{}")
            with self.assertRaisesRegex(ValidationError, "inventory"):
                store.verify("session")
            (generation / "extra.json").unlink()
            (root / "session" / "active").write_text("../escape")
            with self.assertRaisesRegex(ValidationError, "pointer"):
                store.verify("session")

    def test_backup_rejects_path_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, configure in (
                ("traversal.tar.gz", lambda info: setattr(info, "name", "../escape")),
                ("symlink.tar.gz", lambda info: setattr(info, "type", tarfile.SYMTYPE)),
            ):
                archive = root / name
                info = tarfile.TarInfo("file")
                info.size = 0
                configure(info)
                with tarfile.open(archive, "w:gz") as target:
                    target.addfile(info, io.BytesIO())
                with self.subTest(name=name), self.assertRaises(ValidationError):
                    Store.restore(archive, root / f"restore-{name}")
