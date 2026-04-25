"""
Groups G1-G4 — Hypothesis tests for HMAC approval token sign/verify.
Tests _sign_token and verify_approval_token logic without Redis or DB.
The frappe stub (conftest.py) provides get_encryption_key.
"""

import base64
import hashlib
import hmac
import json
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# ── Pull the pure functions from auth.py using the frappe stub ────────────────

# Patch frappe.utils.password before importing
sys.modules.setdefault(
	"frappe.utils.password", MagicMock(get_encryption_key=lambda: "surge-test-hmac-secret-key-32chars!!")
)

# Import the pure HMAC helpers directly
from surge.api.auth import APPROVAL_TOKEN_TTL, _get_hmac_secret, _sign_token, verify_approval_token

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_payload(
	action="discount_override",
	approver="manager@test.com",
	access_level="Manager",
	profile="TestProfile",
	ts=None,
	meta="",
) -> dict:
	return {
		"action": action,
		"approver": approver,
		"access_level": access_level,
		"profile": profile,
		"ts": (ts or datetime.now()).isoformat(),
		"meta": meta,
	}


# ── Sign/verify round-trip ────────────────────────────────────────────────────


def test_sign_verify_roundtrip():
	"""A freshly signed token with Redis stub → verify_approval_token returns payload."""
	payload = _make_payload()
	token = _sign_token(payload)

	cache_mock = MagicMock()
	cache_mock.get_value.return_value = "1"  # token exists in Redis

	with patch("surge.api.auth.frappe") as mock_frappe:
		mock_frappe.cache.return_value = cache_mock
		result = verify_approval_token(token)

	assert result is not None
	assert result["action"] == "discount_override"
	assert result["approver"] == "manager@test.com"


@given(action=st.text(min_size=1, max_size=50), meta=st.text(max_size=100))
def test_sign_roundtrip_any_action(action, meta):
	"""Any action string round-trips correctly through sign/verify."""
	assume("\x00" not in action)  # avoid null bytes in JSON
	payload = _make_payload(action=action, meta=meta)
	token = _sign_token(payload)

	cache_mock = MagicMock()
	cache_mock.get_value.return_value = "1"

	with patch("surge.api.auth.frappe") as mock_frappe:
		mock_frappe.cache.return_value = cache_mock
		result = verify_approval_token(token)

	assert result is not None
	assert result["action"] == action


# ── Tamper detection ──────────────────────────────────────────────────────────


def test_tampered_token_rejected():
	"""Any modification to the token body → signature mismatch → None returned."""
	payload = _make_payload()
	token = _sign_token(payload)

	# Tamper: flip a character in the data section
	data, sig = token.rsplit(".", 1)
	data_bytes = bytearray(base64.urlsafe_b64decode(data + "=="))
	data_bytes[0] ^= 0xFF  # flip first byte
	tampered_data = base64.urlsafe_b64encode(bytes(data_bytes)).decode().rstrip("=")
	tampered_token = f"{tampered_data}.{sig}"

	cache_mock = MagicMock()
	cache_mock.get_value.return_value = "1"

	with patch("surge.api.auth.frappe") as mock_frappe:
		mock_frappe.cache.return_value = cache_mock
		result = verify_approval_token(tampered_token)

	assert result is None


@given(garbage=st.text(min_size=1, max_size=200))
def test_random_string_rejected(garbage):
	"""Random strings are never valid tokens."""
	assume("." not in garbage or garbage.count(".") > 2)
	cache_mock = MagicMock()
	cache_mock.get_value.return_value = "1"
	with patch("surge.api.auth.frappe") as mock_frappe:
		mock_frappe.cache.return_value = cache_mock
		result = verify_approval_token(garbage)
	assert result is None


# ── TTL enforcement ───────────────────────────────────────────────────────────


def test_expired_token_rejected():
	"""Token with ts older than APPROVAL_TOKEN_TTL seconds → None."""
	stale_ts = datetime.now() - timedelta(seconds=APPROVAL_TOKEN_TTL + 60)
	payload = _make_payload(ts=stale_ts)
	token = _sign_token(payload)

	cache_mock = MagicMock()
	cache_mock.get_value.return_value = "1"

	with patch("surge.api.auth.frappe") as mock_frappe:
		mock_frappe.cache.return_value = cache_mock
		result = verify_approval_token(token)

	assert result is None


# ── One-time use (G2) ─────────────────────────────────────────────────────────


def test_token_consumed_on_verify():
	"""verify_approval_token deletes the Redis key — second call returns None."""
	payload = _make_payload()
	token = _sign_token(payload)

	call_count = 0

	def get_value(key):
		nonlocal call_count
		call_count += 1
		return "1" if call_count == 1 else None  # first call returns 1, second returns None

	cache_mock = MagicMock()
	cache_mock.get_value.side_effect = get_value

	with patch("surge.api.auth.frappe") as mock_frappe:
		mock_frappe.cache.return_value = cache_mock
		first = verify_approval_token(token)
		second = verify_approval_token(token)

	assert first is not None  # first use succeeds
	assert second is None  # second use rejected (key deleted)


# ── Redis fail-closed (G4) ────────────────────────────────────────────────────


def test_redis_unavailable_rejects_token():
	"""If Redis raises, token is rejected (fail-closed). No bypass via downtime."""
	payload = _make_payload()
	token = _sign_token(payload)

	cache_mock = MagicMock()
	cache_mock.get_value.side_effect = ConnectionError("Redis down")

	with patch("surge.api.auth.frappe") as mock_frappe:
		mock_frappe.cache.return_value = cache_mock
		mock_frappe.logger.return_value = MagicMock()
		result = verify_approval_token(token)

	assert result is None


# ── Token structure ───────────────────────────────────────────────────────────


def test_token_has_two_parts():
	"""Signed token always has exactly one dot separating data and signature."""
	token = _sign_token(_make_payload())
	parts = token.rsplit(".", 1)
	assert len(parts) == 2
	_data, sig = parts
	assert len(sig) == 64  # SHA256 hex


def test_token_data_is_valid_base64_json():
	"""The data section of the token is valid base64-encoded JSON."""
	token = _sign_token(_make_payload())
	data, _ = token.rsplit(".", 1)
	decoded = base64.urlsafe_b64decode(data + "==")
	parsed = json.loads(decoded)
	assert "action" in parsed
	assert "approver" in parsed
	assert "ts" in parsed
