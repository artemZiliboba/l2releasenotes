"""Offline tests for transient CDN errors and non-retryable HTTP statuses."""
import importlib.util
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location("nc_collector", "scripts/collect_nc_sources.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestAttachmentRetries(unittest.TestCase):
    def test_502_retries_then_succeeds(self):
        error = HTTPError("https://example.invalid/file", 502, "Bad Gateway", {}, io.BytesIO())
        with patch.object(module, "fetch", side_effect=[error, b"image"]) as fetch:
            data, attempts = module.fetch_attachment("https://example.invalid/file", sleep=lambda _: None)
        self.assertEqual(data, b"image")
        self.assertEqual(attempts, 2)
        self.assertEqual(fetch.call_count, 2)

    def test_406_is_not_retried(self):
        error = HTTPError("https://example.invalid/file", 406, "Not Acceptable", {}, io.BytesIO())
        with patch.object(module, "fetch", side_effect=error) as fetch:
            with self.assertRaises(HTTPError):
                module.fetch_attachment("https://example.invalid/file", sleep=lambda _: None)
        self.assertEqual(fetch.call_count, 1)

    def test_502_stops_after_three_attempts(self):
        error = HTTPError("https://example.invalid/file", 502, "Bad Gateway", {}, io.BytesIO())
        with patch.object(module, "fetch", side_effect=error) as fetch:
            with self.assertRaises(HTTPError):
                module.fetch_attachment("https://example.invalid/file", sleep=lambda _: None)
        self.assertEqual(fetch.call_count, 3)


if __name__ == "__main__":
    unittest.main()
