import frappe
from frappe.model.document import Document


class POSSecurityAuditLog(Document):
	def before_save(self):
		# Immutable — block all edits after creation
		if not self.is_new():
			frappe.throw("Audit log entries cannot be modified.", frappe.PermissionError)
