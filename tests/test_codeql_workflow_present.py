"""Cycle 8 PR3 — CodeQL SAST workflow guard.

Đảm bảo ``.github/workflows/codeql.yml`` tồn tại + structure hợp lệ:

* Action versions: ``init@v3`` + ``analyze@v3``.
* Trigger: pull_request + schedule (weekly cron).
* Matrix language ``python``.
* Query set: ``security-extended`` (rộng hơn default).

CodeQL pair với ``pip-audit`` (SCA, security.yml) + ``actionlint``
(workflow lint, actionlint.yml) cho 3-layer security CI.
"""
from __future__ import annotations

import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CODEQL_YML = REPO_ROOT / ".github" / "workflows" / "codeql.yml"


def test_codeql_workflow_file_exists() -> None:
    """File ``.github/workflows/codeql.yml`` phải tồn tại + non-empty."""
    assert _CODEQL_YML.is_file(), (
        f"{_CODEQL_YML} không tồn tại — cycle 8 PR3 cần thêm CodeQL "
        "workflow trong .github/workflows/ để bật SAST scan."
    )
    assert _CODEQL_YML.stat().st_size > 0, "codeql.yml rỗng"


def test_codeql_workflow_uses_v3_actions() -> None:
    """Phải dùng ``codeql-action/init@v3`` + ``analyze@v3`` (KHÔNG @v2)."""
    text = _CODEQL_YML.read_text(encoding="utf-8")
    assert "github/codeql-action/init@v3" in text, (
        "codeql.yml không reference 'github/codeql-action/init@v3' — "
        "@v2 đã EOL từ 2025-01."
    )
    assert "github/codeql-action/analyze@v3" in text, (
        "codeql.yml không reference 'github/codeql-action/analyze@v3'."
    )


def test_codeql_workflow_triggers_pull_request_and_schedule() -> None:
    """Trigger phải có ``pull_request`` + ``schedule`` (weekly cron)."""
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_CODEQL_YML.read_text(encoding="utf-8"))
    on = data.get("on") or data.get(True)  # PyYAML may parse "on" as True
    assert on is not None, f"codeql.yml thiếu key `on:`. Keys: {list(data.keys())}"
    assert "pull_request" in on, (
        "codeql.yml `on` không chứa `pull_request` — fail-fast trên "
        "PR là yêu cầu cốt lõi của SAST."
    )
    assert "schedule" in on, (
        "codeql.yml `on` không chứa `schedule` — weekly cron giúp catch "
        "drift / new CVE patterns sau khi PR merged."
    )
    schedule = on["schedule"]
    assert schedule and any("cron" in s for s in schedule), (
        f"`schedule` không có cron expression: {schedule}"
    )


def test_codeql_workflow_matrix_includes_python() -> None:
    """Matrix language phải chứa ``python``."""
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_CODEQL_YML.read_text(encoding="utf-8"))
    jobs = data.get("jobs") or {}
    analyze = jobs.get("analyze") or {}
    matrix = (analyze.get("strategy") or {}).get("matrix") or {}
    languages = matrix.get("language") or []
    assert "python" in languages, (
        f"matrix.language = {languages!r}; phải chứa 'python' — codebase "
        "này là Python core."
    )


def test_codeql_workflow_uses_security_extended_queries() -> None:
    """Query set phải bao gồm ``security-extended`` (CWE coverage rộng)."""
    text = _CODEQL_YML.read_text(encoding="utf-8")
    assert "security-extended" in text, (
        "codeql.yml không enable 'security-extended' query set — "
        "default queries là minimal; security-extended thêm ~50 queries "
        "phủ CWE-78/79/89/918/etc."
    )


def test_codeql_workflow_grants_security_events_write_permission() -> None:
    """``permissions: security-events: write`` cần để upload SARIF results."""
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_CODEQL_YML.read_text(encoding="utf-8"))
    perms = data.get("permissions") or {}
    assert perms.get("security-events") == "write", (
        f"permissions.security-events = {perms.get('security-events')!r}; "
        "phải `write` để upload SARIF lên GitHub Security tab."
    )
