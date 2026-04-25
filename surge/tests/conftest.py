"""
Root conftest for all Surge POS tests.

Unit tests (surge/tests/unit/) use the unit-level conftest which mocks frappe.
Integration tests (surge/tests/integration/) require a real Frappe site — they
are only run inside the bench environment (bench run-tests --app surge) or in
GitHub Actions after full Frappe setup.
"""

import os

import pytest


def pytest_configure(config):
	"""Register custom markers."""
	config.addinivalue_line("markers", "unit: pure Python tests, no Frappe/DB required")
	config.addinivalue_line("markers", "integration: requires a live Frappe site and MariaDB")
	config.addinivalue_line("markers", "e2e: end-to-end browser tests via Playwright")


def pytest_collection_modifyitems(config, items):
	"""Auto-mark tests based on their directory."""
	for item in items:
		path = str(item.fspath)
		if "/unit/" in path:
			item.add_marker(pytest.mark.unit)
		elif "/integration/" in path:
			item.add_marker(pytest.mark.integration)
		elif "/e2e/" in path:
			item.add_marker(pytest.mark.e2e)


def pytest_runtest_setup(item):
	"""
	Skip integration tests automatically when Frappe is not initialized.
	This allows running unit tests anywhere without a bench.
	"""
	if "integration" in [m.name for m in item.iter_markers()]:
		try:
			import frappe

			if not frappe.db:
				pytest.skip("Integration test requires an active Frappe site (frappe.db not connected)")
		except (ImportError, AttributeError):
			pytest.skip("Integration test requires Frappe to be installed and initialized")
