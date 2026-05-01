# Coverage matrix — OTB Budget Module

> Module × Dimension scoring final.  Mỗi cell là `(good / total =
> percent)` rút từ `evaluate_rri_t()` + `evaluate_rri_ux()` dưới
> 07/08-jsonl.  Bảng dưới đây cùng nhịp với release-gate output trong
> `10-verify-report.md` §2.

## RRI-T (correctness × stress)

| Dimension                  | Stress axes covered                                    | Good / Total | %     | Gate    |
|:---------------------------|:-------------------------------------------------------|:------------:|:-----:|:-------:|
| D1 Functional fitness      | TIME, DATA, ERROR                                      | 3 / 3        | 100   | ✅ PASS |
| D2 Performance             | TIME, DATA                                             | 2 / 2        | 100   | ✅ PASS |
| D3 Reliability             | COLLAB, INFRASTRUCTURE, ERROR, EMERGENCY               | 3 / 4        |  75   | ⚠ ≥70%  |
| D4 Security                | SECURITY (×3)                                          | 3 / 3        | 100   | ✅ PASS |
| D5 Usability               | DATA, TIME, ERROR, COLLAB                              | 3 / 4        |  75   | ⚠ ≥70%  |
| D6 Maintainability         | TIME, DATA                                             | 2 / 2        | 100   | ✅ PASS |
| D7 Compatibility           | INFRASTRUCTURE, LOCALIZATION                           | 2 / 2        | 100   | ✅ PASS |
| **Aggregate**              | **8/8 axes touched**                                   | **18 / 20**  | **90**| **PASS** |

Gate breakdown:
- Every dimension covered ≥ 1 entry: ✅
- Every dimension ≥ 70 %: ✅ (D3 = 75 %, D5 = 75 %)
- ≥ 5/7 dimensions ≥ 85 %: ✅ (5 dims at 100 %)
- 0 P0 FAIL: ✅ (1 P1 PAINFUL — D5 RRI-T-015 deferred)

## RRI-UX (flow × axes)

| Dimension                  | Axes covered                                | FLOW / Total | %     | Gate    |
|:---------------------------|:--------------------------------------------|:------------:|:-----:|:-------:|
| U1 Flow direction          | SCROLL, EYE TRAVEL, VIEWPORT                | 3 / 3        | 100   | ✅ PASS |
| U2 Click depth             | CLICK DEPTH, RETURN PATH                    | 2 / 2        | 100   | ✅ PASS |
| U3 Cognitive load          | DECISION LOAD, DATA, VIEWPORT, DECISION LOAD| 3 / 4        |  75   | ⚠ ≥70%  |
| U4 Progressive disclosure  | FEEDBACK, ERROR                             | 2 / 2        | 100   | ✅ PASS |
| U5 Return path             | RETURN PATH, DATA                           | 2 / 2        | 100   | ✅ PASS |
| U6 Feedback                | FEEDBACK, FEEDBACK, ERROR, FEEDBACK         | 3 / 4        |  75   | ⚠ ≥70%  |
| U7 VN text                 | VN TEXT (×4)                                | 4 / 4        | 100   | ✅ PASS |
| **Aggregate**              | **8/8 axes touched**                        | **19 / 21**  | **90.5**| **PASS** |

Gate breakdown:
- Every dimension covered ≥ 1 entry: ✅
- Every dimension ≥ 70 %: ✅ (U3 = 75 %, U6 = 75 %)
- ≥ 5/7 dimensions ≥ 85 %: ✅ (5 dims at 100 %)
- 0 P0 BROKEN: ✅ (2 P1 FRICTION — U3 RRI-UX-008 mobile table, U6 RRI-UX-015 timeout cancel; cả hai đã ticket Phase 1.1/2)

## Carry-forward (chưa close trước v1.0)

| ID            | Type     | Dim  | Severity | Owner          | Target  |
|:--------------|:---------|:-----|:---------|:---------------|:--------|
| RRI-T-008     | PAINFUL  | D3   | P1       | dev_finance    | 2026-Q3 |
| RRI-T-015     | PAINFUL  | D5   | P1       | fe_finance     | Phase 2 |
| RRI-UX-008    | FRICTION | U3   | P1       | fe_finance     | Phase 2 |
| RRI-UX-015    | FRICTION | U6   | P1       | fe_finance     | Phase 1.1|

## Sign-off

- QA Lead: Phạm Hà — 2026-04-09 (gate PASS)
- Architect: Vibecode AI Architect — 2026-04-09 (carry-forward accepted)
- Compliance Steward: Phạm Quang — 2026-04-09 (no P0 carry)
