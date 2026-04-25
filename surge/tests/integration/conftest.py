"""
Initialize a live Frappe site before integration tests run.

Frappe's pytest plugin has an autouse fixture that skips every test when
frappe.db is None. Calling frappe.init() + frappe.connect() here, in
pytest_configure (before fixture setup), satisfies that check.
"""

import os


def pytest_configure(config):
	import frappe

	bench = os.environ.get("FRAPPE_BENCH", os.getcwd())
	site = os.environ.get("FRAPPE_SITE", "test.localhost")
	frappe.init(site=site, sites_path=os.path.join(bench, "sites"))
	frappe.connect()


def pytest_sessionfinish(session, exitstatus):
	try:
		import frappe

		frappe.destroy()
	except Exception:
		pass
