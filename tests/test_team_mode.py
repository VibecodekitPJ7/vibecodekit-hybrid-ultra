"""Cycle 7 PR2 — coverage Phase 2 cho ``team_mode``.

Mục tiêu: 41% → ≥80%.

Bao phủ:
* ``TeamConfig`` round-trip (as_dict / from_dict / _seq guard).
* ``read_team_config`` — exists / missing / malformed JSON / wrong field type.
* ``write_team_config`` — atomic write + tmp file path + chmod fallback.
* ``is_team_mode`` — true/false.
* ``assert_required_gates_run`` — empty / met / violation paths.
* ``_main`` — init / show (none + present) / check (skip + ok + violation
  + --gates-run override) / record / clear.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from vibecodekit import _logging as vl
from vibecodekit.team_mode import (
    TEAM_FILE,
    TeamConfig,
    TeamGateViolation,
    _main,
    assert_required_gates_run,
    is_team_mode,
    read_team_config,
    write_team_config,
)


# ---------------------------------------------------------------------------
# TeamConfig
# ---------------------------------------------------------------------------


def test_team_config_as_dict_roundtrip() -> None:
    cfg = TeamConfig(
        team_id="x",
        required=("/vck-review", "/vck-qa-only"),
        optional=("/vck-cso",),
        learnings_required=True,
        created_ts=1.0,
        updated_ts=2.0,
    )
    d = cfg.as_dict()
    assert d["team_id"] == "x"
    assert d["required"] == ["/vck-review", "/vck-qa-only"]
    assert d["optional"] == ["/vck-cso"]
    assert d["learnings_required"] is True
    # Round-trip
    cfg2 = TeamConfig.from_dict(d)
    assert cfg2.required == ("/vck-review", "/vck-qa-only")
    assert cfg2.optional == ("/vck-cso",)


def test_team_config_from_dict_rejects_string_for_list_field() -> None:
    """Bare string trong field list-type → ValueError (footgun guard)."""
    with pytest.raises(ValueError, match="expected list"):
        TeamConfig.from_dict({"team_id": "x", "required": "oops"})


def test_team_config_from_dict_handles_none_field() -> None:
    cfg = TeamConfig.from_dict({"team_id": "x"})  # required/optional missing
    assert cfg.required == ()
    assert cfg.optional == ()


def test_team_config_from_dict_coerces_values() -> None:
    cfg = TeamConfig.from_dict({
        "team_id": "x",
        "required": ["/a", "/b"],
        "optional": ("/c",),
        "learnings_required": 1,
        "created_ts": "1.5",
        "updated_ts": None,
    })
    assert cfg.required == ("/a", "/b")
    assert cfg.optional == ("/c",)
    assert cfg.learnings_required is True
    assert cfg.created_ts == 1.5
    assert cfg.updated_ts == 0.0


# ---------------------------------------------------------------------------
# read_team_config / write_team_config / is_team_mode
# ---------------------------------------------------------------------------


def test_is_team_mode_returns_false_when_absent(tmp_path: Path) -> None:
    assert is_team_mode(tmp_path) is False


def test_read_team_config_returns_none_when_absent(tmp_path: Path) -> None:
    assert read_team_config(tmp_path) is None


def test_write_then_read_team_config(tmp_path: Path) -> None:
    cfg = TeamConfig(team_id="t1", required=("/x",))
    written = write_team_config(cfg, root=tmp_path)
    assert written.team_id == "t1"
    assert written.created_ts > 0
    assert written.updated_ts >= written.created_ts
    # File trên disk
    p = tmp_path / TEAM_FILE
    assert p.is_file()
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["team_id"] == "t1"
    assert is_team_mode(tmp_path) is True
    # Read back
    rt = read_team_config(tmp_path)
    assert rt is not None
    assert rt.required == ("/x",)


def test_write_team_config_preserves_created_ts_on_update(
    tmp_path: Path,
) -> None:
    a = write_team_config(TeamConfig(team_id="t", required=("/x",)),
                           root=tmp_path)
    # Update với created_ts=0 → không reset; phải giữ created_ts cũ.
    b = write_team_config(TeamConfig(team_id="t", required=("/x", "/y")),
                           root=tmp_path)
    assert b.created_ts == a.created_ts
    assert b.updated_ts >= a.updated_ts


def test_read_team_config_returns_none_on_malformed_json(
    tmp_path: Path,
) -> None:
    p = tmp_path / TEAM_FILE
    p.parent.mkdir(parents=True)
    p.write_text("{not valid json", encoding="utf-8")
    assert read_team_config(tmp_path) is None


def test_read_team_config_returns_none_on_wrong_field_type(
    tmp_path: Path,
) -> None:
    p = tmp_path / TEAM_FILE
    p.parent.mkdir(parents=True)
    # required là string thay vì list → from_dict raise → fallback None.
    p.write_text(json.dumps({"team_id": "x", "required": "oops"}),
                 encoding="utf-8")
    assert read_team_config(tmp_path) is None


def test_write_team_config_chmod_failure_is_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nếu ``os.chmod`` raise (vd Windows ACL), write vẫn thành công."""
    real_chmod = os.chmod

    def _chmod_raise(path: Any, mode: int) -> None:
        raise OSError("simulated chmod failure")

    monkeypatch.setattr(os, "chmod", _chmod_raise)
    try:
        cfg = write_team_config(TeamConfig(team_id="t", required=("/x",)),
                                  root=tmp_path)
        assert cfg.team_id == "t"
        # File on disk via os.replace path.
        assert (tmp_path / TEAM_FILE).is_file()
    finally:
        monkeypatch.setattr(os, "chmod", real_chmod)


