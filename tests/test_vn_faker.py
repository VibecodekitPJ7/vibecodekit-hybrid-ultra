"""Cycle 7 PR2 — coverage Phase 2 cho ``vn_faker.VnFaker``.

Mục tiêu: 0% → ≥80%.  Test nội dung:

* Determinism — cùng seed cho cùng output (snapshot).
* Mỗi method public phải trả định dạng đúng (regex match).
* Edge cases: empty gender, swapped vnd_amount range.
* CCCD layout (12 ký tự, prefix tỉnh, gender_century).
"""
from __future__ import annotations

import re

import pytest

from vibecodekit.vn_faker import VnFaker


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_seed_same_name() -> None:
    a = VnFaker(seed=42)
    b = VnFaker(seed=42)
    names_a = [a.name() for _ in range(10)]
    names_b = [b.name() for _ in range(10)]
    assert names_a == names_b


def test_different_seed_different_output() -> None:
    a = VnFaker(seed=1)
    b = VnFaker(seed=2)
    # Highly unlikely to collide on first call across two seeds.
    assert a.name() != b.name() or a.phone() != b.phone()


# ---------------------------------------------------------------------------
# name() — gender flag
# ---------------------------------------------------------------------------


def test_name_default_any_gender() -> None:
    f = VnFaker(seed=7)
    name = f.name()
    parts = name.split()
    assert len(parts) == 3
    # Family name must come from the canonical list.
    assert parts[0] in {
        "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan",
        "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương",
        "Lý", "Đào", "Đoàn", "Vương", "Trịnh",
    }


def test_name_male_uses_male_middle() -> None:
    f = VnFaker(seed=7)
    male_middles = {"Văn", "Hữu", "Quang", "Minh", "Đức", "Anh",
                    "Thành", "Quốc", "Tuấn", "Bảo"}
    for _ in range(20):
        parts = f.name(gender="male").split()
        assert parts[1] in male_middles


def test_name_female_uses_female_middle() -> None:
    f = VnFaker(seed=7)
    female_middles = {"Thị", "Thu", "Ngọc", "Bích", "Diệu", "Thanh",
                      "Hồng", "Phương", "Như", "Khánh"}
    for _ in range(20):
        parts = f.name(gender="female").split()
        assert parts[1] in female_middles


def test_name_any_gender_produces_both_branches() -> None:
    """``gender='any'`` random-flips between male/female pool."""
    f = VnFaker(seed=0)
    seen_m = seen_f = False
    male_middles = {"Văn", "Hữu", "Quang", "Minh", "Đức", "Anh",
                    "Thành", "Quốc", "Tuấn", "Bảo"}
    female_middles = {"Thị", "Thu", "Ngọc", "Bích", "Diệu", "Thanh",
                      "Hồng", "Phương", "Như", "Khánh"}
    for _ in range(50):
        m = f.name(gender="any").split()[1]
        if m in male_middles:
            seen_m = True
        elif m in female_middles:
            seen_f = True
        if seen_m and seen_f:
            break
    assert seen_m and seen_f


# ---------------------------------------------------------------------------
# phone()
# ---------------------------------------------------------------------------


_LOCAL_PHONE_RE = re.compile(r"^0\d{3}\.\d{6}$")
_INTL_PHONE_RE = re.compile(r"^\+84\d{9}$")


def test_phone_local_format() -> None:
    f = VnFaker(seed=11)
    for _ in range(20):
        n = f.phone()
        assert _LOCAL_PHONE_RE.match(n), n


def test_phone_international_format() -> None:
    f = VnFaker(seed=11)
    for _ in range(20):
        n = f.phone(international=True)
        assert _INTL_PHONE_RE.match(n), n


# ---------------------------------------------------------------------------
# address / province
# ---------------------------------------------------------------------------


def test_address_format() -> None:
    f = VnFaker(seed=3)
    addr = f.address()
    # Layout: "Số {n} {street}, {district}, {province}"
    assert addr.startswith("Số ")
    parts = [p.strip() for p in addr.split(",")]
    assert len(parts) == 3


def test_province_is_known() -> None:
    f = VnFaker(seed=3)
    known = {
        "Hà Nội", "Thành phố Hồ Chí Minh", "Hải Phòng", "Đà Nẵng",
        "Cần Thơ", "Hà Tĩnh", "Hưng Yên", "Thái Nguyên", "Khánh Hòa",
        "Đắk Lắk", "Đồng Nai", "Bà Rịa - Vũng Tàu",
    }
    for _ in range(20):
        assert f.province() in known


