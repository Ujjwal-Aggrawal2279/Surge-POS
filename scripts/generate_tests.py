#!/usr/bin/env python3
"""
Surge POS — Autonomous Test Coverage Engine

Reads every @frappe.whitelist function in surge/api/*.py using Python's
built-in ast module (zero external dependencies).

For each endpoint, extracts:
  - All frappe.throw() call messages  → validation paths that MUST be tested
  - All require_*() guard calls       → permission guards
  - All msgspec Struct fields + types → Hypothesis strategy hints

Outputs:
  surge/tests/generated/manifest.json   — machine-readable endpoint map
  surge/tests/generated/test_*_gen.py   — generated pytest stubs with parametrize

Exits 1 if:
  - Any @whitelist endpoint has zero frappe.throw AND zero require_* → security gap
  - Any frappe.throw message has no corresponding test (grep check against integration/)
"""

import ast
import json
import os
import re
import sys
import textwrap
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

API_DIR = Path(__file__).parent.parent / "surge" / "api"
TESTS_DIR = Path(__file__).parent.parent / "surge" / "tests"
GENERATED_DIR = TESTS_DIR / "generated"
INTEGRATION_DIR = TESTS_DIR / "integration"


# ── AST Helpers ──────────────────────────────────────────────────────────────


def _is_whitelist_decorator(node: ast.expr) -> bool:
	"""Check if decorator is @frappe.whitelist(...)."""
	if isinstance(node, ast.Attribute):
		return isinstance(node.value, ast.Name) and node.value.id == "frappe" and node.attr == "whitelist"
	if isinstance(node, ast.Call):
		return _is_whitelist_decorator(node.func)
	return False


def _extract_throw_messages(tree: ast.AST) -> list[dict]:
	"""Find all frappe.throw(message, ExcType) calls in the AST."""
	results = []
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		func = node.func
		is_throw = (
			isinstance(func, ast.Attribute)
			and func.attr == "throw"
			and isinstance(func.value, ast.Name)
			and func.value.id == "frappe"
		)
		if not is_throw or not node.args:
			continue
		# First arg is the message
		msg_node = node.args[0]
		message = ast.literal_eval(msg_node) if isinstance(msg_node, ast.Constant) else None
		# Second arg (if present) is exception type
		exc = None
		if len(node.args) > 1:
			exc_node = node.args[1]
			if isinstance(exc_node, ast.Attribute):
				exc = exc_node.attr
			elif isinstance(exc_node, ast.Name):
				exc = exc_node.id
		results.append({"message": message, "exc": exc or "ValidationError", "line": node.lineno})
	return results


def _extract_require_guards(tree: ast.AST) -> list[str]:
	"""Find all require_*() guard calls (require_pos_profile_access, require_surge_manager_role, etc.)."""
	guards = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Call):
			func = node.func
			name = None
			if isinstance(func, ast.Name):
				name = func.id
			elif isinstance(func, ast.Attribute):
				name = func.attr
			if name and name.startswith("require_"):
				guards.append(name)
	return list(set(guards))


def _extract_structs(tree: ast.AST) -> dict[str, dict]:
	"""Find msgspec.Struct subclasses and their typed fields."""
	structs = {}
	for node in ast.walk(tree):
		if not isinstance(node, ast.ClassDef):
			continue
		bases = node.bases
		is_struct = any(
			(isinstance(b, ast.Attribute) and b.attr == "Struct")
			or (isinstance(b, ast.Name) and b.id == "Struct")
			for b in bases
		)
		if not is_struct:
			continue
		fields = {}
		for item in node.body:
			if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
				field_name = item.target.id
				ann = ast.unparse(item.annotation)
				default = ast.unparse(item.value) if item.value else None
				fields[field_name] = {"type": ann, "default": default}
		structs[node.name] = fields
	return structs


# ── Per-file analysis ─────────────────────────────────────────────────────────


