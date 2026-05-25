from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "local-compose.py"


def load_local_compose() -> ModuleType:
    spec = importlib.util.spec_from_file_location("local_compose", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LocalComposeTests(unittest.TestCase):
    def test_read_env_file_parses_simple_dotenv(self) -> None:
        module = load_local_compose()
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "# ignored",
                        "NEWS_SOURCE=naver-search",
                        "NAVER_CLIENT_ID='client-id'",
                        'NAVER_CLIENT_SECRET="client-secret"',
                        "MALFORMED_LINE",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                module.read_env_file(env_file),
                {
                    "NEWS_SOURCE": "naver-search",
                    "NAVER_CLIENT_ID": "client-id",
                    "NAVER_CLIENT_SECRET": "client-secret",
                },
            )

    def test_parse_args_allows_interleaved_log_options(self) -> None:
        module = load_local_compose()

        with patch.object(sys, "argv", ["local-compose.py", "logs", "--tail", "2", "backend", "-f"]):
            args = module.parse_args()

        self.assertEqual(args.command, "logs")
        self.assertEqual(args.services, ["backend"])
        self.assertEqual(args.lines, 2)
        self.assertTrue(args.follow)

    def test_selected_services_rejects_unknown_service(self) -> None:
        module = load_local_compose()
        all_services = module.services({})

        with patch.object(sys, "argv", ["local-compose.py", "ps", "backend", "unknown"]):
            args = module.parse_args()

        with self.assertRaisesRegex(SystemExit, "unknown service"):
            module.selected_services(args, all_services)


if __name__ == "__main__":
    unittest.main()
