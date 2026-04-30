"""Cycle 10 PR1 (Phase 4 coverage).

Phủ hai module hook để Phase 4 coverage:

* ``scripts/vibecodekit/hook_interceptor.py`` (was 33%, target ≥80%):
  - ``_filter_env`` — drop secret-like env keys, bypass khi
    ``VIBECODE_HOOK_ALLOW_SECRETS=1``.
  - ``_scrub_str`` / ``_scrub_payload`` — redact AWS / sk- / ghp_ /
    high-entropy hex; recursive scrub nested dict/list/str.
  - ``_hook_cmd`` — chọn ``python3`` cho ``.py`` / ``bash`` cho ``.sh``.
  - ``run_hooks`` — happy path JSON decision parse, non-existent
    hooks dir, missing event hook, exit code mapping, chmod fallback,
    timeout, structured stdout truncate.
  - ``is_blocked`` — deny / non-zero rc / allow override / empty list.

* ``scripts/vibecodekit/auto_commit_hook.py`` (was 40%, target ≥80%):
  - ``is_sensitive`` — 5+ pattern (env, key, pem, aws creds, ssh
    key) + whitelist (.env.example).
  - ``SensitiveFileGuard.check`` — sensitive path raise, token-in-
    content raise, safe path+content pass.
  - ``_opt_out`` — VIBECODE_NO_AUTOCOMMIT=1 / VIBECODE_AUTOCOMMIT=0.
  - ``_is_git_repo`` / ``_git_status_files`` — real subprocess trên
    tmp_path với ``git init``.
  - ``AutoCommitHook.decide`` — opt-out / not git / nothing /
    sensitive / debounced / ready.
  - ``AutoCommitHook.commit`` — refuse propagate / commit success
    + bump stamp / git error fallback.

Toàn bộ test KHÔNG cần network / không touch real ``$HOME`` / chỉ dùng
``tmp_path``, ``monkeypatch``, ``subprocess`` (cho git).
"""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Any

import pytest

from vibecodekit import auto_commit_hook as ach_mod
from vibecodekit import hook_interceptor as hi_mod


# ---------------------------------------------------------------------------
# hook_interceptor — _filter_env
# ---------------------------------------------------------------------------

def test_filter_env_drops_secret_like_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECODE_HOOK_ALLOW_SECRETS", raising=False)
    env = {
        "PATH": "/usr/bin",
        "GITHUB_TOKEN": "ghp_x",
        "AWS_SECRET_ACCESS_KEY": "abc",
        "MY_PASSWORD": "p",
        "MY_API_KEY": "k",
        "HOME": "/h",
        "PRIVATE_THING": "x",
        "MY_CREDENTIAL": "z",
    }
    out = hi_mod._filter_env(env)
    assert "PATH" in out and "HOME" in out
    assert "GITHUB_TOKEN" not in out
    assert "AWS_SECRET_ACCESS_KEY" not in out
    assert "MY_PASSWORD" not in out
    assert "MY_API_KEY" not in out
    assert "PRIVATE_THING" not in out
    assert "MY_CREDENTIAL" not in out


def test_filter_env_bypass_when_allow_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBECODE_HOOK_ALLOW_SECRETS", "1")
    env = {"GITHUB_TOKEN": "ghp_x", "PATH": "/usr/bin"}
    out = hi_mod._filter_env(env)
    assert out == env


# ---------------------------------------------------------------------------
# hook_interceptor — _scrub_str / _scrub_payload
# ---------------------------------------------------------------------------

def test_scrub_str_redacts_aws_access_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECODE_HOOK_ALLOW_SECRETS", raising=False)
    text = "AKIAIOSFODNN7EXAMPLE is the key"
    out = hi_mod._scrub_str(text)
    assert "AKIA" not in out
    assert "***REDACTED***" in out


