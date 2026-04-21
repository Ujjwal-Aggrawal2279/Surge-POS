---
id: item-catalog
title: Item Catalog
sidebar_position: 9
---

# Item Catalog

An item appears in Surge POS if it is a **Sales Item**, has a price in the active Price List, and is not disabled.

**Images** — upload via the ERPNext Item doctype. Without an image, a category icon is shown.

**Category tabs** — auto-generated from ERPNext Item Groups. No extra configuration needed.

**Barcodes** — add in the Item's Barcodes table; the search box scans them automatically.

**Large catalogs** — delta sync + IndexedDB cache handle 5,000+ items without performance issues.
