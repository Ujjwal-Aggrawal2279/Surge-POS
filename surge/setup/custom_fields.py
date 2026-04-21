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
                "Auto-generated 4-digit PIN. "
                "Visible to System Manager only. "
                "Communicate to cashier verbally."
            ),
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
        }
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
