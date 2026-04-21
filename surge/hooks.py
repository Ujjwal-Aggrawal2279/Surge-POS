app_name = "surge"
app_title = "Surge POS"
app_publisher = "Surge"
app_description = "High-performance POS for ERPNext — India-first, offline-ready"
app_email = "ujjmee2279@gmail.com"
app_license = "mit"
app_version = "0.1.0"

required_apps = ["frappe", "erpnext"]

# ---------------------------------------------------------------------------
# Install / migrate hooks
# ---------------------------------------------------------------------------

after_install = "surge.setup.install.after_install"
before_uninstall = "surge.setup.uninstall.before_uninstall"

# ---------------------------------------------------------------------------
# Auth hooks
# ---------------------------------------------------------------------------

on_session_creation = "surge.utils.auth.on_session_creation"

# Inject "Sign in to Surge POS" link on the default /login page
web_include_js = ["/assets/surge/js/login_inject.js"]

# Auto-generate cashier PIN when a user is made Active on a POS Profile
# Auto-invalidate Surge caches when ERPNext master data changes
doc_events = {
    "POS Profile User": {
        "before_insert": "surge.utils.pin_hooks.auto_generate_pin",
        "before_save":   "surge.utils.pin_hooks.auto_generate_pin",
    },
    "Item": {
        "on_update": "surge.utils.cache_hooks.on_item_update",
        "after_insert": "surge.utils.cache_hooks.on_item_update",
    },
    "Customer": {
        "on_update": "surge.utils.cache_hooks.on_customer_update",
        "after_insert": "surge.utils.cache_hooks.on_customer_update",
    },
    "Bin": {
        "on_update": "surge.utils.cache_hooks.on_bin_update",
    },
    "Item Price": {
        "on_update": "surge.utils.cache_hooks.on_item_price_update",
        "after_insert": "surge.utils.cache_hooks.on_item_price_update",
    },
}

add_to_apps_screen = [
    {
        "name": "surge",
        "logo": "/assets/surge/images/SurgeLogo.png",
        "title": "Surge POS",
        "route": "/surge",
    }
]

scheduler_events = {
    # Runs every ~10s — flushes offline write queue with exponential backoff
    "all": [
        "surge.jobs.sync_engine.flush_write_queue",
    ],
}

website_route_rules = [
    {"from_route": "/surge/<path:app_path>", "to_route": "surge"},
]
