SURGE_CUSTOM_FIELDS: dict = {
	"Role": [
		{
			"fieldname": "pos_access",
			"fieldtype": "Check",
			"label": "POS Access",
			"default": "0",
			"insert_after": "desk_access",
			"description": "Users with this role can log in to Surge POS.",
		}
	],
	"POS Profile User": [
		{
			"fieldname": "status",
			"fieldtype": "Select",
			"label": "Status",
			"options": "Active\nInactive",
			"default": "Active",
			"insert_after": "user",
		},
		{
			"fieldname": "access_level",
			"fieldtype": "Select",
			"label": "Access Level",
			"options": "Cashier\nSupervisor\nManager",
			"default": "Cashier",
			"insert_after": "status",
		},
		{
			"fieldname": "surge_pos_pin",
			"fieldtype": "Data",
			"label": "Cashier PIN",
			"read_only": 1,
			"no_copy": 1,
			"permlevel": 1,
			"insert_after": "access_level",
			"description": (
				"Auto-generated 4-digit PIN. Visible to System Manager only. Communicate to cashier verbally."
			),
		},
	],
	"POS Profile": [
		{
			"fieldname": "surge_discount_section",
			"fieldtype": "Section Break",
			"label": "Surge Discount Limits",
			"insert_after": "allow_discount_change",
		},
		{
			"fieldname": "discount_limit_cashier",
			"fieldtype": "Percent",
			"label": "Cashier Discount Limit (%)",
			"default": "5",
			"insert_after": "surge_discount_section",
			"description": "Maximum discount a Cashier can apply without Supervisor/Manager approval.",
		},
		{
			"fieldname": "discount_limit_supervisor",
			"fieldtype": "Percent",
			"label": "Supervisor Discount Limit (%)",
			"default": "15",
			"insert_after": "discount_limit_cashier",
		},
		{
			"fieldname": "discount_limit_manager",
			"fieldtype": "Percent",
			"label": "Manager Discount Limit (%)",
			"default": "100",
			"insert_after": "discount_limit_supervisor",
		},
	],
	"POS Invoice": [
		{
			"fieldname": "surge_client_req_id",
			"fieldtype": "Data",
			"label": "Surge Client Request ID",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "amended_from",
		},
		{
			"fieldname": "override_approved_by",
			"fieldtype": "Link",
			"options": "User",
			"label": "Override Approved By",
			"read_only": 1,
			"no_copy": 1,
			"permlevel": 1,
			"insert_after": "surge_client_req_id",
		},
		{
			"fieldname": "override_approved_at",
			"fieldtype": "Datetime",
			"label": "Override Approved At",
			"read_only": 1,
			"no_copy": 1,
			"permlevel": 1,
			"insert_after": "override_approved_by",
		},
		{
			"fieldname": "override_reason",
			"fieldtype": "Small Text",
			"label": "Override Reason",
			"read_only": 1,
			"no_copy": 1,
			"permlevel": 1,
			"insert_after": "override_approved_at",
		},
		{
			"fieldname": "void_reason",
			"fieldtype": "Small Text",
			"label": "Void Reason",
			"read_only": 1,
			"no_copy": 1,
			"permlevel": 1,
			"insert_after": "override_reason",
		},
	],
	"Sales Invoice": [
		{
			"fieldname": "surge_client_req_id",
			"fieldtype": "Data",
			"label": "Surge Client Request ID",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "amended_from",
		}
	],
}
