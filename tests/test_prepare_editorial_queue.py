import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "prepare_editorial_queue.py"
spec = importlib.util.spec_from_file_location("prepare_editorial_queue", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class EditorialQueueTests(unittest.TestCase):
    def test_counts_html_structures(self):
        audit = mod.SourceAudit()
        audit.feed('<table><tr><td>1</td></tr><tr><td>2</td></tr></table><a href="/">x</a><img src="x">')
        self.assertEqual((audit.tables, audit.rows, audit.images, audit.links), (1, 2, 1, 1))

    def test_builds_unpublished_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "l2update"
            article = root / "articles" / "a"
            article.mkdir(parents=True)
            (root / "manifest.json").write_text(json.dumps({"records": [{"id": "a", "title": "Listing", "sourceUrl": "https://lineage2.plaync.com/board/l2update/view?articleId=a"}]}), encoding="utf-8")
            (article / "article.json").write_text(json.dumps({"article": {"contentMeta": {"title": "Actual"}, "content": {"content": "<table><tr><td>x</td></tr></table>"}}}), encoding="utf-8")
            queue = mod.build_queue(Path(tmp))["entries"]
            self.assertEqual(queue[0]["titleKorean"], "Actual")
            self.assertEqual(queue[0]["audit"]["rows"], 1)
            self.assertFalse(queue[0]["publishApproved"])

    def test_rejects_empty_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "l2update"
            article = root / "articles" / "a"
            article.mkdir(parents=True)
            (root / "manifest.json").write_text(json.dumps({"records": [{"id": "a", "title": "x"}]}), encoding="utf-8")
            (article / "article.json").write_text(json.dumps({"article": {"content": {"content": ""}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.build_queue(Path(tmp))


if __name__ == "__main__":
    unittest.main()
