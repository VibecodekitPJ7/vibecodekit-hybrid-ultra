"""Coverage Phase 3 (cycle 9 PR2) cho ``vibecodekit.manifest_llm`` +
``vibecodekit.auto_writeback``.

Hai module này trước đây 0% coverage:

- ``manifest_llm.py`` (67 stmt) — generator cho ``manifest.llm.json``.
  Test phủ frontmatter parser (4 nhánh: empty / inline list / multi-line
  list / quoted value), `_ref_title` (H1 vs fallback), `build_manifest`
  (full vs missing files), `emit` (default path vs explicit output),
  `_main` (argparse round-trip qua ``monkeypatch``).
- ``auto_writeback.py`` (66 stmt) — opportunistic refresh wired vào
  ``session_start`` hook.  Test phủ rate-limit (`should_refresh`),
  opt-out marker (`auto_writeback_disabled`), state file lifecycle
  (`_read_last_run` malformed JSON / missing → 0.0; `_write_last_run`
  atomic write), `try_refresh` 6 nhánh (no_claude_md / opted_out /
  rate_limited / force / ok happy / exception swallow).

Goal: 0% → ≥ 80% line coverage cho cả hai module.  KHÔNG đụng runtime
logic — thuần test code dùng ``tmp_path`` + ``monkeypatch``.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from vibecodekit import auto_writeback as aw_mod
from vibecodekit import manifest_llm as ml_mod


# ===========================================================================
# manifest_llm.py
# ===========================================================================
# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------
def test_parse_frontmatter_returns_empty_when_missing() -> None:
    assert ml_mod._parse_frontmatter("# Plain markdown, no frontmatter\n") == {}


def test_parse_frontmatter_simple_key_value_quoted() -> None:
    text = (
        "---\n"
        'name: "vibecode"\n'
        "version: '0.17.0'\n"
        "---\n"
        "# Body\n"
    )
    out = ml_mod._parse_frontmatter(text)
    assert out["name"] == "vibecode"
    assert out["version"] == "0.17.0"


def test_parse_frontmatter_inline_list_literal() -> None:
    text = (
        "---\n"
        'triggers: ["foo", "bar", "baz"]\n'
        "---\n"
    )
    out = ml_mod._parse_frontmatter(text)
    assert out["triggers"] == ["foo", "bar", "baz"]


def test_parse_frontmatter_multiline_list_with_dashes() -> None:
    text = (
        "---\n"
        "paths:\n"
        '  - "scripts/"\n'
        '  - "tests/"\n'
        "---\n"
    )
    out = ml_mod._parse_frontmatter(text)
    assert out["paths"] == ["scripts/", "tests/"]


def test_parse_frontmatter_dash_continuation_when_key_not_list_is_ignored() -> None:
    """Sai cấu trúc YAML (`  - foo` khi key trước đó là string) → không append."""
    text = (
        "---\n"
        'name: "vck"\n'
        "  - this-line-is-orphan\n"
        "---\n"
    )
    out = ml_mod._parse_frontmatter(text)
    assert out["name"] == "vck"
    # `name` value vẫn là string, không bị mutate thành list.
    assert isinstance(out["name"], str)


# ---------------------------------------------------------------------------
# _ref_title
# ---------------------------------------------------------------------------
def test_ref_title_picks_first_h1() -> None:
    text = "# Real title\n\nbody body\n"
    assert ml_mod._ref_title(text, "fallback-id") == "Real title"


def test_ref_title_uses_fallback_when_no_h1() -> None:
    assert ml_mod._ref_title("no heading here\n", "00-overview") == "00-overview"


# ---------------------------------------------------------------------------
# build_manifest
# ---------------------------------------------------------------------------
def _seed_skill_root(tmp_path: Path,
                      *,
                      with_skill: bool = True,
                      with_refs: bool = True) -> Path:
    """Tạo skill bundle root tối thiểu cho `build_manifest`."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "plugin-manifest.json").write_text(
        json.dumps({
            "$schema": "x",
            "name": "vck",
            "version": "0.17.0",
            "commands": [{"name": "vibe-test"}],
            "agents": [{"name": "tester"}],
            "hooks": [{"name": "session_start"}],
            "servers": [{"name": "stdio"}],
        }),
        encoding="utf-8",
    )
    if with_skill:
        (tmp_path / "SKILL.md").write_text(
            "---\n"
            'name: "vck"\n'
            'version: "0.17.0"\n'
            'description: "Test skill"\n'
            'when_to_use: "always"\n'
            "triggers:\n"
            '  - "verb-route"\n'
            "paths:\n"
            '  - "scripts/"\n'
            "---\n"
            "# vck\n",
            encoding="utf-8",
        )
    if with_refs:
        (tmp_path / "references").mkdir()
        (tmp_path / "references" / "00-overview.md").write_text(
            "# Overview\n\nbody\n", encoding="utf-8",
        )
        (tmp_path / "references" / "24-memory.md").write_text(
            "no h1 here\n", encoding="utf-8",
        )
    return tmp_path


