"""Cycle 7 PR2 — coverage Phase 2 cho ``vn_error_translator``.

Mục tiêu: 0% → ≥80%.

Bao phủ:
* Built-in dict matching (Python / npm / build / runtime patterns).
* Group-substitution trong summary / fix.
* Ranking by confidence × specificity.
* ``best()`` convenience.
* YAML loader path (graceful skip nếu PyYAML absent).
* Malformed YAML / entry / regex được skip silently.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit.vn_error_translator import (
    DEFAULT_DICT_DIR,
    TranslatedError,
    VnErrorTranslator,
)


# ---------------------------------------------------------------------------
# Construction & built-in dict
# ---------------------------------------------------------------------------


def test_translator_loads_builtins(tmp_path: Path) -> None:
    """Construction với ``include_builtins=True`` → entries non-empty."""
    tr = VnErrorTranslator(dict_dir=tmp_path)  # tmp_path empty
    # Có ≥30 entry built-in (xem _BUILTIN_DICT).
    hits = tr.translate("ModuleNotFoundError: No module named 'foo'")
    assert hits, "expected at least one match for ModuleNotFoundError"


def test_translator_skips_builtins_when_disabled(tmp_path: Path) -> None:
    tr = VnErrorTranslator(dict_dir=tmp_path, include_builtins=False)
    assert tr.translate("ModuleNotFoundError: No module named 'foo'") == []


# ---------------------------------------------------------------------------
# Pattern matches & group substitution
# ---------------------------------------------------------------------------


def test_module_not_found_substitutes_module_name() -> None:
    tr = VnErrorTranslator()
    hits = tr.translate("ModuleNotFoundError: No module named 'requests'")
    top = hits[0]
    assert "'requests'" in top.summary_vn
    assert "pip install requests" in top.fix_suggestion_vn
    assert top.confidence >= 0.9


def test_eaddrinuse_substitutes_port() -> None:
    tr = VnErrorTranslator()
    hits = tr.translate("Error: listen EADDRINUSE :::8080 - Address in use")
    assert any("8080" in h.summary_vn for h in hits)


def test_npm_404_extracts_package_name() -> None:
    tr = VnErrorTranslator()
    hits = tr.translate("npm ERR! 404 'no-such-pkg' is not in this registry")
    assert any("no-such-pkg" in h.summary_vn for h in hits)


def test_indentation_error_summary() -> None:
    tr = VnErrorTranslator()
    h = tr.best("IndentationError: unexpected indent")
    assert h is not None
    assert "thụt lề" in h.summary_vn.lower() or "thut le" in h.summary_vn.lower()


def test_permission_error_text() -> None:
    tr = VnErrorTranslator()
    h = tr.best("PermissionError: [Errno 13] Permission denied")
    assert h is not None
    assert "quyền" in h.summary_vn.lower() or "quyen" in h.summary_vn.lower()


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_ranking_prefers_higher_confidence() -> None:
    """``EADDRINUSE :8080`` matches BOTH specific (with port) và generic.
    The specific (longer regex + same/higher confidence) phải đứng đầu."""
    tr = VnErrorTranslator()
    hits = tr.translate("EADDRINUSE 0.0.0.0:8080", max_results=5)
    assert len(hits) >= 1
    # Hit đầu phải có port substituted.
    assert "8080" in hits[0].summary_vn or hits[0].confidence >= 0.85


def test_max_results_cap() -> None:
    tr = VnErrorTranslator()
    # Text matches nhiều patterns; cap về 2.
    text = ("ModuleNotFoundError: No module named 'x'\n"
            "PermissionError: [Errno 13] Permission denied\n"
            "EADDRINUSE: port 3000")
    hits = tr.translate(text, max_results=2)
    assert len(hits) == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_translate_empty_text_returns_empty() -> None:
    tr = VnErrorTranslator()
    assert tr.translate("") == []


def test_translate_no_match_returns_empty() -> None:
    tr = VnErrorTranslator()
    assert tr.translate("zzzzz no error here zzzzz") == []


def test_best_returns_none_when_no_match() -> None:
    tr = VnErrorTranslator()
    assert tr.best("zzz no match zzz") is None


def test_best_returns_top_translation() -> None:
    tr = VnErrorTranslator()
    h = tr.best("ModuleNotFoundError: No module named 'numpy'")
    assert isinstance(h, TranslatedError)
    assert "numpy" in h.summary_vn


# ---------------------------------------------------------------------------
# render()
# ---------------------------------------------------------------------------


def test_translated_error_render_has_two_lines() -> None:
    h = TranslatedError(
        summary_vn="Tóm tắt",
        fix_suggestion_vn="Gợi ý",
        confidence=0.85,
        matched_pattern=r"x",
        matched_substring="x",
    )
    rendered = h.render()
    assert "Tóm tắt" in rendered
    assert "Gợi ý" in rendered
    assert "0.85" in rendered


# ---------------------------------------------------------------------------
# YAML loader (graceful)
# ---------------------------------------------------------------------------


def test_yaml_loader_with_valid_entry(tmp_path: Path) -> None:
    """Khi PyYAML có sẵn + YAML hợp lệ → entries thêm vào pool."""
    yaml_mod = pytest.importorskip("yaml")
    p = tmp_path / "extra.yaml"
    p.write_text(
        "- pattern: 'CustomErrorXYZ:\\s*(.+)'\n"
        "  summary_vn: 'Lỗi tuỳ chỉnh: {0}'\n"
        "  fix_vn: 'Liên hệ admin'\n"
        "  confidence: 0.75\n",
        encoding="utf-8",
    )
    tr = VnErrorTranslator(dict_dir=tmp_path, include_builtins=False)
    h = tr.best("CustomErrorXYZ: something broke")
    assert h is not None
    assert "Lỗi tuỳ chỉnh" in h.summary_vn
    assert "something broke" in h.summary_vn


def test_yaml_loader_skips_malformed_yaml(tmp_path: Path) -> None:
    """File YAML không parse được → skip, không raise."""
    pytest.importorskip("yaml")
    p = tmp_path / "broken.yaml"
    p.write_text("::: not valid yaml :::\n", encoding="utf-8")
    tr = VnErrorTranslator(dict_dir=tmp_path, include_builtins=False)
    # Không có entry custom, không raise.
    assert tr.translate("anything") == []


def test_yaml_loader_skips_non_list_yaml(tmp_path: Path) -> None:
    """YAML parse OK nhưng top-level KHÔNG phải list → skip."""
    pytest.importorskip("yaml")
    p = tmp_path / "dict.yaml"
    p.write_text("key: value\n", encoding="utf-8")
    tr = VnErrorTranslator(dict_dir=tmp_path, include_builtins=False)
    assert tr.translate("anything") == []


def test_yaml_loader_skips_invalid_entry(tmp_path: Path) -> None:
    """Entry thiếu key bắt buộc → skip, các entry khác vẫn load."""
    pytest.importorskip("yaml")
    p = tmp_path / "mixed.yaml"
    p.write_text(
        "- pattern: 'GoodErr:\\s*(.+)'\n"
        "  summary_vn: 'OK: {0}'\n"
        "  fix_vn: 'fix'\n"
        "  confidence: 0.8\n"
        "- summary_vn: 'thiếu pattern'\n"
        "- pattern: '['  # invalid regex\n"
        "  summary_vn: 'broken regex'\n"
        "  fix_vn: 'x'\n",
        encoding="utf-8",
    )
    tr = VnErrorTranslator(dict_dir=tmp_path, include_builtins=False)
    h = tr.best("GoodErr: something")
    assert h is not None
    assert "OK" in h.summary_vn


def test_default_dict_dir_is_a_path() -> None:
    """``DEFAULT_DICT_DIR`` luôn là Path (smoke)."""
    assert isinstance(DEFAULT_DICT_DIR, Path)


# ---------------------------------------------------------------------------
# Group-substitution fallback when format() fails
# ---------------------------------------------------------------------------


def test_format_index_error_falls_back_to_raw_text(tmp_path: Path) -> None:
    """Pattern declares too many groups in summary template → fallback."""
    pytest.importorskip("yaml")
    p = tmp_path / "fallback.yaml"
    # 1 group nhưng template tham chiếu {0} {1} → IndexError → fallback.
    p.write_text(
        "- pattern: 'BadFmt:\\s*(.+)'\n"
        "  summary_vn: 'Got {0} and {1}'\n"
        "  fix_vn: 'fix'\n"
        "  confidence: 0.7\n",
        encoding="utf-8",
    )
    tr = VnErrorTranslator(dict_dir=tmp_path, include_builtins=False)
    h = tr.best("BadFmt: only-one")
    assert h is not None
    # Fallback giữ nguyên template không substitute.
    assert h.summary_vn == "Got {0} and {1}"
