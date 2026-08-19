# VitePress Korean and English Build Design

## Goal

Keep GitBook publishing all five languages from the existing Markdown tree while
limiting the GitHub Pages VitePress build to Korean and English. Fix the
repository issues that directly affect publishing quality without introducing
Docusaurus or duplicating content.

## Publishing Boundaries

- GitBook continues to read `ko/`, `en/`, `cn/`, `jp/`, and `es/`.
- VitePress reads the repository root but excludes `cn/`, `jp/`, and `es/`.
- The repository `README.md` remains the five-language selector.
- A separate root `index.md` becomes the VitePress landing page and links only
  to `/ko/` and `/en/`.
- Shared assets remain under `assets/`.

## Validation

Add repository scripts that validate:

1. Local Markdown links for the source languages used by each publishing path.
2. Referenced PNG dimensions so 1x1 placeholder diagrams cannot be published.
3. VitePress source scope so translated mirror directories cannot silently
   re-enter the GitHub Pages build.

VitePress dead-link checking will be enabled after existing Korean and English
link errors are corrected.

## Diagrams

- Delete unused 1x1 PNG exports under `assets/generated-diagrams/`; retain their
  Draw.io sources.
- Replace the referenced 1x1 observability lab images with shared SVG diagrams.
- Keep diagram source and rendered output distinct for newly repaired diagrams.
- Update the Pages workflow to copy interactive HTML assets recursively if they
  become referenced.

## Quiz Compatibility

GitBook must continue to render every quiz as ordinary Markdown with
`<details>` answer blocks. VitePress may progressively enhance those pages:

- Quiz state exists only in the browser.
- Storage keys use the locale and route.
- Opening an answer marks a question reviewed.
- Progress is restored from `localStorage`.
- No account, server synchronization, or content-format migration is included.

This MVP intentionally tracks review progress rather than attempting automatic
answer grading from unstructured Markdown.

## Navigation

`quizzes/` remains the location of real quiz content. `quiz/` placeholder pages
are replaced by label-only `SUMMARY.md` groups. The sidebar parser already
supports label-only groups; translation navigation synchronization must preserve
them without requiring fake files.

## Non-Goals

- Moving the project to Docusaurus.
- Rewriting translated content.
- Adding authentication or a backend.
- Writing the proposed Kueue, KubeVirt, multi-cluster, and stateful workload
  curriculum in this change.

## Acceptance Criteria

- GitBook source directories for all languages remain present.
- VitePress produces routes and search data only for Korean and English.
- Korean and English dead links fail validation.
- No referenced 1x1 PNG remains.
- Quiz answer-review progress survives a reload in VitePress.
- The ko/en VitePress build completes in the available environment, or the
  remaining memory requirement is measured and documented.
