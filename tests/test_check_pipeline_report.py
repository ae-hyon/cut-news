from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-pipeline-report.py"


def load_check_pipeline_report() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pipeline_report", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CheckPipelineReportTests(unittest.TestCase):
    def test_successful_report_passes_with_usable_imports_and_snapshots(self) -> None:
        module = load_check_pipeline_report()
        failures, summary = module.evaluate_report(
            {
                "status": "success",
                "failed_step": None,
                "max_articles": None,
                "import_stats": {"inserted": 1, "updated": 0, "deleted": 0, "skipped": 0},
                "drop_reason_counts": {},
                "snapshot_generation": {"attempted_user_count": 1, "generated_count": 1, "failed_count": 0},
            },
            require_uncapped=True,
        )

        self.assertEqual(failures, [])
        self.assertEqual(summary["usable_imports"], 1)
        self.assertFalse(summary["has_drop_reasons"])

    def test_failed_step_zero_import_and_snapshot_failure_are_alerts(self) -> None:
        module = load_check_pipeline_report()
        failures, summary = module.evaluate_report(
            {
                "status": "failed",
                "failed_step": "import",
                "max_articles": 3,
                "import_stats": {"inserted": 0, "updated": 0, "deleted": 2, "skipped": 0},
                "drop_reason_counts": {"missing_summary": 2},
                "snapshot_generation": {"attempted_user_count": 1, "generated_count": 0, "failed_count": 1},
            },
            require_uncapped=True,
        )

        self.assertIn("status='failed'", failures)
        self.assertIn("failed_step='import'", failures)
        self.assertIn("zero_usable_imports", failures)
        self.assertIn("snapshot_generation.failed_count=1", failures)
        self.assertIn("max_articles=3", failures)
        self.assertTrue(summary["has_drop_reasons"])

    def test_bounded_diagnostic_can_pass_when_uncapped_not_required(self) -> None:
        module = load_check_pipeline_report()
        failures, _summary = module.evaluate_report(
            {
                "status": "success",
                "failed_step": None,
                "max_articles": 3,
                "import_stats": {"inserted": 0, "updated": 2, "deleted": 0, "skipped": 0},
                "drop_reason_counts": {},
                "snapshot_generation": {"failed_count": 0},
            },
            require_uncapped=False,
        )

        self.assertEqual(failures, [])
    def test_all_keyword_rule_classifications_emit_quality_warning_not_failure(self) -> None:
        module = load_check_pipeline_report()
        failures, summary = module.evaluate_report(
            {
                "status": "success",
                "failed_step": None,
                "max_articles": None,
                "import_stats": {"inserted": 2, "updated": 0, "deleted": 0, "skipped": 0},
                "drop_reason_counts": {},
                "classification_source_counts": {"keyword_rule": 2},
                "snapshot_generation": {"failed_count": 0},
            },
            require_uncapped=True,
        )

        self.assertEqual(failures, [])
        self.assertEqual(summary["quality_warnings"], ["all_classifications_from_keyword_rule"])


if __name__ == "__main__":
    unittest.main()
