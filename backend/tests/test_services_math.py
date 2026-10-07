"""Pure-function tests: price audit spike math, reorder points, number parsing."""

import pytest

from app.services import price_audit
from app.services.inventory import is_low_stock, reorder_point
from app.services.number_format import parse_indonesian_number


class TestPriceAudit:
    def test_spike_detected_over_threshold(self) -> None:
        result = price_audit.audit_line_item(
            ingredient_name="Cabai Merah",
            quantity=2.0,
            unit="kg",
            unit_price=52_000.0,
            price_history=[44_000.0, 44_000.0, 43_500.0],
        )
        assert result["is_spike"] is True
        assert result["spike_pct"] == pytest.approx((52_000 - 43_833.33) / 43_833.33 * 100, rel=0.01)

    def test_no_spike_within_threshold(self) -> None:
        result = price_audit.audit_line_item(
            ingredient_name="Beras",
            quantity=50.0,
            unit="kg",
            unit_price=14_200.0,
            price_history=[13_900.0, 13_950.0],
        )
        assert result["is_spike"] is False

    def test_price_drop_is_not_a_spike(self) -> None:
        result = price_audit.audit_line_item(
            ingredient_name="Minyak",
            quantity=20.0,
            unit="L",
            unit_price=17_500.0,
            price_history=[19_500.0, 19_000.0],
        )
        assert result["is_spike"] is False
        assert result["spike_pct"] < 0

    def test_empty_history_cannot_spike(self) -> None:
        result = price_audit.audit_line_item(
            ingredient_name="New Item",
            quantity=1.0,
            unit="kg",
            unit_price=99_999.0,
            price_history=None,
        )
        assert result["is_spike"] is False
        assert result["spike_pct"] == 0

    def test_spike_percentage_pure_math(self) -> None:
        assert price_audit.spike_percentage(110.0, [100.0]) == pytest.approx(10.0)
        assert price_audit.spike_percentage(100.0, [100.0]) == 0


class TestInventory:
    def test_reorder_point_formula(self) -> None:
        assert reorder_point(avg_daily_usage=2.0, lead_time_days=3, safety_days=2) == 10.0
        assert reorder_point(avg_daily_usage=0.5, lead_time_days=1) == 1.5

    def test_low_stock_inclusive_boundary(self) -> None:
        assert is_low_stock(current_stock=5.0, reorder_point_value=5.0) is True
        assert is_low_stock(current_stock=5.1, reorder_point_value=5.0) is False


class TestIndonesianNumbers:
    def test_thousands_with_decimal_comma(self) -> None:
        assert parse_indonesian_number("1.234,5") == pytest.approx(1234.5)

    def test_dot_thousands(self) -> None:
        assert parse_indonesian_number("12.500") == pytest.approx(12_500.0)
        assert parse_indonesian_number("1.234.567") == pytest.approx(1_234_567.0)

    def test_decimal_comma(self) -> None:
        assert parse_indonesian_number("2,5") == pytest.approx(2.5)

    def test_plain_numbers(self) -> None:
        assert parse_indonesian_number("22000") == 22_000.0
        assert parse_indonesian_number("12.5") == pytest.approx(12.5)  # single non-thousands dot

    def test_invalid_inputs_raise(self) -> None:
        for bad in ("", "abc", "1,2,3"):
            with pytest.raises(ValueError):
                parse_indonesian_number(bad)
