import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("update_nc_registry", SCRIPTS / "update_nc_registry.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RegistryTests(unittest.TestCase):
    def test_first_run_baseline(self):
        registry, changes = mod.update_registry({"a": {"id": "a", "contentHash": "h1"}}, {})
        self.assertEqual(changes[0]["status"], "new")
        self.assertEqual(registry["records"]["a"]["contentHash"], "h1")

    def test_repeated_run_is_unchanged(self):
        current = {"a": {"id": "a", "contentHash": "h1"}}
        registry, _ = mod.update_registry(current, {})
        next_registry, changes = mod.update_registry(current, registry)
        self.assertEqual(changes[0]["status"], "unchanged")
        self.assertEqual(next_registry, registry)

    def test_edits_and_new_items(self):
        previous = {"schemaVersion": 1, "records": {"a": {"contentHash": "old"}}}
        _, changes = mod.update_registry({"a": {"id": "a", "contentHash": "new"}, "b": {"id": "b", "contentHash": "h"}}, previous)
        self.assertEqual([x["status"] for x in changes], ["changed", "new"])

    def test_out_of_window_items_preserved(self):
        previous = {"schemaVersion": 1, "records": {"old": {"contentHash": "x"}}}
        registry, _ = mod.update_registry({"recent": {"id": "recent", "contentHash": "y"}}, previous)
        self.assertIn("old", registry["records"])

    def test_rejects_corrupt_previous_state(self):
        with self.assertRaises(ValueError):
            mod.update_registry({}, {"schemaVersion": 99, "records": {}})


if __name__ == "__main__":
    unittest.main()
