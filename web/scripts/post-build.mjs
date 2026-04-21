#!/usr/bin/env node
/**
 * post-build.mjs
 *
 * Runs after `vite build`:
 *  1. Reads the Vite-generated dist/index.html
 *  2. Extracts all asset tags (script, modulepreload, stylesheet)
 *  3. Replaces the production block in surge.html so chunk hashes stay current
 *  4. Runs `bench build --app surge` to copy assets into the site's public dir
 */

import { readFileSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dir = dirname(fileURLToPath(import.meta.url));
const webDir = resolve(__dir, "..");
const distHtml = resolve(webDir, "../surge/public/dist/index.html");
const surgeHtml = resolve(webDir, "../surge/www/surge.html");
const benchRoot = resolve(webDir, "../../..");

// ── 1. Parse asset tags from Vite output ────────────────────────────────────

const indexHtml = readFileSync(distHtml, "utf8");
const tags = [];

// CSS first — only local assets (external fonts are handled by the bundle's CSS)
for (const m of indexHtml.matchAll(/<link\s[^>]*rel="stylesheet"[^>]*>/g)) {
  const href = m[0].match(/href="([^"]+)"/)?.[1];
  if (href?.startsWith("/")) tags.push(`  <link rel="stylesheet" crossorigin href="${href}">`);
}

// Module preloads (chunks)
for (const m of indexHtml.matchAll(/<link\s[^>]*rel="modulepreload"[^>]*>/g)) {
  const href = m[0].match(/href="([^"]+)"/)?.[1];
  if (href) tags.push(`  <link rel="modulepreload" crossorigin href="${href}">`);
}

// Entry script
const scriptM = indexHtml.match(/<script\s[^>]*type="module"[^>]*src="([^"]+)"[^>]*><\/script>/);
if (scriptM?.[1]) tags.push(`  <script type="module" crossorigin src="${scriptM[1]}"></script>`);

if (tags.length === 0) {
  console.error("✗ No asset tags found in dist/index.html — aborting.");
  process.exit(1);
}

// ── 2. Splice tags into surge.html ──────────────────────────────────────────

const template = readFileSync(surgeHtml, "utf8");

// Matches:  {%- else -%}  ...anything...  {%- endif -%}
//           (including the block we wrote last time)
const BLOCK_RE = /(\{%-?\s*else\s*-?%\})[\s\S]*?(\{%-?\s*endif\s*-?%\})/;

if (!BLOCK_RE.test(template)) {
  console.error("✗ Could not find {%- else -%}...{%- endif -%} block in surge.html — aborting.");
  process.exit(1);
}

const updated = template.replace(
  BLOCK_RE,
  `$1\n${tags.join("\n")}\n  $2`,
);

writeFileSync(surgeHtml, updated, "utf8");
console.log(`✓ surge.html updated with ${tags.length} asset tag(s)`);

// ── 3. bench build ──────────────────────────────────────────────────────────

if (process.argv.includes("--skip-bench")) {
  console.log("⏭  bench build skipped (--skip-bench)");
} else {
  try {
    execSync("bench build --app surge", { cwd: benchRoot, stdio: "inherit" });
  } catch {
    console.warn("⚠  bench build failed or not found — run manually:");
    console.warn("     cd", benchRoot, "&& bench build --app surge");
  }
}