def test_scrub_str_redacts_openai_and_github_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECODE_HOOK_ALLOW_SECRETS", raising=False)
    text = "openai sk-abcdefghijklmnopqrstuvwxyz1234567890 and ghp_" + "a" * 36
    out = hi_mod._scrub_str(text)
    assert "sk-" not in out
    assert "ghp_" not in out


def test_scrub_str_redacts_authorization_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECODE_HOOK_ALLOW_SECRETS", raising=False)
    text = "curl -H 'Authorization: Bearer eyJabcDEFghi'"
    out = hi_mod._scrub_str(text)
    assert "eyJabcDEFghi" not in out
    assert "Authorization: Bearer ***REDACTED***" in out


def test_scrub_str_bypass_when_allow_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBECODE_HOOK_ALLOW_SECRETS", "1")
    text = "AKIAIOSFODNN7EXAMPLE"
    assert hi_mod._scrub_str(text) == text


def test_scrub_payload_recursive_dict_list_str(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECODE_HOOK_ALLOW_SECRETS", raising=False)
    payload: dict[str, Any] = {
        "command": "echo AKIAIOSFODNN7EXAMPLE",
        "GITHUB_TOKEN": "ghp_xyz",  # key matches secret RX → redact whole value
        "headers": [
            {"value": "curl -H 'Authorization: Bearer abc.def.ghi'"},
            {"safe": "value"},
        ],
        "count": 42,
    }
    out = hi_mod._scrub_payload(payload)
    assert "AKIA" not in out["command"]
    assert out["GITHUB_TOKEN"] == "***REDACTED***"
    # Non-string scalars passed through.
    assert out["count"] == 42
    # Nested redaction applies inside lists.
    assert "abc.def.ghi" not in out["headers"][0]["value"]
    assert "***REDACTED***" in out["headers"][0]["value"]
    # safe value untouched.
    assert out["headers"][1]["safe"] == "value"


def test_scrub_payload_bypass_when_allow_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBECODE_HOOK_ALLOW_SECRETS", "1")
    obj = {"GITHUB_TOKEN": "ghp_x"}
    assert hi_mod._scrub_payload(obj) == obj


# ---------------------------------------------------------------------------
# hook_interceptor — _hook_cmd
# ---------------------------------------------------------------------------

def test_hook_cmd_python_for_py_suffix(tmp_path: Path) -> None:
    h = tmp_path / "x.py"
    h.touch()
    assert hi_mod._hook_cmd(h, "echo hi") == ["python3", str(h), "echo hi"]


def test_hook_cmd_bash_for_sh_suffix(tmp_path: Path) -> None:
    h = tmp_path / "x.sh"
    h.touch()
    assert hi_mod._hook_cmd(h, "echo hi") == ["bash", str(h), "echo hi"]


# ---------------------------------------------------------------------------
# hook_interceptor — run_hooks
# ---------------------------------------------------------------------------

def test_run_hooks_no_hooks_dir_returns_empty(tmp_path: Path) -> None:
    assert hi_mod.run_hooks(tmp_path, "pre_tool_use") == []


def test_run_hooks_missing_event_returns_empty(tmp_path: Path) -> None:
    (tmp_path / ".claw" / "hooks").mkdir(parents=True)
    assert hi_mod.run_hooks(tmp_path, "pre_tool_use") == []


def test_run_hooks_executes_sh_and_parses_decision(tmp_path: Path) -> None:
    hooks = tmp_path / ".claw" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "pre_tool_use.sh"
    hook.write_text(
        textwrap.dedent("""
            #!/usr/bin/env bash
            echo '{"decision":"allow","note":"ok"}'
        """).lstrip(),
        encoding="utf-8",
    )
    # Intentionally non-executable — run_hooks must chmod 0o755.
    hook.chmod(0o644)
    results = hi_mod.run_hooks(tmp_path, "pre_tool_use", payload={"command": "ls"})
    assert len(results) == 1
    assert results[0]["decision"] == "allow"
    assert results[0]["returncode"] == 0
    assert results[0]["structured"] == {"decision": "allow", "note": "ok"}


def test_run_hooks_non_json_stdout_decision_none(tmp_path: Path) -> None:
    hooks = tmp_path / ".claw" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "post_tool_use.sh"
    hook.write_text("#!/usr/bin/env bash\necho 'plain text'\n",
                    encoding="utf-8")
    hook.chmod(0o755)
    results = hi_mod.run_hooks(tmp_path, "post_tool_use")
    assert results[0]["decision"] is None
    assert results[0]["structured"] is None


def test_run_hooks_invalid_json_object_swallowed(tmp_path: Path) -> None:
    hooks = tmp_path / ".claw" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "post_tool_use.sh"
    # Looks like JSON ({...}) but is malformed → JSONDecodeError swallowed.
    hook.write_text("#!/usr/bin/env bash\necho '{not json'\n", encoding="utf-8")
    hook.chmod(0o755)
    results = hi_mod.run_hooks(tmp_path, "post_tool_use")
    assert results[0]["decision"] is None
    assert results[0]["structured"] is None


def test_run_hooks_nonzero_returncode(tmp_path: Path) -> None:
    hooks = tmp_path / ".claw" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "pre_tool_use.sh"
    hook.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
    hook.chmod(0o755)
    results = hi_mod.run_hooks(tmp_path, "pre_tool_use")
    assert results[0]["returncode"] == 17


def test_run_hooks_timeout_records_124(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hooks = tmp_path / ".claw" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "pre_tool_use.sh"
    hook.write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")
    hook.chmod(0o755)

    def _boom(*a: Any, **kw: Any) -> None:
        raise subprocess.TimeoutExpired(cmd="x", timeout=1, output="o", stderr="e")

    monkeypatch.setattr(hi_mod.subprocess, "run", _boom)
    results = hi_mod.run_hooks(tmp_path, "pre_tool_use")
    assert results[0]["returncode"] == 124
    assert "timeout" in results[0]["error"]


def test_run_hooks_exposes_command_via_payload(tmp_path: Path) -> None:
    hooks = tmp_path / ".claw" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "pre_tool_use.sh"
    hook.write_text(
        '#!/usr/bin/env bash\nprintf "%s" "$VIBECODE_HOOK_COMMAND"\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    results = hi_mod.run_hooks(tmp_path, "pre_tool_use", payload={"command": "rm -rf /"})
    assert results[0]["stdout"].strip() == "rm -rf /"


# ---------------------------------------------------------------------------
# hook_interceptor — is_blocked
# ---------------------------------------------------------------------------

def test_is_blocked_empty_false() -> None:
    assert hi_mod.is_blocked([]) is False


def test_is_blocked_deny_decision_true() -> None:
    assert hi_mod.is_blocked([{"decision": "deny", "returncode": 0}]) is True


def test_is_blocked_nonzero_rc_true() -> None:
    assert hi_mod.is_blocked([{"decision": None, "returncode": 1}]) is True


def test_is_blocked_allow_overrides_nonzero_rc() -> None:
    # Even nonzero rc, allow decision unblocks.
    assert hi_mod.is_blocked([{"decision": "allow", "returncode": 1}]) is False


def test_is_blocked_zero_rc_no_decision_false() -> None:
    assert hi_mod.is_blocked([{"decision": None, "returncode": 0}]) is False


# ---------------------------------------------------------------------------
# auto_commit_hook — is_sensitive
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    ".env",
    ".env.local",
    "config/.env.production",
    "secret.key",
    "tls.pem",
    "id_rsa",
    "credentials.json",
    "service_account.json",
    "/home/u/.aws/credentials",
    ".kube/config",
    ".docker/config.json",
    ".npmrc",
    "stripe.secret.txt",
])
def test_is_sensitive_true(path: str) -> None:
    assert ach_mod.is_sensitive(path) is True


@pytest.mark.parametrize("path", [
    ".env.example",
    ".env.sample",
    ".env.template",
    "credentials.example",
    "service_account.example.json",
    "src/main.py",
    "README.md",
    "tests/test_x.py",
])
def test_is_sensitive_false(path: str) -> None:
    assert ach_mod.is_sensitive(path) is False


# ---------------------------------------------------------------------------
# auto_commit_hook — SensitiveFileGuard
# ---------------------------------------------------------------------------

def test_guard_raises_on_sensitive_path() -> None:
    g = ach_mod.SensitiveFileGuard()
    with pytest.raises(PermissionError, match="sensitive file refused"):
        g.check(".env", content="DB=foo")


def test_guard_raises_on_token_in_content() -> None:
    g = ach_mod.SensitiveFileGuard()
    with pytest.raises(PermissionError, match="high-entropy"):
        g.check("notes.md", content="api: AKIAIOSFODNN7EXAMPLE")


def test_guard_pass_safe_path_no_content() -> None:
    g = ach_mod.SensitiveFileGuard()
    g.check("README.md", content=None)  # noop


def test_guard_pass_safe_content() -> None:
    g = ach_mod.SensitiveFileGuard()
    g.check("README.md", content="hello world\nno secrets here\n")


def test_guard_detects_openai_token() -> None:
    g = ach_mod.SensitiveFileGuard()
    with pytest.raises(PermissionError):
        g.check(
            "notes.md",
            content="OPENAI_KEY=sk-1234567890abcdefghij1234567890",
        )


def test_guard_detects_private_key_block() -> None:
    g = ach_mod.SensitiveFileGuard()
    with pytest.raises(PermissionError):
        g.check(
            "key.txt",
            content="-----BEGIN RSA PRIVATE KEY-----\nfoo\n",
        )


# ---------------------------------------------------------------------------
# auto_commit_hook — _opt_out
# ---------------------------------------------------------------------------

def test_opt_out_via_no_autocommit_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBECODE_NO_AUTOCOMMIT", "1")
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    assert ach_mod._opt_out() is True


def test_opt_out_via_autocommit_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.setenv("VIBECODE_AUTOCOMMIT", "0")
    assert ach_mod._opt_out() is True


def test_opt_out_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    assert ach_mod._opt_out() is False


# ---------------------------------------------------------------------------
# auto_commit_hook — _is_git_repo / _git_status_files
# ---------------------------------------------------------------------------

def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"],
                   cwd=str(repo), check=True)


