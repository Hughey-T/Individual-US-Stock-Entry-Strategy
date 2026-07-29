import copy
import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).parents[1]


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_schema = json.loads(
            (ROOT / "schemas/entry-strategy-output.schema.json").read_text()
        )
        cls.state_schema = json.loads(
            (ROOT / "schemas/entry-strategy-state.schema.json").read_text()
        )
        cls.output = json.loads((ROOT / "fixtures/valid/final-output.json").read_text())
        cls.state = json.loads((ROOT / "fixtures/valid/state.json").read_text())

    def test_valid_fixtures_and_sample_really_validate(self):
        jsonschema.Draft202012Validator.check_schema(self.output_schema)
        jsonschema.Draft202012Validator.check_schema(self.state_schema)
        jsonschema.validate(self.output, self.output_schema)
        jsonschema.validate(self.state, self.state_schema)
        sample = json.loads((ROOT / "samples/final-execution-card.json").read_text())
        jsonschema.validate(sample, self.output_schema)

    def test_output_rejects_missing_unknown_and_bad_enums(self):
        cases = []
        missing = copy.deepcopy(self.output)
        del missing["invalidations"]["investment_thesis_review"]
        cases.append(missing)
        unknown = copy.deepcopy(self.output)
        unknown["execution_card"]["broker_order"] = "market"
        cases.append(unknown)
        bad_enum = copy.deepcopy(self.output)
        bad_enum["event_dominance"] = "存在"
        cases.append(bad_enum)
        empty = copy.deepcopy(self.output)
        empty["coverage"]["items"] = []
        cases.append(empty)
        no_number = copy.deepcopy(self.output)
        no_number["execution_card"]["first_condition"] = "主要支持帯で反転"
        cases.append(no_number)
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(payload, self.output_schema)

    def test_state_schema_enforces_zone_lock_dependency(self):
        unlocked_with_zone = copy.deepcopy(self.state)
        unlocked_with_zone.update(zones_locked=False, zones_locked_at_phase=None)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(unlocked_with_zone, self.state_schema)
        locked_without_phase = copy.deepcopy(self.state)
        locked_without_phase["zones_locked_at_phase"] = None
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(locked_without_phase, self.state_schema)
        update_not_complete = copy.deepcopy(self.state)
        update_not_complete.update(mode="update", current_phase=1, initial_complete=False)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(update_not_complete, self.state_schema)

    def test_stopped_decision_has_no_purchase_route(self):
        stopped = copy.deepcopy(self.output)
        stopped["decision"].update(current_action="購入計画中止", routes=[], route_priority=[])
        stopped["execution_card"]["current_action"] = "購入計画中止"
        jsonschema.validate(stopped, self.output_schema)
        stopped["decision"]["routes"] = ["押し目"]
        stopped["decision"]["route_priority"] = ["押し目"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(stopped, self.output_schema)