def test_address_default_districts_path() -> None:
    """Provinces NOT trong ``_DISTRICTS_BY_PROVINCE`` → fallback districts."""
    f = VnFaker(seed=12345)
    default = {"Trung tâm", "Đông", "Tây", "Nam", "Bắc"}
    # Lặp đủ lần để chạm fallback path ít nhất 1 lần.
    saw_default = False
    for _ in range(100):
        addr = f.address()
        district = addr.split(",")[1].strip()
        if district in default:
            saw_default = True
            break
    assert saw_default, "expected fallback districts path to fire"


# ---------------------------------------------------------------------------
# cccd()
# ---------------------------------------------------------------------------


_CCCD_RE = re.compile(r"^\d{12}$")


def test_cccd_layout() -> None:
    f = VnFaker(seed=8)
    for _ in range(20):
        c = f.cccd()
        assert _CCCD_RE.match(c), c
        # Province prefix (3 digits) phải nằm trong table.
        prefix = c[:3]
        assert prefix in {"001", "079", "031", "048", "092", "038",
                           "033", "019", "056", "066", "075", "077"}
        # Gender+century digit
        assert c[3] in "0123"


def test_cccd_century_year_branches() -> None:
    """Both 1900s và 2000s code path phải reachable."""
    f = VnFaker(seed=99)
    seen_19 = seen_20 = False
    for _ in range(50):
        c = f.cccd()
        if c[3] in "01":
            seen_19 = True
        else:
            seen_20 = True
        if seen_19 and seen_20:
            break
    assert seen_19 and seen_20


# ---------------------------------------------------------------------------
# bank_account
# ---------------------------------------------------------------------------


def test_bank_account_format() -> None:
    f = VnFaker(seed=21)
    valid_prefixes = {"VCB", "TCB", "MB", "ACB", "BID", "VPB",
                      "STB", "TPB"}
    for _ in range(30):
        acc = f.bank_account()
        assert "-" in acc
        prefix, digits = acc.split("-")
        assert prefix in valid_prefixes
        assert digits.isdigit()
        # Length theo bank table (12-14)
        assert 12 <= len(digits) <= 14


# ---------------------------------------------------------------------------
# vnd_amount
# ---------------------------------------------------------------------------


def test_vnd_amount_format() -> None:
    f = VnFaker(seed=4)
    s = f.vnd_amount()
    assert s.endswith("đ")
    # Phần số phải dùng dấu "." làm thousands separator
    body = s[:-1]
    assert "," not in body


def test_vnd_amount_round_to() -> None:
    f = VnFaker(seed=4)
    for _ in range(10):
        s = f.vnd_amount(round_to=10_000)
        # Bỏ "đ" + dấu "." → integer chia hết cho 10_000.
        n = int(s[:-1].replace(".", ""))
        assert n % 10_000 == 0


def test_vnd_amount_swapped_min_max_normalised() -> None:
    """Khi min > max, generator phải swap thay vì raise."""
    f = VnFaker(seed=4)
    s = f.vnd_amount(min_amount=100_000, max_amount=10_000)
    assert s.endswith("đ")


# ---------------------------------------------------------------------------
# company / email
# ---------------------------------------------------------------------------


def test_company_starts_with_company_type() -> None:
    f = VnFaker(seed=33)
    for _ in range(10):
        c = f.company()
        assert c.startswith(("Công ty TNHH", "Công ty Cổ phần",
                              "Công ty TNHH MTV"))


def test_email_format() -> None:
    f = VnFaker(seed=5)
    e = f.email()
    assert "@" in e
    local, domain = e.split("@", 1)
    assert domain in {"gmail.com", "yahoo.com", "outlook.com"}
    # 2-digit suffix
    assert local[-2:].isdigit()


def test_email_with_full_name_strips_diacritics() -> None:
    f = VnFaker(seed=5)
    e = f.email(full_name="Nguyễn Văn Đức")
    local = e.split("@")[0]
    # All letters before suffix must be ASCII.
    body = local[:-2]
    assert all(ord(c) < 128 for c in body), body
    assert "." in body


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def test_strip_diacritics_preserves_case() -> None:
    f = VnFaker._strip_diacritics  # static method
    assert f("Đức") == "Duc"
    assert f("đức") == "duc"
    assert f("Không-Có-Dấu") == "Khong-Co-Dau"


def test_format_vnd_separator() -> None:
    assert VnFaker._format_vnd(1_500_000) == "1.500.000đ"
    assert VnFaker._format_vnd(0) == "0đ"
    assert VnFaker._format_vnd(999) == "999đ"


def test_address_str_has_three_parts() -> None:
    """``_Address.__str__`` smoke."""
    from vibecodekit.vn_faker import _Address  # type: ignore[attr-defined]
    a = _Address(12, "Lê Lợi", "Hoàn Kiếm", "Hà Nội")
    s = str(a)
    assert s == "Số 12 Lê Lợi, Hoàn Kiếm, Hà Nội"
