import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import common


class _Proc:
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_call_codex_retries_transient_cli_failure_and_returns_output(tmp_path, monkeypatch):
    output_files = []
    attempts = []

    class FakeTemp:
        def __init__(self, delete=False, suffix=''):
            self.name = str(tmp_path / f'codex-output-{len(output_files)}.txt')
            output_files.append(Path(self.name))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_run(cmd, input, text, capture_output, timeout, cwd):
        attempts.append(cmd)
        if len(attempts) == 1:
            return _Proc(returncode=1, stderr='stream interrupted')
        Path(cmd[cmd.index('-o') + 1]).write_text('{"ok": true}', encoding='utf-8')
        return _Proc(returncode=0)

    monkeypatch.setenv('PIPELINE_CODEX_MAX_ATTEMPTS', '3')
    monkeypatch.setenv('PIPELINE_LLM_RETRY_BASE_DELAY', '0')
    monkeypatch.setattr(common.tempfile, 'NamedTemporaryFile', FakeTemp)
    monkeypatch.setattr(common.subprocess, 'run', fake_run)
    monkeypatch.setattr(common.time, 'sleep', lambda delay: None)

    result = common._call_codex('system', 'user', timeout=10)

    assert result == '{"ok": true}'
    assert len(attempts) == 2


def test_call_codex_does_not_retry_auth_configuration_errors(tmp_path, monkeypatch):
    attempts = []

    class FakeTemp:
        name = str(tmp_path / 'codex-output.txt')

        def __init__(self, delete=False, suffix=''):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_run(*args, **kwargs):
        attempts.append(1)
        return _Proc(returncode=1, stderr='401 Unauthorized: Missing bearer or basic authentication')

    monkeypatch.setenv('PIPELINE_CODEX_MAX_ATTEMPTS', '5')
    monkeypatch.setenv('PIPELINE_LLM_RETRY_BASE_DELAY', '0')
    monkeypatch.setattr(common.tempfile, 'NamedTemporaryFile', FakeTemp)
    monkeypatch.setattr(common.subprocess, 'run', fake_run)
    monkeypatch.setattr(common.time, 'sleep', lambda delay: None)

    try:
        common._call_codex('system', 'user', timeout=10)
    except RuntimeError as exc:
        assert 'Missing bearer' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')

    assert len(attempts) == 1


def test_call_codex_retries_timeout(tmp_path, monkeypatch):
    attempts = []

    class FakeTemp:
        def __init__(self, delete=False, suffix=''):
            self.name = str(tmp_path / f'codex-output-{len(attempts)}.txt')

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_run(cmd, *args, **kwargs):
        attempts.append(cmd)
        if len(attempts) == 1:
            raise subprocess.TimeoutExpired(cmd, timeout=kwargs.get('timeout', 10))
        Path(cmd[cmd.index('-o') + 1]).write_text('{"ok": true}', encoding='utf-8')
        return _Proc(returncode=0)

    monkeypatch.setenv('PIPELINE_CODEX_MAX_ATTEMPTS', '2')
    monkeypatch.setenv('PIPELINE_LLM_RETRY_BASE_DELAY', '0')
    monkeypatch.setattr(common.tempfile, 'NamedTemporaryFile', FakeTemp)
    monkeypatch.setattr(common.subprocess, 'run', fake_run)
    monkeypatch.setattr(common.time, 'sleep', lambda delay: None)

    assert common._call_codex('system', 'user', timeout=10) == '{"ok": true}'
    assert len(attempts) == 2


def test_call_hermes_cli_uses_profile_and_strips_session_id(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return _Proc(returncode=0, stdout='\nsession_id: 20260528_000000_abcd\n{"ok": true}\n')

    monkeypatch.setattr(common, 'HERMES_PROFILE', 'cut-news-pipeline')
    monkeypatch.setattr(common.subprocess, 'run', fake_run)

    result = common._call_hermes_cli('system', 'user', timeout=10)

    assert result == '{"ok": true}'
    cmd, kwargs = calls[0]
    assert cmd[:3] == ['hermes', '--profile', 'cut-news-pipeline']
    assert cmd[3:6] == ['chat', '-Q', '-q']
    assert kwargs['timeout'] == 10


def test_call_hermes_cli_adds_optional_model_and_provider(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Proc(returncode=0, stdout='{"ok": true}\n')

    monkeypatch.setattr(common, 'HERMES_PROFILE', 'cut-news-pipeline')
    monkeypatch.setattr(common, 'HERMES_MODEL', 'openai/gpt-5.5')
    monkeypatch.setattr(common, 'HERMES_PROVIDER', 'openai-codex')
    monkeypatch.setattr(common.subprocess, 'run', fake_run)

    assert common._call_hermes_cli('system', 'user', timeout=10) == '{"ok": true}'
    cmd = calls[0]
    assert cmd[cmd.index('--model') + 1] == 'openai/gpt-5.5'
    assert cmd[cmd.index('--provider') + 1] == 'openai-codex'


def test_call_hermes_cli_fails_on_empty_clean_output(monkeypatch):
    def fake_run(*args, **kwargs):
        return _Proc(returncode=0, stdout='\nsession_id: only\n')

    monkeypatch.setattr(common.subprocess, 'run', fake_run)

    try:
        common._call_hermes_cli('system', 'user', timeout=10)
    except RuntimeError as exc:
        assert 'empty output' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')
