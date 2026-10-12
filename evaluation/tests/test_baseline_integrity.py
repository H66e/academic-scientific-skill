"""Independent pins prevent a shortened or rewritten frozen contract passing."""
import hashlib
import json
from pathlib import Path
import unittest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/native-runtime-baseline.json"


class NativeBaselineIntegrityTests(unittest.TestCase):
    def test_source_observations_are_complete_and_match_the_reviewed_bytes(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "d90295f376725162fe54a0e423804395e0f4e419f2f274a9f07e35293de83f55")
        document = json.loads(raw)
        self.assertIs(document["synthetic"], True)
        self.assertEqual(document["provenance"]["source_commit"], "b2647a94595626f039ef1091cde5f4e5cb908b2b")
        contracts = document["contracts"]
        self.assertEqual(set(contracts), {"audit", "source", "output", "evolution"})
        expected_counts = {"audit": 245, "source": 28, "output": 20, "evolution": 28}
        actual_counts = {key: sum(len(batch["expected"]) for batch in rows) for key, rows in contracts.items()}
        self.assertEqual(actual_counts, expected_counts)
        self.assertEqual(sum(len(rows) for rows in contracts.values()), 14)
        self.assertEqual(sum(actual_counts.values()), 321)
        self.assertEqual([len(batch["expected"]) for batch in contracts["evolution"]], [4, 2, 22])
        for group, batches in contracts.items():
            for batch in batches:
                self.assertTrue(batch["expected"])
                if group != "evolution":
                    self.assertRegex(batch["inputs_sha256"], r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
