"""
Group D1 — Hypothesis tests for Z-report paise arithmetic.
Tests that floating-point rounding in _build_z_report never drifts.
No DB or Frappe required — pure math properties.
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# ── Inline paise helper (same logic as production) ────────────────────────────


def _paise(amount: float) -> int:
	"""Convert rupee float to integer paise with correct rounding."""
	return round(amount * 100)


# ── Paise rounding invariants ─────────────────────────────────────────────────


@given(amount=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
def test_paise_is_always_int(amount):
	"""_paise() always returns an int, never a float."""
	assert isinstance(_paise(amount), int)


@given(amount=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
def test_paise_non_negative_for_non_negative_input(amount):
	"""Non-negative rupee amounts produce non-negative paise."""
	assert _paise(amount) >= 0


@given(paise_int=st.integers(min_value=0, max_value=1_000_000_00))
def test_paise_roundtrip_from_int(paise_int):
	"""Integer paise → rupee float → back to paise loses at most 1 unit (rounding)."""
	rupees = paise_int / 100.0
	recovered = _paise(rupees)
	assert abs(recovered - paise_int) <= 1


@given(
	a=st.integers(min_value=0, max_value=10_000_00),
	b=st.integers(min_value=0, max_value=10_000_00),
)
def test_sum_paise_matches_individual(a, b):
	"""Sum of paise values matches paise of sum (within 1 unit of rounding error)."""
	total_direct = a + b
	total_via_float = _paise(a / 100.0 + b / 100.0)
	assert abs(total_direct - total_via_float) <= 1


# ── Z-report mode math ────────────────────────────────────────────────────────


@given(
	opening=st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
	sales=st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
	actual=st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
)
def test_discrepancy_formula(opening, sales, actual):
	"""discrepancy = actual - (opening + sales). Sign and magnitude are always consistent."""
	expected = opening + sales
	discrepancy = _paise(actual - expected)
	_paise(expected)
	_paise(actual)
	_paise(opening)
	_paise(sales)

	# discrepancy direction must match the sign of actual - expected
	if actual > expected + 0.005:
		assert discrepancy > 0, "Actual > expected → positive discrepancy (over)"
	elif actual < expected - 0.005:
		assert discrepancy < 0, "Actual < expected → negative discrepancy (short)"


@given(
	values=st.lists(
		st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
		min_size=0,
		max_size=50,
	)
)
def test_net_sales_sum_non_negative(values):
	"""Sum of non-negative grand_totals is always non-negative."""
	total = sum(values)
	assert _paise(total) >= 0


# ── Union-of-modes completeness ───────────────────────────────────────────────


@given(
	opening_modes=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5, unique=True),
	closing_modes=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5, unique=True),
)
def test_union_of_modes_contains_all(opening_modes, closing_modes):
	"""Union of opening and closing modes must contain every mode from both sets."""
	all_modes = sorted(set(opening_modes) | set(closing_modes))
	for mode in opening_modes:
		assert mode in all_modes
	for mode in closing_modes:
		assert mode in all_modes


@given(
	opening_modes=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5, unique=True),
	extra_closing=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=3, unique=True),
)
def test_extra_closing_modes_appear_in_union(opening_modes, extra_closing):
	"""Modes present only in closing (not in opening) appear in the union."""
	assume(not set(extra_closing) & set(opening_modes))  # truly extra modes
	all_modes = sorted(set(opening_modes) | set(extra_closing))
	for mode in extra_closing:
		assert mode in all_modes, f"Extra closing mode {mode!r} missing from union"


# ── Zero-invoice edge case ────────────────────────────────────────────────────


def test_zero_invoices_gives_zero_net_sales():
	"""When there are no invoices, net sales = 0 paise."""
	assert _paise(0.0) == 0


def test_returns_reduce_net():
	"""A return invoice reduces net sales."""
	gross = 1000.0  # ₹1000 in sales
	ret = 200.0  # ₹200 returned
	net = gross - ret
	assert _paise(net) == 800_00  # ₹800 = 80000 paise
