import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class SchemaTests(unittest.TestCase):
    def test_all_json_parses(self):
        for p in (
            list(ROOT.glob("schemas/*.json"))
            + list(ROOT.glob("fixtures/**/*.json"))
            + list(ROOT.glob("samples/*.json"))
        ):
            json.loads(p.read_text())

    def test_samples_validate_when_jsonschema_available(self):
        try:
            import jsonschema
        except ImportError:
            self.fail("jsonschema dev dependency is required")
        schema = json.loads((ROOT / "schemas/entry-strategy-output.schema.json").read_text())
        data = json.loads((ROOT / "samples/final-execution-card.json").read_text())
        jsonschema.validate(data, schema)
