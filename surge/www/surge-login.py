"""
Backward-compat redirect — /surge-login now redirects to /surge.
The React app handles login for guests.
"""
import frappe

no_cache = 1
allow_guest = True


def get_context(context):
    frappe.local.flags.redirect_location = "/surge"
    raise frappe.Redirect
