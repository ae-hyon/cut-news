"""공통 유틸리티: LLM 호출, 파일 I/O"""

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import requests

# Default backend: Hermit gateway (OpenAI-compatible API)
HERMIT_URL = os.getenv("PIPELINE_LLM_URL", "http://localhost:8765/v1/chat/completions")
HERMIT_MODEL = os.getenv("PIPELINE_MODEL", "glm-5.1")
LLM_BACKEND = os.getenv("PIPELINE_LLM_BACKEND", "hermit_http")  # hermit_http | codex_exec | hermes_cli
CODEX_REASONING_EFFORT = os.getenv("PIPELINE_CODEX_REASONING_EFFORT", "low")
HERMES_PROFILE = os.getenv("PIPELINE_HERMES_PROFILE", "cut-news-pipeline")
HERMIT_API_KEY = None  # 최초 호출 시 ~/.hermit/settings.json에서 로드

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
JSON_DIR = DATA_DIR / "json"
SCORED_DIR = DATA_DIR / "scored"
SUMMARIZED_DIR = DATA_DIR / "summarized"
VERIFIED_DIR = DATA_DIR / "verified"

MAX_RETRIES = 5
RETRY_BASE_DELAY = 10  # 초
CODEX_MAX_ATTEMPTS = 5


_NON_RETRYABLE_CODEX_MARKERS = (
    "401 Unauthorized",
    "Missing bearer or basic authentication",
    "refresh_token_reused",
    "token_expired",
    "not logged in",
    "login required",
    "No such file or directory: 'codex'",
    "command not found: codex",
)


def _get_api_key() -> str:
    global HERMIT_API_KEY
    if HERMIT_API_KEY is None:
        settings_path = Path.home() / ".hermit" / "settings.json"
        with open(settings_path, encoding="utf-8") as f:
            HERMIT_API_KEY = json.load(f).get("gateway_api_key", "")
    return HERMIT_API_KEY


def _retry_base_delay() -> float:
    return float(os.getenv("PIPELINE_LLM_RETRY_BASE_DELAY", str(RETRY_BASE_DELAY)))


def _codex_max_attempts() -> int:
    return max(1, int(os.getenv("PIPELINE_CODEX_MAX_ATTEMPTS", str(CODEX_MAX_ATTEMPTS))))


def _is_non_retryable_codex_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker.lower() in lowered for marker in _NON_RETRYABLE_CODEX_MARKERS)


def _codex_retry_delay(attempt: int) -> float:
    return _retry_base_delay() * (2 ** attempt)


def _call_codex_once(system: str, user: str, timeout: int) -> str:
    prompt = (
        "다음 system 지시와 user 입력을 따르세요.\n"
        "최종 답변만 출력하고, 설명/머리말/코드펜스는 붙이지 마세요.\n\n"
        f"[system]\n{system}\n\n"
        f"[user]\n{user}\n"
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        output_path = tmp.name

    cmd = [
        "codex", "exec",
        "--skip-git-repo-check",
        "--sandbox", "workspace-write",
        "--ignore-rules",
        "--ignore-user-config",
        "--ephemeral",
        "--model", HERMIT_MODEL,
        "-c", f'model_reasoning_effort="{CODEX_REASONING_EFFORT}"',
        "-o", output_path,
        "-",
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout,
            cwd=str(Path(__file__).parent.parent),
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            raise RuntimeError(stderr or stdout or f"codex exec failed: {proc.returncode}")
        output = Path(output_path).read_text(encoding="utf-8").strip()
        if not output:
            raise RuntimeError("codex exec produced empty output")
        return output
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def _call_codex(system: str, user: str, timeout: int) -> str:
    max_attempts = _codex_max_attempts()
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return _call_codex_once(system, user, timeout)
        except subprocess.TimeoutExpired as e:
            last_error = e
            message = f"codex exec timed out after {timeout}s"
        except RuntimeError as e:
            last_error = e
            message = str(e)
            if _is_non_retryable_codex_error(message):
                raise

        if attempt == max_attempts - 1:
            break

        delay = _codex_retry_delay(attempt)
        print(f"\n    ⚠️ Codex Error — {message} — {delay:g}초 대기 후 재시도 ({attempt + 1}/{max_attempts})")
        if delay > 0:
            time.sleep(delay)

    raise RuntimeError(f"codex exec {max_attempts}회 재시도 실패: {last_error}")


def _clean_hermes_stdout(stdout: str) -> str:
    lines = [line for line in stdout.splitlines() if line.strip()]
    content_lines = [line for line in lines if not line.strip().startswith("session_id:")]
    return "\n".join(content_lines).strip()


def _call_hermes_cli(system: str, user: str, timeout: int) -> str:
    prompt = (
        "다음 system 지시와 user 입력을 따르세요.\n"
        "최종 답변만 출력하고, 설명/머리말/코드펜스는 붙이지 마세요.\n\n"
        f"[system]\n{system}\n\n"
        f"[user]\n{user}\n"
    )
    cmd = [
        "hermes",
        "--profile",
        HERMES_PROFILE,
        "chat",
        "-Q",
        "-q",
        prompt,
        "--toolsets",
        "",
    ]
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=timeout,
        cwd=str(Path(__file__).parent.parent),
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise RuntimeError(stderr or stdout or f"hermes cli failed: {proc.returncode}")
    output = _clean_hermes_stdout(proc.stdout or "")
    if not output:
        raise RuntimeError("hermes cli produced empty output")
    return output


def call_llm(system: str, user: str, temperature: float = 0.3, timeout: int = 300) -> str:
    """LLM 호출. backend 설정에 따라 Hermit HTTP, Codex CLI, Hermes CLI 중 하나를 실행."""
    if LLM_BACKEND == "codex_exec":
        return _call_codex(system, user, timeout)
    if LLM_BACKEND == "hermes_cli":
        return _call_hermes_cli(system, user, timeout)

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                HERMIT_URL,
                headers={"Authorization": f"Bearer {_get_api_key()}"},
                json={
                    "model": HERMIT_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "stream": False,
                },
                timeout=timeout,
            )

            if resp.status_code == 429:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"\n    ⚠️ 429 Rate Limited — {delay}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(delay)
                continue

            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict) and data.get("error"):
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                message = data.get("error", {}).get("message", "unknown gateway error")
                print(f"\n    ⚠️ Gateway Error — {message} — {delay}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(delay)
                continue

            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                raise RuntimeError(f"LLM 응답에 choices 없음: {data}")

            return choices[0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"\n    ⚠️ Timeout — {delay}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
            time.sleep(delay)
            continue

        except requests.exceptions.ConnectionError:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"\n    ⚠️ Connection Error — {delay}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
            time.sleep(delay)
            continue

        except RuntimeError as e:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"\n    ⚠️ Runtime Error — {e} — {delay}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
            time.sleep(delay)
            continue

    raise RuntimeError(f"LLM 호출 {MAX_RETRIES}회 재시도 실패")


def parse_json_response(raw: str) -> dict:
    """LLM 응답에서 JSON 추출 및 파싱"""
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:]
            part = part.strip()
            if part.startswith("{"):
                raw = part
                break

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fixed = re.sub(
            r'(?<=": ")(.*?)(?="(?:,|\n|\s*\}))',
            lambda m: m.group(0).replace('\n', '\\n').replace('\r', ''),
            raw,
            flags=re.DOTALL,
        )
        return json.loads(fixed)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
