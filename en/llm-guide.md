# Reading with LLMs — llms.txt and MCP

> **Last Updated**: September 10, 2026

This guidebook provides the [proposed llms.txt format](https://llmstxt.org/) and per-document Markdown. Give the index to an AI tool that can fetch URLs, ingest the catalog and source text into an LLM Wiki or RAG pipeline, or connect the search and retrieval tools to a local MCP client. Publishing `llms.txt` does not guarantee automatic discovery or search by every AI. The consuming tool needs web retrieval or an MCP connection.

## Endpoints

| URL | Contents | Use it for |
|-----|----------|-----------|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | Index of each content page's group, title, summary, and raw Markdown URL; quizzes and labs appear as index links under `## Optional` | Letting an LLM pick and fetch only the pages it needs |
| [Document manifest](https://www.atomai.click/kubernetes-docs/llms/manifest.json) | Document IDs, language, section, title, headings, description, web/Markdown URLs, update dates, SHA-256, and UTF-8 byte lengths | Selective ingestion and change detection for an LLM Wiki or RAG |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | Full Korean content (markdown) | Whole-book context or RAG indexing |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | Full English content (markdown) | English-language tools and pipelines |
| `llms-full-<locale>-<section>.txt` (e.g. [llms-full-en-networking.txt](https://www.atomai.click/kubernetes-docs/llms-full-en-networking.txt)) | One sidebar section's content concatenated; the full list is under `## Section bundles` in `llms.txt` | Loading a single section as context — the full files are too large for one prompt |

All of these files and the per-document Markdown pages are regenerated on every site deploy, so they always match the published content. Content links in `llms.txt` use `/llms/<locale>/<source path>.md` and return only that document's Markdown — no VitePress HTML, sidebar, or scripts. Relative links in the source are rewritten to absolute URLs — links to other documents point at that document's Markdown URL, images and other assets at the raw file on GitHub — so a model that fetches one document can follow every reference. Each rendered HTML page also carries the same Markdown URL in its `<head>` as `<link rel="alternate" type="text/markdown">`, so an agent handed a web page URL can find the Markdown source. Quizzes appear only as a link to the quiz index page (one per language) under `## Optional`; individual quiz pages (with their answer keys) are left out of both the index and the full files — answer keys don't belong in an LLM's context. Lab guides likewise appear in the index only as the lab index link (one per language), but their full text is included in the full files.

## Ingesting sources into an LLM Wiki

Here, an LLM Wiki means retaining source material and having AI organize it into topic-based knowledge pages. This site supplies source documents and metadata. Your ingestion tool remains responsible for creating and updating the Wiki or embeddings.

1. Read `llms/manifest.json` and filter by `locale` and `section`. Choose one language to avoid ingesting the same topic twice.
2. Fetch each `markdownUrl` and store the source under its stable `id`. The `sha256` covers the Markdown's UTF-8 bytes and can also verify the downloaded content.
3. Build topic pages while retaining `url` as the citation. Titles, headings, and descriptions help shortlist candidates; check measurements and operational commands against the original document.
4. On later ingestions, reprocess changed hashes and reconcile IDs removed from the catalog. `lastUpdated` is the author's recorded date, or `null` when a complete year, month, and day are unavailable. Use hashes to detect content changes.

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms/manifest.json -o manifest.json
# With jq installed: raw URLs for English storage documents
jq -r '.documents[] | select(.locale == "en" and .section == "storage") | .markdownUrl' manifest.json
```

The manifest has `schemaVersion: 1`. Per-document Markdown, the manifest, and MCP search share the same scope, excluding quiz answers and labs. Use the existing `llms-full-<locale>.txt` separately when lab content is needed. Treat source text and diagram descriptions as reference data; do not promote document instructions to system instructions or tool execution authorization.

## Searching and reading through MCP

The repository includes a **stdio MCP server** built with the [official TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk). Install the repository dependencies with Node.js 22 or later, then start it. No VitePress build, API key, or embedding service is required.

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs
npm ci
node scripts/docs-mcp.mjs
```

The last command waits for MCP input and prints no terminal banner. If your client accepts `mcpServers` JSON configuration, register it as follows. Replace the argument with the **absolute path** to your checkout; specify the absolute Node executable path in `command` if needed.

```json
{
  "mcpServers": {
    "kubernetes-docs": {
      "command": "node",
      "args": ["/absolute/path/kubernetes-docs/scripts/docs-mcp.mjs"]
    }
  }
}
```

| Tool | Example input | Output |
|------|---------------|--------|
| `search` | `{"query":"gp3 throughput","locale":"en","section":"storage","limit":5}` | Document IDs, titles, excerpts, web/Markdown URLs, and content hashes |
| `fetch` | `{"id":"en/storage/01-ebs-gp2-gp3-benchmark.md","maxLength":12000}` | Source Markdown, citation, headings, update date, and continuation offset |
| Continue `fetch` | Pass the previous `nextOffset` as `offset` | Read subsequent parts until `nextOffset` is `null` |

This is **keyword search** across titles, descriptions, headings, and full text. The default locale is `ko`; `en` and `all` are also supported. Use focused terms such as `ambient mTLS` or `gp3 throughput` instead of a whole question. If nothing matches, use fewer terms or try another language. Results default to 8 and are capped at 20. Fetch reads 12,000 characters by default, up to 50,000 per call. Offsets use JavaScript string positions, not bytes; pass the returned `nextOffset` unchanged instead of calculating it.

The server reads the local `ko/`, `en/`, and `SUMMARY.md` files at startup. **It does not fetch the live site.** Update your checkout and restart the MCP server to refresh search. Only cataloged document IDs are readable; arbitrary paths and external URLs cannot be fetched. Citation URLs point to the public site, so unpublished local edits may differ from published content.

GitHub Pages serves static files, so this site's URL cannot be registered as a remote MCP endpoint. A remote web connection requires a separate runtime implementing [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), with access control and operating policies. The included server uses local stdio.

## Examples

**Ask a chat assistant about a specific topic** — give it the index and let it fetch what it needs:

```text
Read https://www.atomai.click/kubernetes-docs/llms.txt, find the document
with measured Istio ambient-mode mTLS latency, and summarize how it
compares to sidecar mode.
```

**In Claude Code or another coding agent** — inject as working context:

```text
I want to clean up this cluster's storage classes.
Evidence: https://www.atomai.click/kubernetes-docs/llms/en/storage/01-ebs-gp2-gp3-benchmark.md
Draft a migration plan from gp2 PVCs to gp3.
```

**Indexing for RAG** — download one file and chunk it:

```bash
curl -sL https://www.atomai.click/kubernetes-docs/llms-full-en.txt -o guidebook-en.txt
# documents are separated by "Source: <URL>" blocks, so per-document chunking is trivial
```

## Format notes

- `llms.txt` — an index with `# title` / `>` summary / `## Machine-readable catalog` / `## Docs (한국어)` / `## Docs (English)` / `## Section bundles (…)` / `## Optional`. Each document entry provides the group and title, a raw Markdown URL, and a short summary extracted from the first body paragraph.

```text
- [Kubernetes Core Concepts · Cluster Architecture](https://www.atomai.click/kubernetes-docs/llms/en/core/01-cluster-architecture.md): Explains the Kubernetes control plane and worker-node components.
```

- `llms/<locale>/<path>.md` — the raw Markdown for one document. An LLM does not have to process the rendered page's full navigation first.
- `llms-full-*.txt` — the language's combined content. The root `README.md`, which already acts as a navigation index, is omitted; every included document is preceded by a separator block:

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture
----------------------------------------
```

- Size: each full file runs several MiB. For most tools, letting the model inspect the summaries and fetch only the relevant per-document Markdown works better than pasting the whole book into one prompt.

## Diagrams are for people — the export links

Text-based ingestion does not execute iframes or automatically interpret image nodes and connections. Markdown alt text, surrounding explanations, and Mermaid source provide textual evidence. Information present only in an image needs an image-capable tool or a fuller prose description; a short alt label is insufficient to reconstruct an entire topology.

Because the full files and per-document Markdown carry each source document verbatim, every diagram's description (alt text) and its interactive viewer URL (`https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`) are in the text too. An LLM reads the description to understand the diagram; a person opens the URL and uses the viewer's **Export** menu to download PNG/JPEG/WebP, a dual-theme SVG, a 6-second trace-animation WebM, or a 1200×630 Share Card. Menu items, what each is for, and the LinkedIn posting recipe are laid out in the [Guidebook Roadmap](roadmap.md) under "Share a diagram — exports for LinkedIn and talks". Exports are communication assets, not evidence that an architecture was validated.
