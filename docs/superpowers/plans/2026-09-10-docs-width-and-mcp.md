# Responsive documentation and LLM retrieval

User request: expand the 688px VitePress article to approximately 953px on a
1920px desktop, keep mobile diagrams usable, and improve consumption as an
LLM Wiki source, including MCP.

- [x] Override the internal article cap and excess gutters; verify desktop,
  tablet, mobile, Mermaid, and embedded architecture diagrams in Chromium.
- [x] Extend the existing Markdown generator with a deterministic document
  manifest: stable ID, language, section, canonical/raw URLs, updated date,
  SHA-256 and byte length. Use the same published page allowlist for MCP.
- [x] Add an official-SDK stdio MCP server with bounded keyword search and
  paginated Markdown retrieval. Read the local checkout at startup, expose no
  arbitrary filesystem or network access, and preserve source citations.
- [x] Link the LLM index from HTML and document Wiki ingestion, configuration,
  refresh behavior, and the distinction between local MCP and remote hosting
  in both existing LLM guides.
- [x] Test corpus scope, search relevance and language filters, pagination,
  invalid IDs, transport behavior, generated metadata and links; run repository
  validation and both locale builds, then review the resulting changes.

Implementation boundaries: the theme owns layout; the existing generator owns
publication metadata; `scripts/lib/docs-search.mjs` owns retrieval;
`scripts/docs-mcp.mjs` owns the MCP transport. No deployment or client-global
configuration changes. New generated metadata belongs under ignored
`public/llms/`. GitHub Pages remains static; remote Streamable HTTP deployment
requires a separate runtime and is documented rather than advertised as live.

Validation completed:

- 93 tests, local links, referenced PNGs and Korean/English parity passed.
- Both locale builds passed with CI's `NODE_OPTIONS=--max-old-space-size=8192`.
- Chromium measured 688 → 952px at a 1920px viewport and verified seven
  viewport sizes plus 23 interaction/breakpoint checks.
- The built site passed desktop/mobile checks, AI-guide SPA navigation with
  an updated Markdown alternate, and manifest/raw Markdown HTTP retrieval.
- The 642-document catalog preserves citations and hashes; independent review
  fixes covered UTF-8-safe pagination/excerpts and 47 previously missed dates.
- Public index/Markdown endpoints returned HTTP 200 and origin robots.txt
  allowed crawling. Automatic AI discovery still depends on the consuming tool.

QA evidence is in `/tmp/vitepress-width-qa/` and
`/tmp/kubernetes-docs-production-qa.json`; generated outputs remain ignored.