def analyze_file(path: Path) -> dict:
	"""Parse one API file and return its endpoint manifest."""
	source = path.read_text()
	try:
		tree = ast.parse(source)
	except SyntaxError as e:
		print(f"SYNTAX ERROR in {path}: {e}", file=sys.stderr)
		return {}

	structs = _extract_structs(tree)
	endpoints = {}

	for node in ast.walk(tree):
		if not isinstance(node, ast.FunctionDef):
			continue
		# Must have @frappe.whitelist decorator
		has_whitelist = any(_is_whitelist_decorator(d) for d in node.decorator_list)
		if not has_whitelist:
			continue

		fn_name = node.name
		# Build a sub-tree for this function only (walk its body)
		fn_tree = ast.Module(body=node.body, type_ignores=[])
		throws = _extract_throw_messages(fn_tree)
		guards = _extract_require_guards(fn_tree)

		endpoints[fn_name] = {
			"module": f"surge.api.{path.stem}",
			"line": node.lineno,
			"throws": throws,
			"guards": guards,
			"structs_used": [s for s in structs],
		}

	return {"structs": structs, "endpoints": endpoints}


# ── Coverage check ────────────────────────────────────────────────────────────


def check_coverage(manifest: dict) -> list[str]:
	"""
	For each frappe.throw message found, grep integration test files to verify
	at least one test references that message string.
	Returns list of uncovered message strings.
	"""
	integration_sources = ""
	if INTEGRATION_DIR.exists():
		for f in INTEGRATION_DIR.glob("*.py"):
			integration_sources += f.read_text()

	uncovered = []
	for file_data in manifest.values():
		for fn_data in file_data.get("endpoints", {}).values():
			for throw in fn_data.get("throws", []):
				msg = throw.get("message")
				if not msg:
					continue
				# Check if any fragment of the message appears in test files
				fragment = msg[:30]  # first 30 chars is enough
				if fragment not in integration_sources:
					uncovered.append(msg)
	return uncovered


# ── Test file generation ──────────────────────────────────────────────────────


def _type_to_hypothesis(type_str: str) -> str:
	"""Map msgspec type annotations to Hypothesis strategies."""
	mapping = {
		"str": "st.text(min_size=1, max_size=100)",
		"str | None": "st.one_of(st.none(), st.text(min_size=1, max_size=100))",
		"int": "st.integers(min_value=-1_000_000, max_value=1_000_000)",
		"float": "st.floats(min_value=-10000.0, max_value=10000.0, allow_nan=False)",
		"bool": "st.booleans()",
		"list": "st.lists(st.text(), max_size=5)",
	}
	for key, strat in mapping.items():
		if key in type_str:
			return strat
	return "st.text()"


