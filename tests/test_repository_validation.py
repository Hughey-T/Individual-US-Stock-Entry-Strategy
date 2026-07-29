import unittest
from pathlib import Path

from entry_strategy.validation import validate_repository


class RepositoryValidationTests(unittest.TestCase):
    def test_repository_contracts(self):
        validate_repository(Path(__file__).resolve().parents[1])
