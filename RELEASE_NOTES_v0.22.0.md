# VibecodeKit Hybrid Ultra v0.22.0 — Documentation expansion (cycle 13)

**Release date**: 2026-05-01
**Type**: Documentation expansion (minor bump)
**Backward compat**: 100% — no breaking changes, no API surface change, no runtime behaviour change.

## Highlights

Cycle 13 thuần documentation polish — đáp ứng 3 follow-up gap được
ghi nhận sau cycle 12 release: case study end-to-end, anti-pattern
visual catalog, color/font appendix.

| Cycle 13 PR | Scope                                                  | Probes | Tests added |
|:------------|:-------------------------------------------------------|:------:|:-----------:|
| PR1 #1      | Pre-baked case study `references/examples/01-otb-budget-module/` (11 file) | +1 (#88) | +16  |
| PR2 #2      | Anti-pattern gallery 12 AP-01..AP-12 visualization     | +1 (#89) | +40  |
| PR3 (this)  | Color psychology + Font pairing appendix + bump        | +2 (#90, #91) | +24  |

> Lưu ý: spec ban đầu nhắm 90/90 với "3 probe mới"; trong quá trình
> implement chốt 4 probe (mỗi artifact 1 probe — case study, anti-pattern
> gallery, color appendix, font appendix) để giữ behaviour-based check
> dày → final 91/91 thay vì 90/90.  Chấp nhận trade-off probe count
> tăng 1 đổi lấy guard chặt hơn.

Tổng cộng: **+3 documentation file mới** (reference 37, 38; gallery)
**+1 case-study folder** (11 file), **+4 conformance probe**, **+~80 test**.

## Numbers

| Metric                 | v0.21.0       | v0.22.0          | Δ                |
|:-----------------------|:--------------|:-----------------|:-----------------|
| Tests pass             | 1615 / 9 skip | **1695** / 9 skip | **+80**          |
| Conformance probes     | 87/87 met     | **91/91 met**    | +4               |
| Coverage TOTAL         | 90%           | **≥ 90%**        | giữ nguyên        |
| mypy strict (9 module) | 0 errors      | 0 errors         | =                |
| Ruff F401/F841/F811    | clean         | clean            | =                |
| Demo speed             | ~1.27 s       | ≤ 1.5 s          | ~                |
| Reference docs         | 18            | **21**           | +3 (37, 38, gallery) |
| Examples folder        | 0             | **1**            | +1 (OTB Budget)  |
| Release notes archive  | 5             | **6**            | +1 (this file)   |

## Files added (cycle 13 cumulative)

```
references/
├── 37-color-psychology.md             # PR3 — 7 industry palettes + WCAG + VN cultural
├── 38-font-pairing.md                 # PR3 — 5 use-case stacks + VN subset + scale
└── anti-patterns-gallery.md            # PR2 — 12 AP-XX với BAD/GOOD viz + recipe + detector

references/examples/01-otb-budget-module/   # PR1 — 11 file end-to-end case study
├── README.md, 00-scan-report.md
├── 01-rri-requirements.md, 02-vision.md, 03-blueprint.md
├── 04-task-graph.md
├── 05-tips/{tip-001,002,003}-spec.md
├── 06-completion-reports/{tip-001,002,003}-report.md
├── 07-rri-t-results.jsonl, 08-rri-ux-results.jsonl
├── 09-coverage-matrix.md, 10-verify-report.md

scripts/vibecodekit/conformance_audit.py    # +4 probe wired (88, 89, 90, 91)
tests/test_case_study_otb_budget.py          # PR1 +16
tests/test_anti_patterns_gallery.py          # PR2 +40
tests/test_color_psychology_appendix.py      # PR3 +12
tests/test_font_pairing_appendix.py          # PR3 +12

VERSION                                      # 0.21.0 → 0.22.0
CHANGELOG.md                                 # +entry [0.22.0]
BENCHMARKS-METHODOLOGY.md                    # +Phase 7 doc-expansion entry
RELEASE_NOTES_v0.22.0.md                     # this file
```

## API surface

**Không thay đổi.**

`methodology.__all__` giữ nguyên 100 % với v0.21.0.  Tất cả runtime
module trong `scripts/vibecodekit/` không touch — cycle 13 chỉ
thêm 3 probe (file `conformance_audit.py`) + 4 test file mới + 14
documentation file.

## Upgrade guide

```bash
pip install --upgrade vibecodekit-hybrid-ultra==0.22.0
# hoặc reproducible:
uv sync --frozen
```

KHÔNG breaking change.  KHÔNG migration cần.

## Verify locally

```bash
git pull origin main
git checkout v0.22.0     # tag

# Tests
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m pytest tests -q -p no:warnings | tail -3
# → 1695 pass / 9 skip

# Conformance
PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit --threshold 1.0 | tail -3
# → parity: 100.00%   (91/91, threshold 100%)

# Ruff
python3 -m ruff check scripts/vibecodekit examples --select F401,F841,F811
# → All checks passed

# Mypy strict (9 core modules)
PYTHONPATH=./scripts python3 -m mypy --strict \
  scripts/vibecodekit/{permission_engine,scaffold_engine,verb_router,denial_store,_audit_log,tool_executor,team_mode,task_runtime,subagent_runtime}.py
# → Success: no issues found in 9 source files
```

## What's next (post-v0.22.0)

- Optional v0.22.x patches: thêm AP-13+ vào gallery khi mới phát hiện.
- v0.23.0+ candidates: schema-driven RRI-T runner (replace jsonl với DSL),
  expand case study folder lên 3-5 modules (CRM, POS, HRM).
- Không có breaking change planned trong v0.x line.

## Acknowledgments

- Cycle 13 là 100 % documentation-only — KHÔNG touch core runtime,
  KHÔNG bump major.
- Cảm ơn các reviewer đã nhặt nits trên PR Devin Review (cycle 12 PR3 follow-up #18 pattern).