def generate_test_file(api_stem: str, file_data: dict) -> str:
	"""Produce a pytest file for one API module."""
	endpoints = file_data.get("endpoints", {})
	structs = file_data.get("structs", {})

	if not endpoints:
		return ""

	lines = [
		f"# Generated by scripts/generate_tests.py from surge/api/{api_stem}.py",
		"# DO NOT EDIT — regenerated on every CI run",
		"# Add real tests in surge/tests/integration/ to cover these paths.",
		"",
		"import pytest",
		"",
		"# ── Endpoint manifest ────────────────────────────────────────────",
		f"ENDPOINTS = {json.dumps({k: v['module'] for k, v in endpoints.items()}, indent=4)}",
		"",
	]

	# Struct field type map (for documentation + Hypothesis hints)
	if structs:
		lines.append("# ── Struct field types (Hypothesis strategy hints) ──────────────")
		lines.append("STRUCT_STRATEGIES = {")
		for struct_name, fields in structs.items():
			lines.append(f"    {struct_name!r}: {{")
			for field, meta in fields.items():
				strategy = _type_to_hypothesis(meta["type"])
				lines.append(f"        {field!r}: '{strategy}',  # {meta['type']}")
			lines.append("    },")
		lines.append("}")
		lines.append("")

	# Parametrized stub for each validation path
	all_paths = []
	for fn_name, fn_data in endpoints.items():
		for throw in fn_data.get("throws", []):
			msg = throw.get("message")
			if msg:
				all_paths.append((fn_name, msg, throw.get("exc", "ValidationError")))

	if all_paths:
		lines.append("# ── Validation path stubs (implement in integration/) ────────────")
		lines.append("# Each stub will XFAIL until a real integration test covers it.")
		param_data = [(f"{fn}::{msg[:40]}", fn, msg) for fn, msg, _ in all_paths]
		lines.append("@pytest.mark.parametrize('path_id,endpoint,error_fragment', [")
		for pid, fn, msg in param_data:
			lines.append(f"    ({pid!r}, {fn!r}, {msg[:60]!r}),")
		lines.append("])")
		lines.append(
			"def test_validation_path_has_integration_coverage(path_id, endpoint, error_fragment, request):"
		)
		lines.append(
			"    '''Each frappe.throw() path must have an integration test that matches the message.'''"
		)
		lines.append("    # This xfail is removed when integration/test_*.py covers the message.")
		lines.append("    pytest.xfail(f'Add integration test covering: {error_fragment!r} in {endpoint}')")
		lines.append("")

	# Security gate: endpoints with no guards and no throws
	unguarded = [fn for fn, data in endpoints.items() if not data["throws"] and not data["guards"]]
	if unguarded:
		lines.append("# ── Security gap detection ───────────────────────────────────────")
		lines.append("@pytest.mark.parametrize('endpoint', [")
		for fn in unguarded:
			lines.append(f"    {fn!r},")
		lines.append("])")
		lines.append("def test_endpoint_has_validation_or_guard(endpoint):")
		lines.append("    pytest.fail(")
		lines.append("        f'SECURITY GAP: {endpoint} has no frappe.throw() and no require_*() guard. '")
		lines.append("        'Add input validation or remove this test by adding guards.'")
		lines.append("    )")

	return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
	args = argv or sys.argv[1:]

	GENERATED_DIR.mkdir(parents=True, exist_ok=True)
	(GENERATED_DIR / "__init__.py").touch()

	full_manifest = {}
	exit_code = 0
	security_gaps = []

	api_files = sorted(API_DIR.glob("*.py"))
	api_files = [f for f in api_files if f.name != "__init__.py"]

	print(f"Scanning {len(api_files)} API files in {API_DIR}...")

	for api_path in api_files:
		data = analyze_file(api_path)
		if not data.get("endpoints"):
			continue

		full_manifest[api_path.stem] = data
		ep_count = len(data["endpoints"])
		throw_count = sum(len(v["throws"]) for v in data["endpoints"].values())
		print(f"  {api_path.name}: {ep_count} endpoints, {throw_count} validation paths")

		# Security gate: collect unguarded endpoints
		for fn_name, fn_data in data["endpoints"].items():
			if not fn_data["throws"] and not fn_data["guards"]:
				security_gaps.append(f"{api_path.stem}.{fn_name}")

		# Write generated test file
		content = generate_test_file(api_path.stem, data)
		if content:
			out_path = GENERATED_DIR / f"test_{api_path.stem}_gen.py"
			out_path.write_text(content)
			print(f"  → wrote {out_path.name}")

	# Write manifest JSON (used by CI coverage check step)
	manifest_path = GENERATED_DIR / "manifest.json"
	manifest_path.write_text(json.dumps(full_manifest, indent=2, default=str))
	print(f"\nManifest written: {manifest_path}")

	# Print security gaps after all scanning is done
	if security_gaps:
		print(f"\n{'=' * 60}", file=sys.stderr)
		print(f"SECURITY GAPS — {len(security_gaps)} unvalidated endpoints:", file=sys.stderr)
		for gap in security_gaps:
			print(f"  ⚠  {gap} has no frappe.throw() AND no require_*() guard", file=sys.stderr)
		print(f"{'=' * 60}", file=sys.stderr)
		exit_code = 1

	# Coverage check: verify integration tests cover each error message
	if "--check-coverage" in args:
		uncovered = check_coverage(full_manifest)
		if uncovered:
			print(
				f"\n❌ {len(uncovered)} validation paths have no integration test coverage:", file=sys.stderr
			)
			for msg in uncovered:
				print(f"   missing: {msg!r}", file=sys.stderr)
			exit_code = 1
		else:
			print(
				f"\n✓ All {sum(len(v.get('throws', [])) for d in full_manifest.values() for v in d.get('endpoints', {}).values())} validation paths are covered"
			)

	total_endpoints = sum(len(d.get("endpoints", {})) for d in full_manifest.values())
	print(f"\nTotal: {total_endpoints} whitelisted endpoints scanned")

	return exit_code


if __name__ == "__main__":
	sys.exit(main())
