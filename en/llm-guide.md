# Reading with LLMs — llms.txt

> **Last Updated**: September 2, 2026

The entire guidebook is published under the [llms.txt convention](https://llmstxt.org/). Hand a single URL to ChatGPT, Claude, or your in-house RAG pipeline and this book becomes a knowledge source.

## Endpoints

| URL | Contents | Use it for |
|-----|----------|-----------|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | Index of every content page (title + URL); quizzes and labs appear as index links under `## Optional` | Letting an LLM pick and fetch only the pages it needs |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | Full Korean content (markdown) | Whole-book context or RAG indexing |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | Full English content (markdown) | English-language tools and pipelines |

All three files are regenerated on every site deploy, so they always match the published content. Quizzes appear in `llms.txt` only as a link to the quiz index page (one per language) under `## Optional`; individual quiz pages (with their answer keys) are left out of both the index and the full files — answer keys don't belong in an LLM's context. Lab guides likewise appear in the index only as the lab index link (one per language), but their full text is included in the full files.

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
Evidence: https://www.atomai.click/kubernetes-docs/en/storage/01-ebs-gp2-gp3-benchmark
Draft a migration plan from gp2 PVCs to gp3.
```

**Indexing for RAG** — download one file and chunk it:

```bash
curl -sL https://www.atomai.click/kubernetes-docs/llms-full-en.txt -o guidebook-en.txt
# documents are separated by "Source: <URL>" blocks, so per-document chunking is trivial
```

## Format notes

- `llms.txt` — a standard llms.txt index: `# title` / `>` summary / `## Docs (한국어)` / `## Docs (English)` / `## Optional`. Each entry is a link labeled with its group and title, so the taxonomy survives even in a flat list.
- `llms-full-*.txt` — every document is preceded by a separator block:

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture
----------------------------------------
```

- Size: the full files run several MiB. For most tools, pointing the model at the index and letting it fetch specific pages works better than pasting the whole book into one prompt.

## Diagrams are for people — the export links

Because the full files carry each document's markdown verbatim, every diagram's description (alt text) and its interactive viewer URL (`https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`) are in the text too. An LLM reads the description to understand the diagram; a person opens the URL and uses the viewer's **Export** menu to download PNG/JPEG/WebP, a dual-theme SVG, a 6-second trace-animation WebM, or a 1200×630 Share Card. Menu items, what each is for, and the LinkedIn posting recipe are laid out in the [Guidebook Roadmap](roadmap.md) under "Share a diagram — exports for LinkedIn and talks". Exports are communication assets, not evidence that an architecture was validated.
