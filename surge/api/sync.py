import frappe

from surge.utils.json import surge_response
from surge.utils.permissions import require_pos_role


@frappe.whitelist(allow_guest=False)
def queue_status():
	require_pos_role()

	counts = frappe.db.sql(
		"""
        SELECT status, COUNT(*) as cnt
        FROM `tabSurge Write Queue`
        GROUP BY status
        """,
		as_dict=True,
	)

	result = {"pending": 0, "syncing": 0, "done": 0, "failed": 0, "conflict": 0}
	for row in counts:
		key = (row["status"] or "").lower()
		if key in result:
			result[key] = row["cnt"]

	return surge_response(result)


@frappe.whitelist(allow_guest=False)
def get_failed_items(offset: int = 0, limit: int = 50):
	require_pos_role()

	limit = min(int(limit), 200)
	offset = max(int(offset), 0)

	items = frappe.get_all(
		"Surge Write Queue",
		filters={"status": "Failed"},
		fields=[
			"name",
			"client_req_id",
			"resource_type",
			"attempt_count",
			"last_error",
			"creation",
		],
		order_by="creation asc",
		limit_page_length=limit,
		limit_start=offset,
	)

	total = frappe.db.count("Surge Write Queue", filters={"status": "Failed"})

	return surge_response(
		{
			"items": items,
			"count": len(items),
			"total": total,
			"offset": offset,
			"limit": limit,
			"has_more": offset + len(items) < total,
		}
	)


@frappe.whitelist(allow_guest=False)
def get_conflicts():
	from surge.utils.permissions import require_surge_manager_role

	require_surge_manager_role()

	conflicts = frappe.get_all(
		"Surge Sync Conflict",
		filters={"resolution": "Pending Review"},
		fields=[
			"name",
			"client_req_id",
			"terminal_id",
			"conflict_type",
			"conflict_detail",
			"payload",
			"creation",
		],
		order_by="creation asc",
		limit=50,
	)
	return surge_response({"conflicts": conflicts})


@frappe.whitelist(allow_guest=False)
def retry_failed(name: str):
	require_pos_role()

	doc = frappe.get_doc("Surge Write Queue", name)

	if doc.status not in ("Failed",):
		frappe.throw(
			f"Cannot retry item with status '{doc.status}'. Only 'Failed' items can be retried.",
			frappe.ValidationError,
		)

	doc.status = "Pending"
	doc.attempt_count = 0
	doc.last_error = None
	doc.next_retry_at = frappe.utils.now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — queue entry must be visible to background worker immediately

	return surge_response({"status": "queued", "name": name})
