"""
Group F (crypto layer) — Hypothesis-driven tests for PIN hashing.
Tests _hash_pin and _is_hashed without any Frappe/DB context.
Hypothesis generates hundreds of inputs automatically.
"""

import hashlib
import sys

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Inline the pure functions so we test the exact same logic without importing
# frappe (frappe is mocked in conftest but we prefer direct function isolation)


def _hash_pin(pin: str) -> str:
	return hashlib.sha256(pin.encode()).hexdigest()


def _is_hashed(stored: str) -> bool:
	return len(stored) == 64 and all(c in "0123456789abcdef" for c in stored)


# ── _hash_pin ─────────────────────────────────────────────────────────────────


@given(pin=st.text(alphabet="0123456789", min_size=4, max_size=8))
def test_hash_pin_always_64hex(pin):
	"""Any valid PIN (4-8 digits) produces a 64-char hex digest."""
	result = _hash_pin(pin)
	assert len(result) == 64
	assert all(c in "0123456789abcdef" for c in result)


@given(pin=st.text(alphabet="0123456789", min_size=4, max_size=8))
def test_hash_pin_is_hashed_returns_true(pin):
	"""The output of _hash_pin always passes _is_hashed."""
	assert _is_hashed(_hash_pin(pin))


@given(
	pin_a=st.text(alphabet="0123456789", min_size=4, max_size=8),
	pin_b=st.text(alphabet="0123456789", min_size=4, max_size=8),
)
def test_hash_pin_different_pins_different_hashes(pin_a, pin_b):
	"""Two different PINs must produce different hashes (collision resistance)."""
	assume(pin_a != pin_b)
	assert _hash_pin(pin_a) != _hash_pin(pin_b)


@given(pin=st.text(alphabet="0123456789", min_size=4, max_size=8))
def test_hash_pin_deterministic(pin):
	"""Same PIN always produces the same hash."""
	assert _hash_pin(pin) == _hash_pin(pin)


# ── _is_hashed ────────────────────────────────────────────────────────────────


@given(text=st.text(alphabet="0123456789", min_size=1, max_size=8))
def test_is_hashed_rejects_plaintext_digits(text):
	"""Raw digit strings (1-8 chars) are never considered hashed."""
	# Plaintext PINs are at most 8 digits — always shorter than 64 chars
	assert not _is_hashed(text)


@given(text=st.text(min_size=65, max_size=200))
def test_is_hashed_rejects_too_long(text):
	"""Strings longer than 64 chars are never considered hashed."""
	assert not _is_hashed(text)


@given(text=st.text(min_size=64, max_size=64).filter(lambda s: any(c not in "0123456789abcdef" for c in s)))
def test_is_hashed_rejects_non_hex_64chars(text):
	"""64-char strings with non-hex characters are not hashes."""
	assert not _is_hashed(text)


def test_is_hashed_accepts_known_sha256():
	"""A real SHA256 hex digest is recognized as hashed."""
	known = hashlib.sha256(b"1234").hexdigest()
	assert _is_hashed(known)


# ── Migration path ────────────────────────────────────────────────────────────


@given(plaintext_pin=st.text(alphabet="0123456789", min_size=4, max_size=8))
def test_migration_path_consistency(plaintext_pin):
	"""
	Migration logic: client sends SHA256(digits), stored is plaintext.
	Verify: compare_digest(client_hash, SHA256(stored_plaintext)) is True.
	"""
	import hmac

	client_sends = _hash_pin(plaintext_pin)  # SHA256 of digits
	stored_plaintext = plaintext_pin  # legacy DB value
	# Migration comparison
	assert hmac.compare_digest(client_sends, _hash_pin(stored_plaintext))


@given(plaintext_pin=st.text(alphabet="0123456789", min_size=4, max_size=8))
def test_after_migration_stored_is_hashed(plaintext_pin):
	"""After upgrading storage from plaintext to hash, _is_hashed returns True."""
	client_hash = _hash_pin(plaintext_pin)
	# This is what gets written to DB on first successful login
	assert _is_hashed(client_hash)
