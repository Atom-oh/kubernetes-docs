# Reading with LLMs — llms.txt Quiz

1. What does this guidebook's `llms.txt` file contain, and what is it for?
   - A) The full Korean content in markdown, for pasting whole into a context window
   - B) An index of every content page (title + URL), for letting an LLM pick and fetch only the pages it needs
   - C) A collection of quiz answer keys, for automated grading
   - D) A bundle of diagram PNGs, for building slides
<details>
<summary>Show Answer</summary>

**Answer: B) An index of every content page (title + URL), for letting an LLM pick and fetch only the pages it needs**

**Explanation:**
In the endpoints table, `llms.txt` is the "Index of every content page (title + URL)", used for "Letting an LLM pick and fetch only the pages it needs". The full markdown content lives in the separate `llms-full-ko.txt` / `llms-full-en.txt` files. The index follows the standard llms.txt layout — `# title` / `>` summary / `## Docs (한국어)` / `## Docs (English)` / `## Optional` — and each entry is labeled with its group and title, so the taxonomy survives even in a flat list. Quizzes and labs are not listed page by page; `## Optional` carries one quiz-index link and one lab-index link per language.

</details>

2. In which languages are the full-content files published?
   - A) Korean only (`llms-full-ko.txt`)
   - B) Korean and English — two files (`llms-full-ko.txt`, `llms-full-en.txt`)
   - C) Five languages: Korean, English, Chinese, Japanese, and Spanish
   - D) A single `llms-full.txt` with every language merged together
<details>
<summary>Show Answer</summary>

**Answer: B) Korean and English — two files (`llms-full-ko.txt`, `llms-full-en.txt`)**

**Explanation:**
The endpoints table lists exactly three files: `llms.txt` (the index), `llms-full-ko.txt` (full Korean content), and `llms-full-en.txt` (full English content), all served under `https://www.atomai.click/kubernetes-docs/`. The Korean file is recommended for "Whole-book context or RAG indexing" and the English one for "English-language tools and pipelines".

</details>

3. Why do `llms.txt` and the full files always match the published content?
   - A) The author re-uploads the three files by hand after every edit
   - B) A weekly news-digest workflow refreshes them
   - C) All three files are regenerated on every site deploy
   - D) The server converts the documents on the fly for each LLM request
<details>
<summary>Show Answer</summary>

**Answer: C) All three files are regenerated on every site deploy**

**Explanation:**
The page states: "All three files are regenerated on every site deploy, so they always match the published content." They are build outputs of the deploy pipeline — not manual uploads and not on-demand conversions.

</details>

4. How are quiz documents handled in `llms.txt` and the full files?
   - A) Every quiz page appears in both the index and the full files, answer keys included
   - B) Only the quiz index page is linked (one link per language), under `## Optional` in `llms.txt`; individual quiz pages and their answer keys are left out of both the index and the full files
   - C) Every individual quiz page is listed in the index, but the full files drop them
   - D) Quiz pages appear in the full files but are excluded from the index
<details>
<summary>Show Answer</summary>

**Answer: B) Only the quiz index page is linked (one link per language), under `## Optional` in `llms.txt`; individual quiz pages and their answer keys are left out of both the index and the full files**

**Explanation:**
The page says: "Quizzes appear in `llms.txt` only as a link to the quiz index page (one per language) under `## Optional`; individual quiz pages (with their answer keys) are left out of both the index and the full files — answer keys don't belong in an LLM's context." So an LLM can discover that quizzes exist and where each language's quiz index lives, but neither the flat index nor the whole-book files ever carry a single quiz page or its answers. Lab guides differ: they are also only an index link in `llms.txt`, but their full text is included in the full files.

</details>

5. Given the size of the full files, which way of using them with an LLM does the page recommend?
   - A) Paste the multi-MiB full file into every prompt — it is the most accurate approach
   - B) Split the full file into several pieces and attach all of them every time
   - C) Point the model at the index and let it fetch specific pages — this works better with most tools
   - D) Hand over only the diagram viewer URLs and let the LLM infer the rest
<details>
<summary>Show Answer</summary>

**Answer: C) Point the model at the index and let it fetch specific pages — this works better with most tools**

**Explanation:**
The "Size" note says the full files run several MiB and that "for most tools, pointing the model at the index and letting it fetch specific pages works better than pasting the whole book into one prompt." The first example prompt ("Read …/llms.txt, find the document … and summarize …") is exactly this pattern. The full files suit whole-file download-and-chunk uses such as RAG indexing.

</details>

6. Why is per-document chunking of `llms-full-*.txt` described as trivial?
   - A) Each document is stored as a separate ZIP entry
   - B) Every document is preceded by a separator block containing `Source: <URL>`
   - C) Each document is cut to a fixed 4,096 characters
   - D) The documents are stored one per element in a JSON array
<details>
<summary>Show Answer</summary>

**Answer: B) Every document is preceded by a separator block containing `Source: <URL>`**

**Explanation:**
Under "Format notes", "every document is preceded by a separator block" — a dashed line, a `Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture`-style URL, and another dashed line. The RAG example's comment repeats it: "documents are separated by `Source: <URL>` blocks, so per-document chunking is trivial." The file is plain markdown text, not ZIP or JSON.

</details>

7. How does the page describe the way an LLM and a person each use the diagram information carried in the full files?
   - A) The LLM analyzes the PNG image directly while the person reads the alt text
   - B) The LLM reads the diagram's description (alt text) to understand it, while a person opens the interactive viewer URL and uses the Export menu to download PNG/JPEG/WebP, SVG, WebM, or a Share Card
   - C) Neither the LLM nor a person can get any diagram information from the full files
   - D) The LLM renders a WebM animation from the viewer URL and hands it to the person
<details>
<summary>Show Answer</summary>

**Answer: B) The LLM reads the diagram's description (alt text) to understand it, while a person opens the interactive viewer URL and uses the Export menu to download PNG/JPEG/WebP, SVG, WebM, or a Share Card**

**Explanation:**
The "Diagrams are for people — the export links" section explains that because the full files carry each document's markdown verbatim, every diagram's alt text and its viewer URL (`https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`) are in the text. "An LLM reads the description to understand the diagram; a person opens the URL and uses the viewer's **Export** menu to download PNG/JPEG/WebP, a dual-theme SVG, a 6-second trace-animation WebM, or a 1200×630 Share Card." The per-item guidance lives in the Guidebook Roadmap's "Share a diagram" section.

</details>

8. What limit does the page place on diagram files exported from the viewer (PNG, SVG, WebM, Share Card)?
   - A) Exports may be used as formal evidence that the architecture was validated
   - B) Exports are communication assets, not evidence that an architecture was validated
   - C) Exports are for LLMs only and cannot be opened by people
   - D) Exports are the official release form of the document and replace the source HTML
<details>
<summary>Show Answer</summary>

**Answer: B) Exports are communication assets, not evidence that an architecture was validated**

**Explanation:**
The section closes with: "Exports are communication assets, not evidence that an architecture was validated." Exporting a diagram serves sharing purposes such as LinkedIn posts or talk slides; the existence of the image says nothing about whether the architecture it depicts has been validated.

</details>
