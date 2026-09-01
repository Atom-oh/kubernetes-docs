# Reading with LLMs — llms.txt

> **Last Updated**: September 1, 2026

The entire guidebook is published under the [llms.txt convention](https://llmstxt.org/). Hand a single URL to ChatGPT, Claude, or your in-house RAG pipeline and this book becomes a knowledge source.

## Endpoints

| URL | Contents | Use it for |
|-----|----------|-----------|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | Index of every document (title + URL) | Letting an LLM pick and fetch only the pages it needs |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | Full Korean content (markdown) | Whole-book context or RAG indexing |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | Full English content (markdown) | English-language tools and pipelines |

All three files are regenerated on every site deploy, so they always match the published content. Quizzes are listed in the index but excluded from the full files — answer keys don't belong in an LLM's context.

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

- `llms.txt` — a standard llms.txt index: `# title` / `>` summary / `## Docs (한국어)` / `## Docs (English)` / `## Optional`. Each entry reads `- [Group · Title](URL)`, so the taxonomy survives even in a flat list.
- `llms-full-*.txt` — every document is preceded by a separator block:

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture
----------------------------------------
```

- Size: the full files run several MiB. For most tools, pointing the model at the index and letting it fetch specific pages works better than pasting the whole book into one prompt.
