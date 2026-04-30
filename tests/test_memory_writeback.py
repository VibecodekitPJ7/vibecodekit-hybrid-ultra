"""Coverage Phase 3 (cycle 9 PR1) cho ``vibecodekit.memory_writeback``.

Module ``memory_writeback.py`` (229 stmt) trước đây 0% coverage.  Test suite
này phủ:

- 5 section detector (``_detect_stack`` / ``_detect_scripts`` /
  ``_detect_conventions`` / ``_detect_gotchas`` / ``_detect_test_strategy``)
  — mỗi detector chạy với fixture repo nhỏ (``tmp_path``) chứa các file
  trigger để hit từng nhánh ``if`` (next.js / react / fastapi / vitest /
  jest / make targets / src.api / app/page.tsx / run-history malformed
  JSON / pytest.ini absence / empty fallback).
- ``MemoryWriteback`` class (4 method public): ``init`` (tạo mới + no-op
  khi đã tồn tại + ``dry_run``), ``update`` (added vs updated, preserve
  user content ngoài marker, no-change → no write), ``check`` (drift
  semantics: missing / drifted / extra), ``nest`` (subdir + raise khi
  target không phải dir + raise khi escape repo).
- Marker manipulation helpers: ``_build_section`` / ``_extract_sections``
  / ``_replace_section`` (qua public API operations).
- Dataclass shape: ``DiffReport.changed`` / ``DriftReport.in_sync``
  property đúng semantics khi không có thay đổi.

Goal: 0% → ≥ 80% line coverage cho module.  KHÔNG đụng runtime logic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit.memory_writeback import (
    DiffReport,
    DriftReport,
    MemoryWriteback,
    _build_section,
    _extract_sections,
    _replace_section,
    _read,
    _detect_stack,
    _detect_scripts,
    _detect_conventions,
    _detect_gotchas,
    _detect_test_strategy,
)


# ---------------------------------------------------------------------------
# Helper utilities (module-level functions)
# ---------------------------------------------------------------------------
def test_read_missing_file_returns_empty_string(tmp_path: Path) -> None:
    """``_read`` trả "" khi file không tồn tại (OSError swallow)."""
    assert _read(tmp_path / "does-not-exist.txt") == ""


def test_read_existing_file_returns_content(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("hello\nworld", encoding="utf-8")
    assert _read(p) == "hello\nworld"


def test_read_invalid_unicode_returns_empty_string(tmp_path: Path) -> None:
    """``_read`` swallow ``UnicodeDecodeError`` khi gặp byte không phải UTF-8."""
    p = tmp_path / "bin.bin"
    # 0xFF không hợp lệ UTF-8 ở mọi vị trí → trigger UnicodeDecodeError.
    p.write_bytes(b"\xff\xfe\xfd")
    assert _read(p) == ""


def test_build_section_wraps_body_with_markers() -> None:
    out = _build_section("stack", "  - foo\n")
    assert out.startswith("<!-- vibecode:auto:stack:begin -->")
    assert out.endswith("<!-- vibecode:auto:stack:end -->")
    assert "- foo" in out


def test_extract_sections_finds_all_named_blocks() -> None:
    text = (
        "<!-- vibecode:auto:stack:begin -->\nA\n<!-- vibecode:auto:stack:end -->"
        "\n\n"
        "<!-- vibecode:auto:scripts:begin -->\nB\n<!-- vibecode:auto:scripts:end -->"
    )
    out = _extract_sections(text)
    assert out == {"stack": "A", "scripts": "B"}


def test_replace_section_appends_when_absent() -> None:
    text = "user content\n"
    out = _replace_section(text, "stack", "X")
    assert "user content" in out
    assert "<!-- vibecode:auto:stack:begin -->" in out
    assert "X" in out


def test_replace_section_substitutes_when_present() -> None:
    text = (
        "<!-- vibecode:auto:stack:begin -->\nOLD\n"
        "<!-- vibecode:auto:stack:end -->"
    )
    out = _replace_section(text, "stack", "NEW")
    assert "OLD" not in out
    assert "NEW" in out


# ---------------------------------------------------------------------------
# Section detectors
# ---------------------------------------------------------------------------
def test_detect_stack_handles_empty_repo(tmp_path: Path) -> None:
    assert _detect_stack(tmp_path) == "- (no stack auto-detected)"


def test_detect_stack_node_next_react_expo(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"engines": {"node": ">=20"},'
        ' "dependencies": {"next": "14.0.0", "react": "18.0.0"},'
        ' "devDependencies": {"expo": "50.0.0"}}',
        encoding="utf-8",
    )
    out = _detect_stack(tmp_path)
    assert "Next.js" in out and "14.0.0" in out
    assert "React" in out and "18.0.0" in out
    assert "Expo" in out and "50.0.0" in out
    assert "Node" in out and ">=20" in out


def test_detect_stack_python_fastapi_django(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        'requires-python = ">=3.10"\n'
        "dependencies = ['fastapi', 'django']\n",
        encoding="utf-8",
    )
    out = _detect_stack(tmp_path)
    assert "Python" in out and ">=3.10" in out
    assert "FastAPI" in out
    assert "Django" in out


def test_detect_stack_go_and_rust(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text(
        "module example.com/x\n\ngo 1.22\n", encoding="utf-8",
    )
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8",
    )
    out = _detect_stack(tmp_path)
    assert "Go" in out and "1.22" in out
    assert "Rust" in out


def test_detect_stack_handles_malformed_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("not-json{", encoding="utf-8")
    # KHÔNG raise, fallback empty.
    assert _detect_stack(tmp_path) == "- (no stack auto-detected)"


def test_detect_scripts_npm_and_makefile(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"scripts": {"build": "tsc", "test": "vitest"}}',
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text(
        "lint:\n\truff check .\n"
        "fmt:\n\truff format .\n",
        encoding="utf-8",
    )
    out = _detect_scripts(tmp_path)
    assert "npm run build" in out
    assert "npm run test" in out
    assert "make lint" in out
    assert "make fmt" in out


def test_detect_scripts_handles_malformed_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not json", encoding="utf-8")
    assert _detect_scripts(tmp_path) == "- (no scripts auto-detected)"


def test_detect_scripts_empty_repo(tmp_path: Path) -> None:
    assert _detect_scripts(tmp_path) == "- (no scripts auto-detected)"


def test_detect_conventions_picks_known_layouts(tmp_path: Path) -> None:
    (tmp_path / "src" / "api").mkdir(parents=True)
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("# fastapi", encoding="utf-8")
    (tmp_path / "components").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts").mkdir()
    out = _detect_conventions(tmp_path)
    assert "src/api/" in out
    assert "FastAPI entrypoint" in out
    assert "components/" in out
    assert "tests/" in out
    assert "scripts/" in out


def test_detect_conventions_nextjs_app_router(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "page.tsx").write_text("export default", encoding="utf-8")
    (tmp_path / "test").mkdir()
    out = _detect_conventions(tmp_path)
    assert "Next.js App Router" in out
    assert "Tests in `test/`" in out


def test_detect_conventions_empty_repo(tmp_path: Path) -> None:
    assert _detect_conventions(tmp_path) == "- (no conventions auto-detected)"


def test_detect_gotchas_no_history_returns_placeholder(tmp_path: Path) -> None:
    out = _detect_gotchas(tmp_path)
    assert "no run-history" in out


def test_detect_gotchas_history_no_errors(tmp_path: Path) -> None:
    (tmp_path / ".vibecode").mkdir()
    (tmp_path / ".vibecode" / "run-history.jsonl").write_text(
        '{"ok": true}\n', encoding="utf-8",
    )
    out = _detect_gotchas(tmp_path)
    assert "no gotchas accumulated" in out


def test_detect_gotchas_ranks_top_signatures(tmp_path: Path) -> None:
    (tmp_path / ".vibecode").mkdir()
    lines = [
        '{"error": "ZeroDivisionError: division by zero"}',
        '{"error": "ZeroDivisionError: division by zero"}',
        '{"error": "ZeroDivisionError: division by zero"}',
        '{"err": "PermissionError: Operation not permitted"}',
        '{"stderr": "ConnectionError: timed out"}',
        "",  # blank line ignored
        "not-json{",  # invalid JSON ignored
        '{"unrelated": "noop"}',  # no error key ignored
    ]
    (tmp_path / ".vibecode" / "run-history.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8",
    )
    out = _detect_gotchas(tmp_path)
    assert "(3×)" in out
    assert "ZeroDivisionError" in out
    assert "PermissionError" in out
    assert "ConnectionError" in out


def test_detect_test_strategy_pytest_and_conftest(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\nminversion = '8.0'\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "conftest.py").write_text("# fix", encoding="utf-8")
    out = _detect_test_strategy(tmp_path)
    assert "pytest" in out
    assert "conftest.py" in out


def test_detect_test_strategy_vitest_and_jest(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"devDependencies": {"vitest": "1.0.0", "jest": "29.0.0"}}',
        encoding="utf-8",
    )
    out = _detect_test_strategy(tmp_path)
    assert "vitest" in out
    assert "jest" in out


def test_detect_test_strategy_empty_repo(tmp_path: Path) -> None:
    assert _detect_test_strategy(tmp_path) == "- (no test framework auto-detected)"


# ---------------------------------------------------------------------------
# MemoryWriteback class — init / update / check / nest
# ---------------------------------------------------------------------------
def test_init_creates_claude_md_from_scratch(tmp_path: Path) -> None:
    mw = MemoryWriteback(tmp_path)
    report = mw.init()

    assert report.path == tmp_path / "CLAUDE.md"
    assert (tmp_path / "CLAUDE.md").is_file()
    assert set(report.sections_added) == {
        "stack", "scripts", "conventions", "gotchas", "test-strategy",
    }
    assert report.bytes_before == 0
    assert report.bytes_after > 0
    assert report.changed
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    for marker in ("stack", "scripts", "conventions",
                   "gotchas", "test-strategy"):
        assert f"vibecode:auto:{marker}:begin" in text
        assert f"vibecode:auto:{marker}:end" in text


def test_init_dry_run_does_not_write(tmp_path: Path) -> None:
    mw = MemoryWriteback(tmp_path)
    report = mw.init(dry_run=True)
    assert report.changed
    assert not (tmp_path / "CLAUDE.md").exists()


def test_init_when_file_exists_delegates_to_update(tmp_path: Path) -> None:
    """Spec: ``init`` no-op khi file đã tồn tại — delegate ``update``."""
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "user header\n"
        "<!-- vibecode:auto:stack:begin -->\n"
        "- (no stack auto-detected)\n"
        "<!-- vibecode:auto:stack:end -->\n",
        encoding="utf-8",
    )
    mw = MemoryWriteback(tmp_path)
    report = mw.init()
    # Vì ``init`` delegate ``update``, các section còn thiếu sẽ được added,
    # KHÔNG phải `sections_added=tuple(self.sections)`.
    assert "user header" in target.read_text(encoding="utf-8")
    # 4/5 section còn thiếu (chỉ có ``stack``) → added.
    assert set(report.sections_added) >= {
        "scripts", "conventions", "gotchas", "test-strategy",
    }


def test_update_preserves_user_content_outside_markers(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "# Tôi là user content\n\n"
        "Đoạn text không nên bị động đến.\n\n"
        "<!-- vibecode:auto:stack:begin -->\n"
        "OLD-stale\n"
        "<!-- vibecode:auto:stack:end -->\n",
        encoding="utf-8",
    )
    mw = MemoryWriteback(tmp_path)
    report = mw.update()

    text = target.read_text(encoding="utf-8")
    assert "Tôi là user content" in text
    assert "Đoạn text không nên bị động đến." in text
    assert "OLD-stale" not in text  # đã refresh
    assert "stack" in report.sections_updated


def test_update_no_change_when_already_in_sync(tmp_path: Path) -> None:
    mw = MemoryWriteback(tmp_path)
    mw.init()
    bytes_before = (tmp_path / "CLAUDE.md").read_bytes()
    report = mw.update()
    bytes_after = (tmp_path / "CLAUDE.md").read_bytes()
    assert bytes_before == bytes_after
    assert not report.changed


def test_update_dry_run_does_not_write(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "<!-- vibecode:auto:stack:begin -->\n"
        "OLD\n"
        "<!-- vibecode:auto:stack:end -->\n",
        encoding="utf-8",
    )
    mw = MemoryWriteback(tmp_path)
    mw.update(dry_run=True)
    # Vẫn còn OLD vì dry-run không write.
    assert "OLD" in target.read_text(encoding="utf-8")


def test_update_when_file_missing_delegates_to_init(tmp_path: Path) -> None:
    mw = MemoryWriteback(tmp_path)
    report = mw.update()
    assert (tmp_path / "CLAUDE.md").is_file()
    assert set(report.sections_added) == {
        "stack", "scripts", "conventions", "gotchas", "test-strategy",
    }


def test_check_in_sync_after_init(tmp_path: Path) -> None:
    mw = MemoryWriteback(tmp_path)
    mw.init()
    drift = mw.check()
    assert drift.in_sync
    assert drift.drifted == ()
    assert drift.missing == ()


def test_check_reports_missing_sections(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "<!-- vibecode:auto:stack:begin -->\n"
        "- (no stack auto-detected)\n"
        "<!-- vibecode:auto:stack:end -->\n",
        encoding="utf-8",
    )
    mw = MemoryWriteback(tmp_path)
    drift = mw.check()
    assert "scripts" in drift.missing
    assert "test-strategy" in drift.missing
    assert not drift.in_sync


def test_check_reports_drifted_section(tmp_path: Path) -> None:
    mw = MemoryWriteback(tmp_path)
    mw.init()
    # Manually rewrite stack section với content cũ.
    target = tmp_path / "CLAUDE.md"
    text = target.read_text(encoding="utf-8")
    text = text.replace(
        "- (no stack auto-detected)", "- **Outdated** stale", 1,
    )
    target.write_text(text, encoding="utf-8")
    drift = mw.check()
    assert "stack" in drift.drifted


def test_check_reports_extra_unmanaged_section(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "<!-- vibecode:auto:stack:begin -->\n"
        "- (no stack auto-detected)\n"
        "<!-- vibecode:auto:stack:end -->\n\n"
        "<!-- vibecode:auto:custom-extra:begin -->\n"
        "manual\n"
        "<!-- vibecode:auto:custom-extra:end -->\n",
        encoding="utf-8",
    )
    mw = MemoryWriteback(tmp_path)
    drift = mw.check()
    assert "custom-extra" in drift.extra


def test_nest_creates_subdir_claude_md(tmp_path: Path) -> None:
    sub = tmp_path / "apps" / "api"
    sub.mkdir(parents=True)
    mw = MemoryWriteback(tmp_path)
    mw.nest(sub.relative_to(tmp_path))
    assert (sub / "CLAUDE.md").is_file()


def test_nest_raises_when_target_not_directory(tmp_path: Path) -> None:
    not_dir = tmp_path / "not-a-dir.txt"
    not_dir.write_text("file", encoding="utf-8")
    mw = MemoryWriteback(tmp_path)
    with pytest.raises(ValueError, match="not a directory"):
        mw.nest("not-a-dir.txt")


def test_nest_raises_when_target_escapes_repo(tmp_path: Path) -> None:
    """Path traversal guard: ``nest("..")`` không được escape."""
    sub = tmp_path / "child"
    sub.mkdir()
    mw = MemoryWriteback(sub)
    with pytest.raises(ValueError, match="escapes repo"):
        mw.nest("../")


# ---------------------------------------------------------------------------
# Dataclass shape
# ---------------------------------------------------------------------------
def test_diff_report_changed_property_false_when_empty() -> None:
    report = DiffReport(
        path=Path("x"),
        sections_added=(),
        sections_updated=(),
        sections_removed=(),
        bytes_before=0,
        bytes_after=0,
        preview="",
    )
    assert not report.changed


def test_drift_report_in_sync_property_true_when_clean() -> None:
    report = DriftReport(
        path=Path("x"),
        drifted=(),
        missing=(),
        extra=(),
    )
    assert report.in_sync
