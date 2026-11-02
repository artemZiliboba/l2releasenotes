import unittest
from scripts.translate_patch import translate

class TranslationValidationTests(unittest.TestCase):
    def test_missing_fields_fails_before_network(self):
        with self.assertRaises(ValueError):
            translate({"source_id":"1"},"not-a-real-key")
    def test_oversized_source_fails_before_network(self):
        data={"source_id":"1","source_url":"https://lineage2.plaync.com","date":"2026-11-02","korean_title":"제목","korean_body":"가"*50001}
        with self.assertRaises(ValueError):
            translate(data,"not-a-real-key")
if __name__=="__main__":
    unittest.main()
