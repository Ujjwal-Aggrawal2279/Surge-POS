"""
Unit test conftest — installs a lightweight frappe mock so pure Python
functions (hashing, HMAC, paise math) can be imported without a live site.
Only affects tests in surge/tests/unit/.
"""

import hashlib
import hmac as _hmac
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ── Build a minimal frappe stub ───────────────────────────────────────────────


def _build_frappe_stub() -> ModuleType:
	stub = ModuleType("frappe")

	# Exceptions the production code raises
	stub.ValidationError = type("ValidationError", (Exception,), {})
	stub.PermissionError = type("PermissionError", (Exception,), {})
	stub.AuthenticationError = type("AuthenticationError", (Exception,), {})

	def throw(msg, exc=None, title=None):
		raise (exc or stub.ValidationError)(msg)

	stub.throw = throw

	# Decorator no-op — just returns the function unchanged
	def whitelist(allow_guest=False):
		def decorator(fn):
			return fn

		return decorator

	stub.whitelist = whitelist
	stub.logger = MagicMock()
	stub.cache = MagicMock()
	stub.db = MagicMock()
	stub.session = MagicMock()
	stub.session.user = "test@example.com"
	stub.get_roles = MagicMock(return_value=["POS User"])
	stub.flags = MagicMock()
	stub.request = MagicMock()
	stub.request.remote_addr = "127.0.0.1"

	# frappe.utils submodule
	utils = ModuleType("frappe.utils")
	from datetime import datetime

	utils.now_datetime = datetime.now
	utils.add_to_date = MagicMock(return_value=datetime.now())
	utils.get_date_str = lambda d: str(d)
	stub.utils = utils
	sys.modules["frappe.utils"] = utils
	sys.modules["frappe.utils.password"] = MagicMock()

	# frappe.utils.password.get_encryption_key — return a fixed test key
	password_mod = sys.modules["frappe.utils.password"]
	password_mod.get_encryption_key = lambda: "surge-test-hmac-secret-key-32chars!!"

	return stub


# Install the stub before any surge module is imported
_frappe_stub = _build_frappe_stub()
sys.modules.setdefault("frappe", _frappe_stub)

# Also stub out msgspec (it's a C extension, available in CI via pip)
# If not available, create a minimal stub
try:
	import msgspec
except ImportError:
	msgspec_stub = ModuleType("msgspec")
	msgspec_stub.Struct = object
	sys.modules["msgspec"] = msgspec_stub
