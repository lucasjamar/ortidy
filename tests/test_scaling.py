"""Unit tests for the float→int unit-scaling layer."""

from __future__ import annotations

from ortidy import _scaling


def test_integral_values_keep_factor_one():
    scaled, factor = _scaling.scale_to_int([1, 2, 3])
    assert factor == 1
    assert scaled == [1, 2, 3]


def test_floats_are_scaled_losslessly():
    scaled, factor = _scaling.scale_to_int([0.1, 0.25, 1.5])
    assert factor == 100
    assert scaled == [10, 25, 150]


def test_choose_factor_caps_at_max():
    # An irrational-ish value cannot be made integral; factor caps out.
    factor = _scaling.choose_factor([0.123456789], max_factor=1000)
    assert factor == 1000


def test_unscale_roundtrip():
    scaled, factor = _scaling.scale_to_int([2.5])
    assert _scaling.unscale(scaled[0], factor) == 2.5