def test_write_team_config_cleans_up_tmp_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nếu ``os.replace`` raise, tmp file phải được unlink."""
    def _boom(src: Any, dst: Any) -> None:
        raise OSError("simulated rename failure")

    with patch("vibecodekit.team_mode.os.replace", _boom):
        with pytest.raises(OSError, match="simulated rename"):
            write_team_config(TeamConfig(team_id="t", required=("/x",)),
                                root=tmp_path)
    # Sau exception, KHÔNG còn tmp file rò rỉ trong .vibecode/.
    leftover = list((tmp_path / ".vibecode").glob("team.json.*.tmp"))
    assert leftover == []


# ---------------------------------------------------------------------------
# assert_required_gates_run
# ---------------------------------------------------------------------------


def test_assert_required_gates_run_no_team_config_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    # Không raise even khi gates_run rỗng.
    assert_required_gates_run([])


def test_assert_required_gates_run_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_team_config(
        TeamConfig(team_id="t", required=("/a", "/b")),
        root=tmp_path,
    )
    with pytest.raises(TeamGateViolation, match=r"\['/b'\]"):
        assert_required_gates_run(["/a"])


def test_assert_required_gates_run_met(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_team_config(
        TeamConfig(team_id="t", required=("/a", "/b")),
        root=tmp_path,
    )
    # Không raise.
    assert_required_gates_run(["/a", "/b", "/extra"])


# ---------------------------------------------------------------------------
# _main CLI
# ---------------------------------------------------------------------------


@pytest.fixture
def _capture_team_log() -> "tuple[io.StringIO, Any]":
    """StringIO log capture cho ``vibecodekit.team_mode`` namespace."""
    os.environ["VIBECODE_LOG_LEVEL"] = "DEBUG"
    os.environ["VIBECODE_LOG_JSON"] = "1"
    vl.reset_for_tests()
    logger = vl.get_logger("vibecodekit.team_mode")
    for h in list(logger.handlers):
        logger.removeHandler(h)
    import logging as _logging
    stream = io.StringIO()
    h = _logging.StreamHandler(stream)
    h.setFormatter(vl._JsonFormatter())
    logger.addHandler(h)
    yield stream, logger
    vl.reset_for_tests()
    os.environ.pop("VIBECODE_LOG_LEVEL", None)
    os.environ.pop("VIBECODE_LOG_JSON", None)


def _last_log(stream: io.StringIO) -> dict:
    raw = stream.getvalue().strip().splitlines()
    assert raw, "no log captured"
    return json.loads(raw[-1])


def test_main_init_creates_team_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    stream, _ = _capture_team_log
    rc = _main(["init", "--team-id", "T1",
                "--required", "/vck-review",
                "--required", "/vck-qa-only",
                "--optional", "/vck-cso",
                "--learnings-required"])
    assert rc == 0
    payload = _last_log(stream)
    assert payload["msg"] == "team_init"
    cfg = read_team_config(tmp_path)
    assert cfg is not None
    assert cfg.team_id == "T1"
    assert "/vck-review" in cfg.required
    assert "/vck-cso" in cfg.optional
    assert cfg.learnings_required is True


def test_main_show_returns_1_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    stream, _ = _capture_team_log
    rc = _main(["show"])
    assert rc == 1
    payload = _last_log(stream)
    assert payload["msg"] == "team_show_none"


def test_main_show_returns_0_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    write_team_config(TeamConfig(team_id="T", required=("/x",)), root=tmp_path)
    stream, _ = _capture_team_log
    rc = _main(["show"])
    assert rc == 0
    payload = _last_log(stream)
    assert payload["msg"] == "team_show"
    assert payload["config"]["team_id"] == "T"


def test_main_check_skips_when_no_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    stream, _ = _capture_team_log
    rc = _main(["check"])
    assert rc == 0
    payload = _last_log(stream)
    assert payload["msg"] == "team_check_skip"


def test_main_check_quiet_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    stream, _ = _capture_team_log
    rc = _main(["check", "--quiet"])
    assert rc == 0
    # KHÔNG log gì khi quiet.
    assert stream.getvalue().strip() == ""


def test_main_check_with_gates_run_override_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    write_team_config(
        TeamConfig(team_id="T", required=("/a", "/b")),
        root=tmp_path,
    )
    stream, _ = _capture_team_log
    rc = _main(["check", "--gates-run", "/a,/b,/extra"])
    assert rc == 0
    payload = _last_log(stream)
    assert payload["msg"] == "team_check_ok"
    assert payload["team_id"] == "T"


def test_main_check_violation_writes_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    write_team_config(
        TeamConfig(team_id="T", required=("/a", "/b")),
        root=tmp_path,
    )
    rc = _main(["check", "--gates-run", "/a"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "team_mode:" in err
    assert "/b" in err


def test_main_record_appends_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    stream, _ = _capture_team_log
    rc = _main(["record", "--gate", "/vck-review"])
    assert rc == 0
    payload = _last_log(stream)
    assert payload["msg"] == "team_record_gate"
    assert payload["entry"]["gate"] == "/vck-review"


def test_main_clear_wipes_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    _capture_team_log: "tuple[io.StringIO, Any]",
) -> None:
    monkeypatch.chdir(tmp_path)
    _main(["record", "--gate", "/x"])
    rc = _main(["clear"])
    assert rc == 0
    # Sau clear, gates_run trả empty.
    from vibecodekit import session_ledger
    assert session_ledger.gates_run() == []
