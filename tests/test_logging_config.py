"""CI guard cho PR2 — structured logging helper.

Scope:

* ``VIBECODE_LOG_LEVEL`` env được honour (DEBUG / INFO / WARNING).
* ``VIBECODE_LOG_JSON=1`` xuất JSON parseable cho mỗi record.
* ``logger.propagate`` = False (tránh bão log khi downstream cấu hình
  root logger).
* Logger được cache per-name — cùng ``name`` trả cùng instance.
* Smoke: ``permission_engine.decide`` emit event khi deny pattern
  (kiểm tra integration giữa helper + module consumer).

Không verify nội dung chi tiết của message (tránh drift khi wording
thay đổi); chỉ verify shape + env wiring.
"""
from __future__ import annotations

import io
import json
import logging
import os
from typing import Iterator

import pytest


# Import helper lazily để mỗi test có thể reset env trước khi get_logger.


@pytest.fixture
def clean_logger_cache() -> Iterator[None]:
    """Reset logger cache + env sandbox cho test độc lập."""
    from vibecodekit import _logging as vl

    saved_env = {
        "VIBECODE_LOG_LEVEL": os.environ.pop("VIBECODE_LOG_LEVEL", None),
        "VIBECODE_LOG_JSON": os.environ.pop("VIBECODE_LOG_JSON", None),
    }
    vl.reset_for_tests()
    try:
        yield
    finally:
        vl.reset_for_tests()
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _make_logger_with_stream(
    name: str, stream: io.StringIO
) -> logging.Logger:
    """Create logger via helper rồi redirect handler sang stream."""
    from vibecodekit._logging import get_logger

    logger = get_logger(name)
    # Replace existing handler(s) với StringIO để capture.
    for h in list(logger.handlers):
        logger.removeHandler(h)
    import logging as _logging
    h = _logging.StreamHandler(stream)
    # Giữ formatter hiện tại theo env — re-instantiate để same class.
    from vibecodekit._logging import _JsonFormatter

    if os.environ.get("VIBECODE_LOG_JSON") == "1":
        h.setFormatter(_JsonFormatter())
    else:
        h.setFormatter(
            _logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
    logger.addHandler(h)
    return logger


def test_logger_respects_log_level(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_LEVEL"] = "WARNING"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_level", stream)
    logger.info("info message")
    logger.warning("warn message")
    output = stream.getvalue()
    assert "warn message" in output
    assert "info message" not in output


def test_logger_debug_level_passes_through(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_LEVEL"] = "DEBUG"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_debug", stream)
    logger.debug("debug message")
    assert "debug message" in stream.getvalue()


def test_invalid_level_falls_back_to_info(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_LEVEL"] = "NOT_A_LEVEL"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_invalid", stream)
    logger.info("info msg")
    logger.debug("debug msg")
    output = stream.getvalue()
    assert "info msg" in output
    assert "debug msg" not in output


def test_json_format(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_JSON"] = "1"
    os.environ["VIBECODE_LOG_LEVEL"] = "INFO"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_json", stream)
    logger.info("hello", extra={"decision": "deny", "rule_id": "R-001"})
    raw = stream.getvalue().strip().splitlines()[-1]
    payload = json.loads(raw)
    assert payload["level"] == "INFO"
    assert payload["msg"] == "hello"
    assert payload["name"] == "vibecodekit._test_json"
    assert payload["decision"] == "deny"
    assert payload["rule_id"] == "R-001"
    assert "ts" in payload


def test_logger_does_not_propagate(clean_logger_cache: None) -> None:
    from vibecodekit._logging import get_logger

    logger = get_logger("vibecodekit._test_propagate")
    assert logger.propagate is False


def test_logger_is_cached_per_name(clean_logger_cache: None) -> None:
    from vibecodekit._logging import get_logger

    a = get_logger("vibecodekit._test_cache")
    b = get_logger("vibecodekit._test_cache")
    assert a is b
    # Handler chỉ được add một lần dù gọi nhiều lần.
    assert len([h for h in a.handlers]) == 1


def test_permission_engine_logs_deny(clean_logger_cache: None) -> None:
    """Integration smoke: permission_engine phải emit event khi deny."""
    os.environ["VIBECODE_LOG_LEVEL"] = "DEBUG"
    os.environ["VIBECODE_LOG_JSON"] = "1"
    stream = io.StringIO()
    _make_logger_with_stream("vibecodekit.permission_engine", stream)

    from vibecodekit.permission_engine import decide

    decision = decide("rm -rf /", mode="default")
    assert decision["decision"] == "deny"
    logged = stream.getvalue().strip()
    assert logged, "expected at least one log line for deny decision"
    last = json.loads(logged.splitlines()[-1])
    assert last["decision"] == "deny"
    assert last["name"] == "vibecodekit.permission_engine"


# ---------------------------------------------------------------------------
# Cycle 6 PR4 — assert each migrated module emits log dưới đúng namespace.
# ---------------------------------------------------------------------------


def _capture_module_logs(module_logger: str) -> io.StringIO:
    """Tạo StringIO handler cho một module logger, set DEBUG."""
    os.environ["VIBECODE_LOG_LEVEL"] = "DEBUG"
    os.environ["VIBECODE_LOG_JSON"] = "1"
    stream = io.StringIO()
    _make_logger_with_stream(module_logger, stream)
    return stream


def test_dashboard_main_emits_structured_log(
    clean_logger_cache: None, tmp_path: "object"
) -> None:
    """`dashboard._main` phải emit log namespace ``vibecodekit.dashboard``."""
    import sys

    stream = _capture_module_logs("vibecodekit.dashboard")
    from vibecodekit import dashboard as dash

    saved_argv = sys.argv[:]
    try:
        sys.argv = ["dashboard", "--root", str(tmp_path), "--json"]
        dash._main()
    finally:
        sys.argv = saved_argv
    raw = stream.getvalue().strip().splitlines()
    assert raw, "expected dashboard to emit at least one log line"
    payload = json.loads(raw[-1])
    assert payload["name"] == "vibecodekit.dashboard"
    assert payload["level"] == "INFO"


def test_team_mode_show_emits_structured_log(
    clean_logger_cache: None, tmp_path: "object", monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`team_mode._main show` (no config) phải emit log ``vibecodekit.team_mode``."""
    stream = _capture_module_logs("vibecodekit.team_mode")
    monkeypatch.chdir(tmp_path)
    from vibecodekit import team_mode

    rc = team_mode._main(["show"])
    assert rc == 1
    raw = stream.getvalue().strip().splitlines()
    assert raw
    payload = json.loads(raw[-1])
    assert payload["name"] == "vibecodekit.team_mode"


def test_security_classifier_main_emits_structured_log(
    clean_logger_cache: None,
) -> None:
    """`security_classifier._main --text --json` phải emit log
    ``vibecodekit.security_classifier`` (allow path → INFO level)."""
    stream = _capture_module_logs("vibecodekit.security_classifier")
    from vibecodekit import security_classifier as sc

    rc = sc._main(["--text", "hello world", "--json"])
    assert rc in (0, 2)
    raw = stream.getvalue().strip().splitlines()
    assert raw
    payload = json.loads(raw[-1])
    assert payload["name"] == "vibecodekit.security_classifier"


def test_learnings_capture_emits_structured_log(
    clean_logger_cache: None, tmp_path: "object", monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`learnings._main capture` phải emit log ``vibecodekit.learnings``."""
    stream = _capture_module_logs("vibecodekit.learnings")
    monkeypatch.chdir(tmp_path)
    from vibecodekit import learnings

    rc = learnings._main(["capture", "--scope", "project", "test learning"])
    assert rc == 0
    raw = stream.getvalue().strip().splitlines()
    assert raw
    payload = json.loads(raw[-1])
    assert payload["name"] == "vibecodekit.learnings"
    assert payload["msg"] == "learning_captured"


def test_no_print_in_migrated_modules() -> None:
    """Cycle 6 PR4 invariant: 4 migrated module KHÔNG còn ``print(``.

    `conformance_audit.py` GIỮ 3 print final-report theo carve-out
    spec ('final report user xem trên terminal → GIỮ').  Embedded
    Python-string trong probe không tính (không phải module print).
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    migrated = [
        "dashboard.py",
        "team_mode.py",
        "security_classifier.py",
        "learnings.py",
    ]
    for fname in migrated:
        src = (repo / "scripts" / "vibecodekit" / fname).read_text(
            encoding="utf-8"
        )
        # ``print(`` ở đầu dòng (sau optional whitespace). Loại trừ
        # chuỗi bên trong dedent triple-quoted (ít nhất với module
        # đã migrate, KHÔNG có embedded probe).
        matches = re.findall(r"^[ \t]*print\(", src, flags=re.MULTILINE)
        assert not matches, (
            f"{fname} vẫn còn {len(matches)} print() — phải migrate sang "
            f"_log.info / _log.warning / _log.debug"
        )
