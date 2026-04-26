import frappe
from frappe.utils import get_date_str, now_datetime, nowdate

from surge.utils.json import surge_response
from surge.utils.permissions import require_pos_profile_access, require_surge_manager_role


@frappe.whitelist(allow_guest=False)
def get_active_session(pos_profile: str) -> dict:
	require_pos_profile_access(pos_profile)

	entry = frappe.db.get_value(
		"POS Opening Entry",
		{"pos_profile": pos_profile, "status": "Open", "docstatus": 1},
		["name", "period_start_date", "user"],
		as_dict=True,
	)
	if not entry:
		return surge_response({"session": None})

	# Opening entries from a previous day cannot accept new invoices —
	# validate_pos_opening_entry() on Sales Invoice rejects them.
	if get_date_str(entry.period_start_date) != nowdate():
		return surge_response({"session": None, "stale": True})

	return surge_response({"session": entry})


@frappe.whitelist(allow_guest=False)
def open_session(pos_profile: str, opening_balances: list) -> dict:
	require_pos_profile_access(pos_profile)

	existing = frappe.db.get_value(
		"POS Opening Entry",
		{"pos_profile": pos_profile, "status": "Open", "docstatus": 1},
		"name",
	)
	if existing:
		frappe.throw(
			f"A shift is already open for POS Profile '{pos_profile}'. Close it first.",
			frappe.ValidationError,
		)

	pos_profile_doc = frappe.get_cached_doc("POS Profile", pos_profile)

	doc = frappe.new_doc("POS Opening Entry")
	doc.pos_profile = pos_profile
	doc.company = pos_profile_doc.company
	doc.period_start_date = now_datetime()
	doc.posting_date = nowdate()
	doc.set_opening_balances = 0
	doc.user = frappe.session.user

	for bal in opening_balances or []:
		doc.append(
			"balance_details",
			{
				"mode_of_payment": bal["mode_of_payment"],
				"opening_amount": float(bal.get("amount") or 0),
			},
		)

	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — shift open must be persisted before cashier enters sell screen

	return surge_response(
		{
			"session_name": doc.name,
			"period_start_date": doc.period_start_date.isoformat(),
		}
	)


@frappe.whitelist(allow_guest=False)
def close_session(opening_entry: str, closing_balances: list, discrepancy_reason: str = "") -> dict:
	require_surge_manager_role()

	entry = frappe.get_doc("POS Opening Entry", opening_entry)
	if entry.status != "Open":
		frappe.throw(f"Session '{opening_entry}' is already closed.", frappe.ValidationError)

	z_report = _build_z_report(entry, closing_balances or [], discrepancy_reason)

	# Atomic UPDATE — WHERE status='Open' ensures only one concurrent request wins
	frappe.db.sql(
		"UPDATE `tabPOS Opening Entry` SET status = 'Closed', modified = %s WHERE name = %s AND status = 'Open'",
		(now_datetime(), opening_entry),
	)
	# ROW_COUNT() must be read before commit — commit resets it
	row_count = frappe.db.sql("SELECT ROW_COUNT()", as_list=True)[0][0]
	if not row_count:
		frappe.throw(
			f"Session '{opening_entry}' was just closed by another request.",
			frappe.ValidationError,
		)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — shift close must be persisted so Z-report is immediately visible

	return surge_response({"z_report": z_report})


def _build_z_report(entry, closing_balances: list, discrepancy_reason: str = "") -> dict:
	closing_map = {b["mode_of_payment"]: float(b.get("amount") or 0) for b in closing_balances}
	opening_map = {d.mode_of_payment: float(d.opening_amount or 0) for d in entry.balance_details}

	# Use a date range so sessions that cross midnight include all invoices
	invoices = frappe.db.sql(
		"""
		SELECT name, grand_total, total_taxes_and_charges, is_return
		FROM `tabSales Invoice`
		WHERE is_pos = 1
		  AND pos_profile = %s
		  AND docstatus = 1
		  AND posting_date >= %s
		  AND posting_date <= %s
		""",
		(entry.pos_profile, get_date_str(entry.period_start_date), nowdate()),
		as_dict=True,
	)

	sales = [i for i in invoices if not i.is_return]
	returns = [i for i in invoices if i.is_return]
	invoice_names = [i.name for i in sales]

	payment_totals: dict[str, float] = {}
	if invoice_names:
		rows = frappe.db.sql(
			"""
			SELECT mode_of_payment, SUM(amount) as total
			FROM `tabSales Invoice Payment`
			WHERE parent IN %s
			GROUP BY mode_of_payment
			""",
			(invoice_names,),
			as_dict=True,
		)
		payment_totals = {r.mode_of_payment: float(r.total or 0) for r in rows}

	net_sales = sum(float(i.grand_total or 0) for i in sales)
	net_returns = sum(float(i.grand_total or 0) for i in returns)
	total_tax = sum(float(i.total_taxes_and_charges or 0) for i in sales)

	# Iterate union of opening and closing modes — extra closing modes appear in Z-report
	all_modes = sorted(set(opening_map.keys()) | set(closing_map.keys()))

	def _paise(amount: float) -> int:
		return round(amount * 100)

	modes = []
	for mode in all_modes:
		opening = opening_map.get(mode, 0.0)
		sales_amt = payment_totals.get(mode, 0.0)
		expected = opening + sales_amt
		actual = closing_map.get(mode, 0.0)
		modes.append(
			{
				"mode_of_payment": mode,
				"opening_amount_paise": _paise(opening),
				"sales_amount_paise": _paise(sales_amt),
				"expected_amount_paise": _paise(expected),
				"actual_amount_paise": _paise(actual),
				"discrepancy_paise": _paise(actual - expected),
			}
		)

	return {
		"opening_entry": entry.name,
		"pos_profile": entry.pos_profile,
		"period_start": entry.period_start_date.isoformat(),
		"period_end": now_datetime().isoformat(),
		"cashier": entry.user,
		"total_invoices": len(sales),
		"total_returns": len(returns),
		"net_sales_paise": _paise(net_sales),
		"net_returns_paise": _paise(net_returns),
		"total_tax_paise": _paise(total_tax),
		"payment_modes": modes,
		"discrepancy_reason": discrepancy_reason,
	}