def test_is_git_repo_true(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert ach_mod._is_git_repo(tmp_path) is True


def test_is_git_repo_false(tmp_path: Path) -> None:
    assert ach_mod._is_git_repo(tmp_path) is False


def test_is_git_repo_handles_missing_git_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*a: Any, **kw: Any) -> None:
        raise FileNotFoundError("git not installed")

    monkeypatch.setattr(ach_mod.subprocess, "run", _boom)
    assert ach_mod._is_git_repo(tmp_path) is False


def test_git_status_files_lists_changed(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("ho\n", encoding="utf-8")
    files = ach_mod._git_status_files(tmp_path)
    assert sorted(files) == ["a.txt", "b.txt"]


def test_git_status_files_empty_clean_tree(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert ach_mod._git_status_files(tmp_path) == []


# ---------------------------------------------------------------------------
# auto_commit_hook — AutoCommitHook.decide
# ---------------------------------------------------------------------------

def test_decide_opt_out(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBECODE_NO_AUTOCOMMIT", "1")
    h = ach_mod.AutoCommitHook()
    d = h.decide(tmp_path, now=1000.0)
    assert d.commit is False
    assert "opt-out" in d.reason


def test_decide_not_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    h = ach_mod.AutoCommitHook()
    d = h.decide(tmp_path, now=1000.0)
    assert d.commit is False
    assert "not a git repo" in d.reason


def test_decide_nothing_to_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    _git_init(tmp_path)
    h = ach_mod.AutoCommitHook()
    d = h.decide(tmp_path, now=1000.0)
    assert d.commit is False
    assert "nothing to commit" in d.reason


def test_decide_refuse_sensitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    _git_init(tmp_path)
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (tmp_path / "ok.txt").write_text("safe\n", encoding="utf-8")
    h = ach_mod.AutoCommitHook()
    d = h.decide(tmp_path, now=1000.0)
    assert d.commit is False
    assert "sensitive" in d.reason
    assert ".env" in d.files


def test_decide_debounced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    _git_init(tmp_path)
    (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
    stamp = tmp_path / ".git" / ".vibecode-last-autocommit"
    stamp.write_text("1000.0\n", encoding="utf-8")
    h = ach_mod.AutoCommitHook(debounce_s=60.0)
    d = h.decide(tmp_path, now=1010.0)
    assert d.commit is False
    assert "debounced" in d.reason
    assert d.debounced_remaining_s > 0


def test_decide_debounce_malformed_stamp_treated_as_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stamp file không phải số → fallback last=0 → coi như đủ thời gian."""
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    _git_init(tmp_path)
    (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
    stamp = tmp_path / ".git" / ".vibecode-last-autocommit"
    stamp.write_text("not-a-float\n", encoding="utf-8")
    h = ach_mod.AutoCommitHook(debounce_s=60.0)
    d = h.decide(tmp_path, now=1000.0)
    # malformed → last=0 → elapsed = 1000 > 60 → ready.
    assert d.commit is True


def test_decide_ready_no_stamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    _git_init(tmp_path)
    (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
    h = ach_mod.AutoCommitHook()
    d = h.decide(tmp_path, now=1000.0)
    assert d.commit is True
    assert "a.txt" in d.files


# ---------------------------------------------------------------------------
# auto_commit_hook — AutoCommitHook.commit
# ---------------------------------------------------------------------------

def test_commit_propagates_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBECODE_NO_AUTOCOMMIT", "1")
    h = ach_mod.AutoCommitHook()
    d = h.commit(tmp_path, message="x", now=1000.0)
    assert d.commit is False


def test_commit_success_creates_stamp_and_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    _git_init(tmp_path)
    (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
    h = ach_mod.AutoCommitHook(debounce_s=0.0)
    d = h.commit(tmp_path, message="checkpoint test", now=2000.0)
    assert d.commit is True
    # Verify git log
    log = subprocess.run(["git", "log", "--oneline"], cwd=str(tmp_path),
                         capture_output=True, text=True, check=True)
    assert "[vibecode-auto] checkpoint test" in log.stdout
    # Stamp file written
    stamp = tmp_path / ".git" / ".vibecode-last-autocommit"
    assert stamp.is_file()
    assert float(stamp.read_text(encoding="utf-8").strip()) == pytest.approx(2000.0)


def test_commit_handles_git_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``git commit`` raise CalledProcessError → Decision(False, reason)."""
    monkeypatch.delenv("VIBECODE_NO_AUTOCOMMIT", raising=False)
    monkeypatch.delenv("VIBECODE_AUTOCOMMIT", raising=False)
    _git_init(tmp_path)
    (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")

    real_run = ach_mod.subprocess.run
    calls: list[list[str]] = []

    def _flaky(cmd: Any, *a: Any, **kw: Any) -> Any:
        calls.append(list(cmd))
        # Allow status / rev-parse / add through.
        if isinstance(cmd, list) and "commit" in cmd:
            raise subprocess.CalledProcessError(
                returncode=1, cmd=cmd, output=b"", stderr=b"refusing"
            )
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(ach_mod.subprocess, "run", _flaky)
    h = ach_mod.AutoCommitHook(debounce_s=0.0)
    d = h.commit(tmp_path, message="x", now=3000.0)
    assert d.commit is False
    assert "git commit failed" in d.reason
    # Stamp NOT written on failure.
    stamp = tmp_path / ".git" / ".vibecode-last-autocommit"
    assert not stamp.is_file()
