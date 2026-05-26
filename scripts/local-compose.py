#!/usr/bin/env python3
"""Small Docker Compose-like runner for local Cut News development.

This keeps AI execution on the host so Codex/Hermes OAuth-based tooling can be used
without trying to pass credentials into a Linux container.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".local" / "compose"
LOG_DIR = STATE_DIR / "logs"
PID_DIR = STATE_DIR / "pids"
ROOT_ENV = ROOT / ".env"
BACKEND_ENV = ROOT / "apps" / "backend" / ".env"


@dataclass(frozen=True)
class Service:
    name: str
    cwd: Path
    command: list[str]
    env: dict[str, str]
    health_url: str | None = None


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def base_env() -> dict[str, str]:
    # Precedence: explicit shell/Make environment > root .env > backend .env > defaults.
    # This keeps root .env useful for local credentials while allowing one-off smoke
    # commands like `NEWS_SOURCE=naver-all-categories make local-pipeline`.
    env = read_env_file(BACKEND_ENV)
    env.update(read_env_file(ROOT_ENV))
    env.update(os.environ)
    env.setdefault("NEWS_SOURCE", "seeded")
    env.setdefault("NEWS_QUERY", "경제")
    env.setdefault("NEWS_COUNT", "20")
    env.setdefault("PIPELINE_LLM_BACKEND", "codex_exec")
    env.setdefault("PIPELINE_MODEL", "gpt-5.4-mini")
    env.setdefault("PIPELINE_CODEX_REASONING_EFFORT", "low")
    env.setdefault("DATABASE_URL", "sqlite+pysqlite:///dev-ui-test.db")
    env.setdefault("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000")
    env.setdefault("AI_NEWS_GENERATION_TIME", "08:30:00")
    env.setdefault("NEWS_SCHEDULE_TIMEZONE", "Asia/Seoul")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def services(env: dict[str, str]) -> dict[str, Service]:
    backend_env = {**env, "PYTHONPATH": "."}
    crawler_env = {**env, "PYTHONPATH": "src"}
    return {
        "backend": Service(
            name="backend",
            cwd=ROOT / "apps" / "backend",
            command=["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
            env=backend_env,
            health_url="http://127.0.0.1:8000/health",
        ),
        "crawler": Service(
            name="crawler",
            cwd=ROOT / "apps" / "crawler",
            command=["uv", "run", "uvicorn", "crawler.main:app", "--reload", "--host", "127.0.0.1", "--port", "8001"],
            env=crawler_env,
            health_url="http://127.0.0.1:8001/health",
        ),
        "frontend": Service(
            name="frontend",
            cwd=ROOT / "apps" / "frontend",
            command=["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3000"],
            env=env,
            health_url="http://127.0.0.1:3000",
        ),
        "scheduler": Service(
            name="scheduler",
            cwd=ROOT,
            command=[sys.executable, str(Path(__file__).resolve()), "scheduler-run"],
            env=env,
            health_url=None,
        ),
    }


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)


def pid_path(name: str) -> Path:
    return PID_DIR / f"{name}.pid"


def log_path(name: str) -> Path:
    return LOG_DIR / f"{name}.log"


def read_pid(name: str) -> int | None:
    path = pid_path(name)
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def is_running(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_health(url: str, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


def start_service(service: Service) -> None:
    ensure_dirs()
    existing = read_pid(service.name)
    if is_running(existing):
        print(f"{service.name}: already running pid={existing}")
        return
    with log_path(service.name).open("ab") as log_file:
        log_file.write(f"\n--- start {datetime.now().isoformat(timespec='seconds')} ---\n".encode())
        process = subprocess.Popen(
            service.command,
            cwd=service.cwd,
            env=service.env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_path(service.name).write_text(str(process.pid), encoding="utf-8")
    print(f"{service.name}: started pid={process.pid} log={log_path(service.name)}")
    if service.health_url:
        ok = wait_health(service.health_url)
        print(f"{service.name}: health {'ok' if ok else 'not ready'} {service.health_url}")


def stop_service(name: str) -> None:
    pid = read_pid(name)
    if not is_running(pid):
        pid_path(name).unlink(missing_ok=True)
        print(f"{name}: stopped")
        return
    assert pid is not None
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.time() + 10
    while time.time() < deadline and is_running(pid):
        time.sleep(0.2)
    if is_running(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    pid_path(name).unlink(missing_ok=True)
    print(f"{name}: stopped")


def status_service(service: Service) -> None:
    pid = read_pid(service.name)
    running = is_running(pid)
    health = "n/a"
    if running and service.health_url:
        health = "ok" if wait_health(service.health_url, timeout_seconds=2) else "not-ready"
    print(f"{service.name:10} {'running' if running else 'stopped':8} pid={pid or '-'} health={health} log={log_path(service.name)}")


def run_pipeline_once(env: dict[str, str]) -> int:
    command = ["uv", "run", "python", "-m", "app.scripts.run_news_pipeline_job"]
    run_env = {**env, "PYTHONPATH": "."}
    print(
        "pipeline: "
        f"source={run_env.get('NEWS_SOURCE')} query={run_env.get('NEWS_QUERY')} "
        f"count={run_env.get('NEWS_COUNT')} backend={run_env.get('PIPELINE_LLM_BACKEND')}"
    )
    completed = subprocess.run(command, cwd=ROOT / "apps" / "backend", env=run_env)
    return completed.returncode


def next_run_time(env: dict[str, str]) -> datetime:
    timezone = ZoneInfo(env.get("NEWS_SCHEDULE_TIMEZONE", "Asia/Seoul"))
    target = env.get("AI_NEWS_GENERATION_TIME", "08:30:00")
    hour, minute, second = [int(part) for part in target.split(":")]
    now = datetime.now(timezone)
    scheduled = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if scheduled <= now:
        scheduled += timedelta(days=1)
    return scheduled


def scheduler_run() -> int:
    env = base_env()
    while True:
        scheduled = next_run_time(env)
        now = datetime.now(scheduled.tzinfo)
        sleep_seconds = max(1, int((scheduled - now).total_seconds()))
        print(
            f"[{now.isoformat(timespec='seconds')}] next AI news pipeline at "
            f"{scheduled.isoformat(timespec='seconds')} in {sleep_seconds}s",
            flush=True,
        )
        time.sleep(sleep_seconds)
        print(f"[{datetime.now(scheduled.tzinfo).isoformat(timespec='seconds')}] starting AI news pipeline", flush=True)
        code = run_pipeline_once(env)
        print(f"[{datetime.now(scheduled.tzinfo).isoformat(timespec='seconds')}] finished AI news pipeline code={code}", flush=True)


def tail_logs(names: Sequence[str], lines: int, follow: bool = False) -> None:
    if follow:
        ensure_dirs()
        paths = [log_path(name) for name in names]
        for path in paths:
            path.touch(exist_ok=True)
        try:
            subprocess.run(["tail", "-n", str(lines), "-f", *[str(path) for path in paths]], check=False)
        except KeyboardInterrupt:
            pass
        return

    for name in names:
        path = log_path(name)
        print(f"\n==> {path} <==")
        if not path.exists():
            print("(missing)")
            continue
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in content[-lines:]:
            print(line)


def print_run_report() -> None:
    path = ROOT / "apps" / "summarizer" / "data" / "run_report.json"
    if not path.exists():
        print(f"missing: {path}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps({
        "status": data.get("status"),
        "failed_step": data.get("failed_step"),
        "source": data.get("source"),
        "query": data.get("query"),
        "count": data.get("count"),
        "feed_date": data.get("feed_date"),
        "import_stats": data.get("import_stats"),
        "drop_reason_counts": data.get("drop_reason_counts"),
        "snapshot_generation": data.get("snapshot_generation"),
    }, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dockerless compose-like runner for Cut News")
    parser.add_argument(
        "command",
        choices=["up", "start", "down", "stop", "restart", "status", "ps", "logs", "pipeline", "report", "scheduler-run"],
    )
    parser.add_argument("services", nargs="*", help="backend crawler frontend scheduler; default: all for up/status/down/logs")
    parser.add_argument("-d", "--detach", action="store_true", help="accepted for docker compose muscle memory; up is always detached")
    parser.add_argument("-f", "--follow", action="store_true", help="follow logs")
    parser.add_argument("--tail", "--lines", dest="lines", type=int, default=80, help="lines per service for logs")
    return parser.parse_intermixed_args()


def selected_services(args: argparse.Namespace, all_services: dict[str, Service]) -> list[str]:
    names = args.services or ["backend", "crawler", "frontend", "scheduler"]
    unknown = [name for name in names if name not in all_services]
    if unknown:
        raise SystemExit(f"unknown service(s): {', '.join(unknown)}")
    return names


def main() -> int:
    args = parse_args()
    if args.command == "scheduler-run":
        return scheduler_run()

    env = base_env()
    all_services = services(env)
    names = selected_services(args, all_services)

    if args.command in {"up", "start"}:
        for name in names:
            start_service(all_services[name])
        return 0
    if args.command in {"down", "stop"}:
        for name in reversed(names):
            stop_service(name)
        return 0
    if args.command == "restart":
        for name in reversed(names):
            stop_service(name)
        for name in names:
            start_service(all_services[name])
        return 0
    if args.command in {"status", "ps"}:
        for name in names:
            status_service(all_services[name])
        return 0
    if args.command == "logs":
        tail_logs(names, args.lines, follow=args.follow)
        return 0
    if args.command == "pipeline":
        return run_pipeline_once(env)
    if args.command == "report":
        print_run_report()
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
