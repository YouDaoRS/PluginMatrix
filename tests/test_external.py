import os
import sys
import unittest
from unittest.mock import patch

from pluginmatrix.external import external_environment


class FrozenExternalEnvironmentTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt" or sys.platform == "darwin", "LD_LIBRARY_PATH applies to frozen Unix bundles")
    def test_frozen_external_environment_restores_original_library_path(self):
        with patch.object(sys, "frozen", True, create=True), patch.dict(
            os.environ, {"LD_LIBRARY_PATH": "/bundle", "LD_LIBRARY_PATH_ORIG": "/system"}, clear=True
        ):
            environment = external_environment()
        self.assertEqual(environment["LD_LIBRARY_PATH"], "/system")
        self.assertEqual(environment["LD_LIBRARY_PATH_ORIG"], "/system")

    @unittest.skipIf(os.name == "nt" or sys.platform == "darwin", "LD_LIBRARY_PATH applies to frozen Unix bundles")
    def test_frozen_external_environment_removes_injected_path_without_original(self):
        with patch.object(sys, "frozen", True, create=True), patch.dict(
            os.environ, {"LD_LIBRARY_PATH": "/bundle"}, clear=True
        ):
            environment = external_environment()
        self.assertNotIn("LD_LIBRARY_PATH", environment)

    def test_non_frozen_environment_is_preserved(self):
        with patch.object(sys, "frozen", False, create=True), patch.dict(os.environ, {"PLUGINMATRIX_TEST": "yes"}, clear=True):
            self.assertEqual(external_environment(), {"PLUGINMATRIX_TEST": "yes"})
