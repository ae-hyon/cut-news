from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-scheduled-artifact-pipeline.py"


def load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_scheduled_artifact_pipeline", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def args(**overrides: object) -> argparse.Namespace:
    defaults = {
        "home": "/Users/reddit",
        "database_url": None,
        "load_dotenv": False,
        "dotenv_path": ROOT / ".env",
        "max_articles": None,
        "report": ROOT / "apps" / "summarizer" / "data" / "run_report.json",
        "dry_run": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class ScheduledArtifactPipelineTests(unittest.TestCase):
    def test_build_runtime_env_requires_database_url(self) -> None:
        module = load_runner()

        with self.assertRaisesRegex(SystemExit, "DATABASE_URL is required"):
            module.build_runtime_env(args(), base={})

    def test_build_runtime_env_sets_home_and_uncapped_default(self) -> None:
        module = load_runner()

        env = module.build_runtime_env(args(database_url="postgresql://example/db"), base={"HOME": "/tmp/wrong"})

        self.assertEqual(env["HOME"], "/Users/reddit")
        self.assertEqual(env["DATABASE_URL"], "postgresql://example/db")
        self.assertEqual(env["NEWS_PIPELINE_MAX_ARTICLES"], "")
        self.assertEqual(env["PIPELINE_LLM_BACKEND"], "codex_exec")

    def test_build_runtime_env_can_load_database_url_from_dotenv_without_overriding_env(self) -> None:
        module = load_runner()
        with tempfile.TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text("DATABASE_URL=postgresql://dotenv/db\nPIPELINE_MODEL=from-dotenv\n", encoding="utf-8")

            env = module.build_runtime_env(
                args(load_dotenv=True, dotenv_path=dotenv),
                base={"DATABASE_URL": "postgresql://env/db", "PIPELINE_MODEL": "from-env"},
            )

        self.assertEqual(env["DATABASE_URL"], "postgresql://env/db")
        self.assertEqual(env["PIPELINE_MODEL"], "from-env")

    def test_dry_run_returns_resolved_plan(self) -> None:
        module = load_runner()

        code, summary = module.run_scheduled_pipeline(
            args(database_url="postgresql://ep-test.neon.tech/neondb?sslmode=require", dry_run=True)
        )

        self.assertEqual(code, 0)
        self.assertEqual(summary["status"], "dry_run")
        self.assertEqual(summary["database_target"], "neon")
        self.assertIn("make local-pipeline-from-github", summary["commands"])

    def test_failed_command_triggers_alert(self) -> None:
        module = load_runner()
        fake_results = [
            module.CommandResult("local-pipeline-from-github", ["make"], 0, "pipeline ok", ""),
            module.CommandResult("local-report-check", ["make"], 1, "bad report", ""),
        ]

        def fake_run_command(name: str, command: list[str], env: dict[str, str]):
            return fake_results.pop(0)

        with patch.object(module, "run_command", side_effect=fake_run_command), patch.object(
            module, "load_report", return_value={"status": "failed", "failed_step": "import"}
        ), patch.object(module, "send_alert") as send_alert:
            code, summary = module.run_scheduled_pipeline(args(database_url="postgresql://example/db"))

        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "failed")
        send_alert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
