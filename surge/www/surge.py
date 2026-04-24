import frappe

from surge.utils.auth import get_user_pos_flags

no_cache = 1


def get_context(context):
	context.dev_server = bool(frappe.conf.get("developer_mode") and frappe.conf.get("surge_dev_server"))
	context.socketio_port = frappe.conf.get("socketio_port") or 9000

	if frappe.session.user == "Guest":
		# React app handles auth — serve the shell with minimal guest context
		context.user = "Guest"
		context.csrf_token = ""
		context.user_fullname = ""
		context.site_name = frappe.local.site
		context.has_desk_access = 0
		return

	# Ensure CSRF token exists before React reads it
	if not frappe.session.data.get("csrf_token"):
		frappe.session.data.csrf_token = frappe.generate_hash()
		frappe.session.update()

	flags = get_user_pos_flags(frappe.session.user)

	context.user = frappe.session.user
	context.csrf_token = frappe.session.data.csrf_token
	context.user_fullname = frappe.utils.get_fullname(frappe.session.user)
	context.site_name = frappe.local.site
	context.has_desk_access = 1 if flags.get("has_desk") else 0
