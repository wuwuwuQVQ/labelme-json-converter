import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from labelme_json_converter.diagnostics import (  # noqa: E402
    run_core_self_test,
    run_ui_smoke_test,
)


class PackagedDiagnosticsTests(unittest.TestCase):
    def test_core_self_test(self):
        self.assertEqual(run_core_self_test(), 0)

    def test_ui_smoke_test_exercises_all_controls(self):
        self.assertEqual(run_ui_smoke_test(), 0)

    def test_ui_smoke_test_skips_known_tk_runtime_mismatch(self):
        with patch(
            "labelme_json_converter.diagnostics.tk.Tk",
            side_effect=RuntimeError("tk.h version (8.5) doesn't match libtk.a version (8.6)"),
        ):
            self.assertEqual(run_ui_smoke_test(), 0)


if __name__ == "__main__":
    unittest.main()
