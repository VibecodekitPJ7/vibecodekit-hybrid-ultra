"""CI guard: drift guard không có cơ chế env-gated bypass.

Cycle 6 commit (xem ``CHANGELOG.md`` Unreleased): canonical org
``VibecodekitPJ6`` lock PERMANENT, và anti-pattern
``CANONICAL_ORG_STRICT=false`` env bypass đã bị xoá khỏi
``.github/workflows/ci.yml``.

Nếu PR sau vô tình tái thêm cơ chế bypass (env var, repo variable,
secret toggle), test này fail — buộc reviewer cân nhắc lại trước khi
relax security boundary.
"""
from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _ci_yml_text() -> str:
    return _CI_YML.read_text(encoding="utf-8")


def test_allowed_orgs_contains_pj6():
    """``ALLOWED_ORGS`` phải chứa ``VibecodekitPJ6`` (canonical permanent)."""
    from tests.test_repo_urls_canonical import ALLOWED_ORGS

    assert "VibecodekitPJ6" in ALLOWED_ORGS, (
        "ALLOWED_ORGS không còn chứa 'VibecodekitPJ6' — canonical org "
        "đã rebrand lần thứ 9?  Cycle 6 đã commit PJ6 PERMANENT; nếu "
        "thực sự cần đổi, mở PR riêng và cập nhật cả "
        "tests/test_canonical_org_no_bypass.py + CHANGELOG."
    )


def test_ci_yml_no_env_bypass_for_canonical_org():
    """``.github/workflows/ci.yml`` KHÔNG được chứa cơ chế bypass.

    Anti-pattern bị cấm: ``CANONICAL_ORG_STRICT`` env var hoặc
    ``vars.CANONICAL_ORG`` repo variable.  Lý do: quy tắc tự tắt được
    qua repo settings không phải quy tắc — fork CI phải tự sync
    ``ALLOWED_ORGS`` hoặc skip suite riêng.
    """
    text = _ci_yml_text()
    forbidden = ("CANONICAL_ORG_STRICT", "vars.CANONICAL_ORG")
    found = [tok for tok in forbidden if tok in text]
    assert not found, (
        ".github/workflows/ci.yml chứa cơ chế bypass đã bị cấm: "
        f"{found}.  Xem CHANGELOG Unreleased / SECURITY.md cho lý do "
        "loại bỏ env-gated bypass.  Fork CI phải sync ALLOWED_ORGS, "
        "không bypass guard."
    )


def test_ci_yml_references_pj6():
    """``.github/workflows/ci.yml`` phải reference ``VibecodekitPJ6``
    (assertion cứng cho canonical owner)."""
    text = _ci_yml_text()
    assert "VibecodekitPJ6" in text, (
        ".github/workflows/ci.yml không còn reference 'VibecodekitPJ6' — "
        "drift guard có vẻ đã bị xoá hoặc đổi canonical org ngầm.  "
        "Cycle 6 commit: PJ6 là canonical PERMANENT."
    )
