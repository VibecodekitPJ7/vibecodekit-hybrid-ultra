"""Cycle 15 PR-D1 + PR-D2 — unit tests for ``design_tokens_export``.

The helper is the canonical adapter between
:mod:`vibecodekit.methodology` (single source of truth) and the
``tailwind.config.ts`` files shipped in ``assets/scaffolds/<name>/nextjs/``.
These tests pin the locked CP-XX → Tailwind token mapping and the
default FP-01 font pairing so a downstream rename gets caught early.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_tailwind_colors_returns_six_cp_tokens() -> None:
    """All 6 CP-XX entries map to a ``vck-*`` Tailwind token name."""
    from vibecodekit.design_tokens_export import tailwind_colors

    colors = tailwind_colors()
    assert len(colors) == 6
    expected = {
        "vck-trust", "vck-energy", "vck-growth",
        "vck-luxury", "vck-warning", "vck-neutral",
    }
    assert set(colors) == expected


def test_tailwind_colors_returns_methodology_hex_values() -> None:
    """Each token resolves to the HEX value declared in ``COLOR_PSYCHOLOGY``."""
    from vibecodekit import methodology as m
    from vibecodekit.design_tokens_export import tailwind_colors

    colors = tailwind_colors()
    # CP-01 is canonical Trust/Professional and pinned at #2563EB.
    assert colors["vck-trust"] == "#2563EB"
    # Spot-check the source data is the only surface — flip any HEX in
    # methodology and the helper should follow.
    cp01_hex = m.COLOR_PSYCHOLOGY["CP-01"][1]
    assert colors["vck-trust"] == cp01_hex


def test_tailwind_font_family_default_fp01() -> None:
    """Default pairing FP-01 ships Plus Jakarta Sans + Inter."""
    from vibecodekit.design_tokens_export import tailwind_font_family

    ff = tailwind_font_family()
    assert ff["heading"][0] == "Plus Jakarta Sans"
    assert ff["body"][0] == "Inter"
    # Each stack must end with a system fallback so the page still
    # renders if the web font fails to load.
    assert ff["heading"][-1] == "sans-serif"
    assert ff["body"][-1] == "sans-serif"


def test_tailwind_font_family_explicit_pairing() -> None:
    """Explicit pairing id is honoured (not silently fallbacked to FP-01)."""
    from vibecodekit import methodology as m
    from vibecodekit.design_tokens_export import tailwind_font_family

    pairing = "FP-02"  # next pairing in the methodology
    if pairing not in m.FONT_PAIRINGS:
        pytest.skip(f"{pairing} not registered in methodology")
    heading_expected, body_expected, _mood = m.FONT_PAIRINGS[pairing]
    ff = tailwind_font_family(pairing)
    assert ff["heading"][0] == heading_expected
    assert ff["body"][0] == body_expected


def test_tailwind_font_family_invalid_id_raises() -> None:
    """Unknown FP-XX ids raise ``ValueError`` (no silent fallback)."""
    from vibecodekit.design_tokens_export import tailwind_font_family

    with pytest.raises(ValueError, match="FP-99"):
        tailwind_font_family("FP-99")


def test_six_nextjs_scaffolds_wire_vck_tokens() -> None:
    """Each shipped Next.js scaffold pre-wires ≥3 ``vck-*`` Tailwind tokens.

    This is the consumer-side companion to ``tailwind_colors()`` — it
    catches the case where a future scaffold copy-paste forgets to
    populate ``theme.extend.colors`` from the methodology.
    """
    scaffolds = (
        "saas", "dashboard", "landing-page",
        "blog", "portfolio", "shop-online",
    )
    locked = (
        "vck-trust", "vck-energy", "vck-growth",
        "vck-luxury", "vck-warning", "vck-neutral",
    )
    for s in scaffolds:
        cfg = _REPO / "assets" / "scaffolds" / s / "nextjs" / "tailwind.config.ts"
        assert cfg.exists(), f"{s}: missing tailwind.config.ts"
        text = cfg.read_text(encoding="utf-8")
        token_hits = sum(1 for n in locked if n in text)
        assert token_hits >= 3, (
            f"{s}: only {token_hits}/6 vck-* tokens wired in {cfg}"
        )
        assert "heading" in text and "body" in text, (
            f"{s}: missing fontFamily heading/body in {cfg}"
        )


# ─── Cycle 15 PR-D2: tokens.json + tokens.css helpers ────────────────


def test_to_json_dict_schema_v1_shape() -> None:
    """``to_json_dict`` returns a schema-v1 envelope with all sections."""
    from vibecodekit.design_tokens_export import to_json_dict

    d = to_json_dict("0.24.0")
    assert d["$schema"] == "https://vibecodekit.dev/schemas/design-tokens-v1.json"
    assert d["version"] == "0.24.0"
    assert d["source"] == "vibecodekit.methodology"
    colors = d["colors"]
    assert isinstance(colors, dict)
    assert len(colors) == 6
    # Each colour entry preserves its CP-XX provenance.
    assert colors["vck-trust"]["cp_id"] == "CP-01"
    assert colors["vck-trust"]["hex"] == "#2563EB"
    typography = d["typography"]
    assert isinstance(typography, dict)
    assert typography["heading"]["fp_id"] == "FP-01"
    assert typography["heading"]["stack"][0] == "Plus Jakarta Sans"
    vn = d["vn_typography"]
    assert isinstance(vn, dict)
    assert vn["body_line_height"] == 1.6


def test_to_json_dict_explicit_pairing_id() -> None:
    """Caller can override pairing; helper validates it against methodology."""
    from vibecodekit import methodology as m
    from vibecodekit.design_tokens_export import to_json_dict

    pairing = "FP-02" if "FP-02" in m.FONT_PAIRINGS else "FP-01"
    d = to_json_dict("0.24.0", pairing_id=pairing)
    typography = d["typography"]
    assert isinstance(typography, dict)
    assert typography["heading"]["fp_id"] == pairing


def test_to_json_dict_invalid_pairing_raises() -> None:
    """Unknown pairing id surfaces immediately, no silent FP-01 fallback."""
    import pytest as _pytest

    from vibecodekit.design_tokens_export import to_json_dict

    with _pytest.raises(ValueError, match="FP-99"):
        to_json_dict("0.24.0", pairing_id="FP-99")


def test_to_css_variables_root_block_contract() -> None:
    """``to_css_variables`` ships ``:root`` with all 6 colour CSS vars + fonts."""
    from vibecodekit.design_tokens_export import to_css_variables

    css = to_css_variables()
    assert ":root {" in css
    assert css.rstrip().endswith("}")
    for token in (
        "--vck-trust", "--vck-energy", "--vck-growth",
        "--vck-luxury", "--vck-warning", "--vck-neutral",
        "--vck-font-heading", "--vck-font-body",
        "--vck-line-height-body", "--vck-line-height-heading",
    ):
        assert token in css, f"missing CSS var {token}"
    # Multi-word font name must be quoted (CSS spec).
    assert '"Plus Jakarta Sans"' in css


def test_six_nextjs_scaffolds_ship_design_tokens_files() -> None:
    """Every Next.js scaffold has ``design/tokens.json`` + ``design/tokens.css``."""
    import json as _json

    scaffolds = (
        "saas", "dashboard", "landing-page",
        "blog", "portfolio", "shop-online",
    )
    for s in scaffolds:
        base = _REPO / "assets" / "scaffolds" / s / "nextjs" / "design"
        json_p = base / "tokens.json"
        css_p = base / "tokens.css"
        assert json_p.exists(), f"{s}: tokens.json missing"
        assert css_p.exists(), f"{s}: tokens.css missing"
        data = _json.loads(json_p.read_text(encoding="utf-8"))
        assert "design-tokens-v1" in data["$schema"]
        assert len(data["colors"]) == 6
        css = css_p.read_text(encoding="utf-8")
        assert "--vck-trust" in css
        assert ":root" in css


def test_six_nextjs_manifests_register_design_tokens() -> None:
    """Each manifest declares the new design tokens files in ``files[]``
    and ``success_criteria[]`` so ``vibe scaffold apply`` actually copies
    them and ``vibe scaffold verify`` actually checks them."""
    import json as _json

    scaffolds = (
        "saas", "dashboard", "landing-page",
        "blog", "portfolio", "shop-online",
    )
    expected_files = ("design/tokens.json", "design/tokens.css")
    expected_crits = ("design/tokens.json exists", "design/tokens.css exists")
    for s in scaffolds:
        manifest = _json.loads(
            (_REPO / "assets" / "scaffolds" / s / "manifest.json")
            .read_text(encoding="utf-8")
        )
        spec = manifest["stacks"]["nextjs"]
        for f in expected_files:
            assert f in spec["files"], f"{s}: manifest.files missing {f}"
        for c in expected_crits:
            assert c in spec["success_criteria"], (
                f"{s}: manifest.success_criteria missing {c!r}"
            )


# ─── Cycle 15 PR-D3: shadcn-style sample component library ───────────


def test_two_scaffolds_ship_three_components_each() -> None:
    """saas + dashboard each ship Button + Input + Card under components/ui/."""
    components = ("button.tsx", "input.tsx", "card.tsx")
    for s in ("saas", "dashboard"):
        for c in components:
            f = _REPO / "assets" / "scaffolds" / s / "nextjs" / "components" / "ui" / c
            assert f.exists(), f"{s}/components/ui/{c} missing"
            text = f.read_text(encoding="utf-8")
            assert "vck-" in text, f"{s}/{c}: no vck-* token reference"
            assert 'from "@/lib/cn"' in text, (
                f"{s}/{c}: missing cn() helper import"
            )


def test_two_scaffolds_ship_cn_helper() -> None:
    """saas + dashboard each ship lib/cn.ts pulling clsx + tailwind-merge."""
    for s in ("saas", "dashboard"):
        cn_path = _REPO / "assets" / "scaffolds" / s / "nextjs" / "lib" / "cn.ts"
        assert cn_path.exists(), f"{s}/lib/cn.ts missing"
        text = cn_path.read_text(encoding="utf-8")
        assert 'from "clsx"' in text
        assert 'from "tailwind-merge"' in text
        assert "export function cn" in text


def test_two_manifests_register_component_files() -> None:
    """Manifest declares the 4 new component-library files + new criteria."""
    import json as _json

    expected_files = (
        "lib/cn.ts",
        "components/ui/button.tsx",
        "components/ui/input.tsx",
        "components/ui/card.tsx",
    )
    for s in ("saas", "dashboard"):
        manifest = _json.loads(
            (_REPO / "assets" / "scaffolds" / s / "manifest.json")
            .read_text(encoding="utf-8")
        )
        spec = manifest["stacks"]["nextjs"]
        for f in expected_files:
            assert f in spec["files"], f"{s}: manifest.files missing {f}"


def test_two_scaffolds_pin_clsx_and_tailwind_merge_deps() -> None:
    """package.json adds clsx + tailwind-merge so cn() helper resolves."""
    import json as _json

    for s in ("saas", "dashboard"):
        pkg = _json.loads(
            (_REPO / "assets" / "scaffolds" / s / "nextjs" / "package.json")
            .read_text(encoding="utf-8")
        )
        deps = pkg.get("dependencies", {})
        assert "clsx" in deps, f"{s}: missing clsx in dependencies"
        assert "tailwind-merge" in deps, (
            f"{s}: missing tailwind-merge in dependencies"
        )


def test_component_library_pattern_doc_exists() -> None:
    """References include the component-library-pattern doc (cycle 15 PR-D3)."""
    doc = _REPO / "references" / "41-component-library-pattern.md"
    assert doc.exists(), "missing references/41-component-library-pattern.md"
    text = doc.read_text(encoding="utf-8")
    # Doc must cover the 3 base components + cn() + anti-patterns.
    for needle in ("Button", "Input", "Card", "cn()", "vck-", "anti-pattern"):
        assert needle.lower() in text.lower(), (
            f"doc missing required topic: {needle!r}"
        )
