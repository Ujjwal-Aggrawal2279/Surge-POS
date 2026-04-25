"""
Initialize a live Frappe site before integration tests run.

Frappe's pytest plugin has an autouse fixture that skips every test when
frappe.db is None. Calling frappe.init() + frappe.connect() here, in
pytest_configure (before fixture setup), satisfies that check.

Frappe v16 resolves sites as {bench}/{site}/ (bench root as sites_path),
not {bench}/sites/{site}/. We match that convention here so the site
symlink created in CI resolves to the actual site directory.
"""

import os


def pytest_configure(config):
	import frappe

	bench = os.environ.get("FRAPPE_BENCH", os.getcwd())
	site = os.environ.get("FRAPPE_SITE", "test.localhost")
	# v16: sites_path = bench root; site lives at {bench}/{site}/
	frappe.init(site=site, sites_path=bench)
	frappe.connect()


def pytest_sessionfinish(session, exitstatus):
	try:
		import frappe

		frappe.destroy()
	except Exception:
		pass
