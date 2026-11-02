import tempfile
import unittest
from pathlib import Path
from scripts.import_patch import import_patch

RECORD = {"source_id":"sample-id","source_url":"https://lineage2.plaync.com/board/l2update/view?articleId=sample-id","date":"2026-11-02","title":"Тест","summary":"Тестовый текст","body":"## Проверка\nТекст","reviewed":True}

class ImportPatchTests(unittest.TestCase):
    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=import_patch(RECORD,Path(tmp))
            self.assertEqual(a,import_patch(RECORD,Path(tmp)))
            self.assertIn("Проверка",a.read_text())
    def test_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                import_patch({**RECORD,"reviewed":False},Path(tmp))
    def test_rejects_unofficial_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                import_patch({**RECORD,"source_url":"https://evil.example/patch"},Path(tmp))
if __name__=="__main__":
    unittest.main()
