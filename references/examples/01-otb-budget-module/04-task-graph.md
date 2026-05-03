# Task graph — OTB Budget Module

> DAG of TIPs.  Mỗi node = 1 TIP = 1 mergeable PR.  Edge = "must merge
> before".  Critical path tô đậm.

## ASCII DAG

```
                       ┌──────────────────────┐
                       │ TIP-001 Schema +     │   (~120 min, Class 2)
                       │ Alembic migration    │
                       └──────────┬───────────┘
                                  │
                  ┌───────────────┼────────────────────────────┐
                  ▼               ▼                            ▼
       ┌──────────────────┐  ┌─────────────────┐  ┌────────────────────────┐
       │ TIP-002 Service +│  │ TIP-004 Tết     │  │ TIP-005 Frontend       │
       │ optimistic lock  │  │ freeze + flag   │  │ pages (plan/approve/   │
       │ (~180m, Class 3) │  │ (~60m, Class 1) │  │ history) (~180m, C3)   │
       └─────────┬────────┘  └────────┬────────┘  └────────────┬───────────┘
                 │                    │                        │
                 └─────┬──────────────┘                        │
                       ▼                                       │
              ┌──────────────────┐                             │
              │ TIP-003 API      │◄────────────────────────────┘
              │ endpoints        │   (frontend hits these)
              │ (~120m, Class 2) │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ TIP-006 PWA      │
              │ offline banner   │   (~60m, Class 1)
              │                  │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │ TIP-007 RRI-T +  │   (~120m, Class 1)
              │ RRI-UX runs      │   ⇒ feed 07-rri-t-results.jsonl
              │                  │   ⇒ feed 08-rri-ux-results.jsonl
              └──────────────────┘
```

## Critical path

`TIP-001 → TIP-002 → TIP-003 → TIP-006 → TIP-007` ≈ 600 min (10 h) sequential.
TIP-004 và TIP-005 chạy song song với TIP-002/TIP-003 nếu đủ owner.

## Edges + reasoning

| Edge                                  | Why                                                                  |
|:--------------------------------------|:---------------------------------------------------------------------|
| TIP-001 → TIP-002                     | Service cần models + table tồn tại                                    |
| TIP-001 → TIP-004                     | `feature_flag` table đã có (reuse), nhưng `tet_calendar` cần seed     |
| TIP-001 → TIP-005                     | Frontend type-gen cần OpenAPI từ models (sau TIP-001 + TIP-003)       |
| TIP-002 + TIP-004 → TIP-003           | API gọi service với Tết check                                         |
| TIP-003 + TIP-005 → TIP-006           | PWA banner cần cả backend (status check) lẫn FE pages                 |
| TIP-006 → TIP-007                     | RRI-T/UX run trên end-to-end app, sau khi cả FE/BE PWA ready          |

## Risk class summary

| Class | TIPs               | Rule                                                  |
|:-----:|:-------------------|:------------------------------------------------------|
|   1   | TIP-004, 006, 007  | Read-only / additive — auto-merge nếu CI pass + 1 LGTM|
|   2   | TIP-001, 003       | Schema-compatible mutation — 1 LGTM + Compliance LGTM |
|   3   | TIP-002, 005       | Behaviour change — Security Auditor sign-off          |

## Replay note

Trong case study này chỉ ship completion-report cho 3 TIP đại diện
(`TIP-001`, `TIP-002`, `TIP-003`) để minh hoạ Class 1/2/3.  Các TIP còn
lại (004-007) reuse cùng template và đã merge production trước khi
case study được archive.
