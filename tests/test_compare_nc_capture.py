import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "compare_nc_capture.py"
spec = importlib.util.spec_from_file_location("compare_nc_capture", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CompareCaptureTests(unittest.TestCase):
    def test_ignores_view_counts(self):
        a = {"article": {"title": "Notice", "content": {"content": "<p>100</p>"}, "viewCount": 1}}
        b = {"article": {"title": "Notice", "content": {"content": "<p>100</p>"}, "viewCount": 999}}
        self.assertEqual(mod.content_hash(a), mod.content_hash(b))

    def test_detects_body_edit(self):
        a = {"article": {"title": "Notice", "content": {"content": "<p>100</p>"}}}
        b = {"article": {"title": "Notice", "content": {"content": "<p>200</p>"}}}
        self.assertNotEqual(mod.content_hash(a), mod.content_hash(b))

    def test_detects_title_and_attachment_edits(self):
        a = {"article": {"title": "A", "content": {"content": "x", "attachments": {"files": [{"fileUrl": "https://example/a", "fileSize": 10}]}}}}
        b = {"article": {"title": "B", "content": {"content": "x", "attachments": {"files": [{"fileUrl": "https://example/a", "fileSize": 10}]}}}}
        c = {"article": {"title": "A", "content": {"content": "x", "attachments": {"files": [{"fileUrl": "https://example/b", "fileSize": 10}]}}}}
        self.assertNotEqual(mod.content_hash(a), mod.content_hash(b))
        self.assertNotEqual(mod.content_hash(a), mod.content_hash(c))

    def test_classifies_new_changed_unchanged(self):
        prev = {"a": {"contentHash": "same"}, "b": {"contentHash": "old"}}
        current = {"a": {"id": "a", "contentHash": "same"}, "b": {"id": "b", "contentHash": "new"}, "c": {"id": "c", "contentHash": "fresh"}}
        self.assertEqual([r["status"] for r in mod.compare(current, prev)], ["unchanged", "changed", "new"])

    def test_reads_manifest_and_detail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "l2update"
            article = root / "articles" / "abc"
            article.mkdir(parents=True)
            (root / "manifest.json").write_text(json.dumps({"records": [{"id": "abc", "title": "X"}]}), encoding="utf-8")
            (article / "article.json").write_text(json.dumps({"article": {"title": "X", "content": {"content": "<p>ok</p>"}}}), encoding="utf-8")
            result = mod.load_capture(Path(temp))
            self.assertEqual(result["abc"]["serverFamily"], "unverified")
            self.assertEqual(len(result["abc"]["contentHash"]), 64)


if __name__ == "__main__":
    unittest.main()