def test_build_manifest_full_skill_root(tmp_path: Path) -> None:
    skill_root = _seed_skill_root(tmp_path)
    manifest = ml_mod.build_manifest(skill_root)

    assert manifest["name"] == "vck"
    assert manifest["version"] == "0.17.0"
    assert manifest["description"] == "Test skill"
    assert manifest["skill_frontmatter"]["triggers"] == ["verb-route"]
    assert manifest["skill_frontmatter"]["paths"] == ["scripts/"]
    assert any(c["name"] == "vibe-test" for c in manifest["commands"])
    assert any(a["name"] == "tester" for a in manifest["agents"])

    # references: H1 picked + fallback-to-id.
    titles = {r["id"]: r["title"] for r in manifest["references"]}
    assert titles["00-overview"] == "Overview"
    assert titles["24-memory"] == "24-memory"

    # memory + introspection block đầy đủ.
    assert manifest["memory"]["writeback_module"] == \
        "vibecodekit.memory_writeback"
    assert "frontmatter_keys" in manifest["introspection"]


def test_build_manifest_raises_when_plugin_missing(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("---\n---\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="plugin-manifest.json"):
        ml_mod.build_manifest(tmp_path)


def test_build_manifest_skill_md_optional(tmp_path: Path) -> None:
    skill_root = _seed_skill_root(tmp_path, with_skill=False, with_refs=False)
    manifest = ml_mod.build_manifest(skill_root)
    # plugin-manifest.json cung cấp name + version, fallback "" cho description.
    assert manifest["name"] == "vck"
    assert manifest["description"] == ""
    assert manifest["references"] == []


def test_build_manifest_no_references_dir(tmp_path: Path) -> None:
    skill_root = _seed_skill_root(tmp_path, with_refs=False)
    manifest = ml_mod.build_manifest(skill_root)
    assert manifest["references"] == []


# ---------------------------------------------------------------------------
# emit + _main
# ---------------------------------------------------------------------------
def test_emit_writes_manifest_to_default_path(tmp_path: Path) -> None:
    skill_root = _seed_skill_root(tmp_path)
    out = ml_mod.emit(skill_root)
    assert out == skill_root.resolve() / "manifest.llm.json"
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == "vibecodekit.manifest.llm"


def test_emit_writes_manifest_to_explicit_output(tmp_path: Path) -> None:
    skill_root = _seed_skill_root(tmp_path)
    custom = tmp_path / "out" / "manifest.json"
    custom.parent.mkdir()
    out = ml_mod.emit(skill_root, output=custom, indent=4)
    assert out == custom
    assert custom.is_file()
    raw = custom.read_text(encoding="utf-8")
    assert raw.startswith("{\n    ")  # indent=4 verified


def test_main_prints_written_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill_root = _seed_skill_root(tmp_path)
    out_path = tmp_path / "manifest.llm.json"
    monkeypatch.setattr(
        "sys.argv",
        ["manifest_llm",
         "--root", str(skill_root),
         "--output", str(out_path)],
    )
    rc = ml_mod._main()
    assert rc == 0
    assert out_path.is_file()
    captured = capsys.readouterr()
    assert "wrote " in captured.out


# ===========================================================================
# auto_writeback.py
# ===========================================================================
# ---------------------------------------------------------------------------
# RefreshDecision dataclass
# ---------------------------------------------------------------------------
def test_refresh_decision_default_fields() -> None:
    rd = aw_mod.RefreshDecision(False, "no_claude_md")
    assert rd.ran is False
    assert rd.reason == "no_claude_md"
    assert rd.elapsed_s == 0.0
    assert rd.sections_updated == ()


# ---------------------------------------------------------------------------
# _read_last_run / _write_last_run
# ---------------------------------------------------------------------------
def test_read_last_run_returns_zero_when_no_state(tmp_path: Path) -> None:
    assert aw_mod._read_last_run(tmp_path) == 0.0


def test_read_last_run_zero_on_malformed_json(tmp_path: Path) -> None:
    sd = tmp_path / ".vibecode"
    sd.mkdir()
    (sd / aw_mod.STATE_FILENAME).write_text("not-json{", encoding="utf-8")
    assert aw_mod._read_last_run(tmp_path) == 0.0


def test_write_last_run_creates_dir_and_atomic(tmp_path: Path) -> None:
    aw_mod._write_last_run(tmp_path, 1234.5,
                            reason="ok",
                            sections=("stack",))
    state = tmp_path / ".vibecode" / aw_mod.STATE_FILENAME
    assert state.is_file()
    data = json.loads(state.read_text(encoding="utf-8"))
    assert data["last_run_ts"] == 1234.5
    assert data["last_reason"] == "ok"
    assert data["sections_updated"] == ["stack"]
    assert data["last_run_iso"].endswith("Z")
    # tmp file đã được os.replace → không còn lưu lại.
    assert not (tmp_path / ".vibecode" / (aw_mod.STATE_FILENAME + ".tmp")).exists()


def test_read_after_write_round_trip(tmp_path: Path) -> None:
    aw_mod._write_last_run(tmp_path, 9876.0)
    assert aw_mod._read_last_run(tmp_path) == 9876.0


# ---------------------------------------------------------------------------
# should_refresh
# ---------------------------------------------------------------------------
def test_should_refresh_true_when_no_state(tmp_path: Path) -> None:
    assert aw_mod.should_refresh(tmp_path, min_interval_seconds=60,
                                  now=1000.0) is True


def test_should_refresh_false_within_interval(tmp_path: Path) -> None:
    aw_mod._write_last_run(tmp_path, 1000.0)
    assert aw_mod.should_refresh(tmp_path, min_interval_seconds=600,
                                  now=1100.0) is False


def test_should_refresh_true_after_interval(tmp_path: Path) -> None:
    aw_mod._write_last_run(tmp_path, 1000.0)
    assert aw_mod.should_refresh(tmp_path, min_interval_seconds=600,
                                  now=2000.0) is True


def test_should_refresh_respects_disable_marker(tmp_path: Path) -> None:
    sd = tmp_path / ".vibecode"
    sd.mkdir()
    (sd / aw_mod.DISABLE_MARKER).touch()
    # Cho dù không có state, vẫn return False vì opt-out.
    assert aw_mod.should_refresh(tmp_path, now=10**9) is False


def test_should_refresh_default_now_uses_time_time(tmp_path: Path) -> None:
    """``now=None`` fallback dùng ``time.time()`` — verify không crash."""
    aw_mod._write_last_run(tmp_path, 0.0)
    # Last run ts=0 + interval 60s + now=time.time() (current) → should
    # always return True trong môi trường thực.
    assert aw_mod.should_refresh(tmp_path, min_interval_seconds=60) is True


# ---------------------------------------------------------------------------
# try_refresh
# ---------------------------------------------------------------------------
def test_try_refresh_no_claude_md(tmp_path: Path) -> None:
    rd = aw_mod.try_refresh(tmp_path)
    assert rd.ran is False
    assert rd.reason == "no_claude_md"


def test_try_refresh_opted_out_when_marker_present(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("body\n", encoding="utf-8")
    sd = tmp_path / ".vibecode"
    sd.mkdir()
    (sd / aw_mod.DISABLE_MARKER).touch()
    rd = aw_mod.try_refresh(tmp_path)
    assert rd.ran is False
    assert rd.reason == "opted_out"


def test_try_refresh_rate_limited(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("body\n", encoding="utf-8")
    aw_mod._write_last_run(tmp_path, 1000.0)
    rd = aw_mod.try_refresh(tmp_path,
                             min_interval_seconds=600,
                             now=1100.0)
    assert rd.ran is False
    assert rd.reason == "rate_limited"


def test_try_refresh_ok_happy_path(tmp_path: Path) -> None:
    """Force=True → bỏ qua rate-limit + opt-out → chạy update + ghi state."""
    (tmp_path / "CLAUDE.md").write_text(
        "user content\n\n"
        "<!-- vibecode:auto:stack:begin -->\n"
        "OLD\n"
        "<!-- vibecode:auto:stack:end -->\n",
        encoding="utf-8",
    )
    rd = aw_mod.try_refresh(tmp_path, force=True, now=2000.0)
    assert rd.ran is True
    assert rd.reason == "ok"
    # State file đã được ghi.
    state = tmp_path / ".vibecode" / aw_mod.STATE_FILENAME
    assert state.is_file()
    data = json.loads(state.read_text(encoding="utf-8"))
    assert data["last_reason"] == "ok"


def test_try_refresh_force_overrides_opt_out(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("body\n", encoding="utf-8")
    sd = tmp_path / ".vibecode"
    sd.mkdir()
    (sd / aw_mod.DISABLE_MARKER).touch()
    rd = aw_mod.try_refresh(tmp_path, force=True, now=3000.0)
    # Opt-out check: `force` bỏ qua → vẫn chạy update, reason ok.
    assert rd.ran is True
    assert rd.reason == "ok"


def test_try_refresh_swallows_exception_records_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``MemoryWriteback.update`` raise → reason có prefix 'error:'."""
    (tmp_path / "CLAUDE.md").write_text("body\n", encoding="utf-8")

    class _BoomWriteback:
        def __init__(self, *a: Any, **kw: Any) -> None:
            pass

        def update(self) -> None:
            raise RuntimeError("simulated failure")

    monkeypatch.setattr(aw_mod, "__name__", "vibecodekit.auto_writeback")
    # Patch lazy-imported memory_writeback.MemoryWriteback.
    from vibecodekit import memory_writeback as mw_mod
    monkeypatch.setattr(mw_mod, "MemoryWriteback", _BoomWriteback)

    rd = aw_mod.try_refresh(tmp_path, force=True, now=5000.0)
    assert rd.ran is False
    assert rd.reason.startswith("error: ")
    assert "RuntimeError" in rd.reason
    # State vẫn được ghi (best-effort) với reason error:.
    state = tmp_path / ".vibecode" / aw_mod.STATE_FILENAME
    assert state.is_file()


def test_try_refresh_swallows_secondary_state_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cả update + _write_last_run fallback đều raise → vẫn return RD."""
    (tmp_path / "CLAUDE.md").write_text("body\n", encoding="utf-8")

    class _BoomWriteback:
        def __init__(self, *a: Any, **kw: Any) -> None:
            pass

        def update(self) -> None:
            raise RuntimeError("inner failure")

    from vibecodekit import memory_writeback as mw_mod
    monkeypatch.setattr(mw_mod, "MemoryWriteback", _BoomWriteback)

    # Make `_write_last_run` raise in BOTH the success-path call and the
    # error-path retry — verify outermost `try` swallows it.
    def _boom_write(*a: Any, **kw: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(aw_mod, "_write_last_run", _boom_write)

    rd = aw_mod.try_refresh(tmp_path, force=True, now=6000.0)
    assert rd.ran is False
    assert rd.reason.startswith("error: ")


def test_try_refresh_default_now_uses_time_time(tmp_path: Path) -> None:
    """Verify ``now=None`` path không crash khi rate-limited."""
    (tmp_path / "CLAUDE.md").write_text("body\n", encoding="utf-8")
    aw_mod._write_last_run(tmp_path, time.time())
    # Min interval rất lớn → chắc chắn rate-limited dù now là current time.
    rd = aw_mod.try_refresh(tmp_path, min_interval_seconds=10**9)
    assert rd.ran is False
    assert rd.reason == "rate_limited"
