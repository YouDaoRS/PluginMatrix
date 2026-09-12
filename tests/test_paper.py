import io
import json
import unittest
from unittest.mock import patch

from pluginmatrix.paper import PaperDownloadError, resolve_paper


class PaperDiagnosticsTests(unittest.TestCase):
    @staticmethod
    def response(payload):
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    def test_missing_version_names_current_value_expectation_and_fix(self):
        with patch("pluginmatrix.paper.urllib.request.urlopen", return_value=self.response([])):
            with self.assertRaises(PaperDownloadError) as captured:
                resolve_paper("1.99.9")
        message = str(captured.exception)
        self.assertIn("requested version '1.99.9'", message)
        self.assertIn("Expected", message)
        self.assertIn("correct", message)

    def test_missing_fixed_build_explains_removal_fallback(self):
        builds = [
            {
                "id": 100,
                "channel": "STABLE",
                "downloads": {"server:default": {"name": "paper.jar", "url": "https://example.invalid"}},
            }
        ]
        with patch("pluginmatrix.paper.urllib.request.urlopen", return_value=self.response(builds)):
            with self.assertRaises(PaperDownloadError) as captured:
                resolve_paper("1.20.1", 196)
        message = str(captured.exception)
        self.assertIn("paper_build 196", message)
        self.assertIn("Paper 1.20.1", message)
        self.assertIn("remove it", message)
