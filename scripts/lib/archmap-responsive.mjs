import { readFile, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const STYLE_ID = 'docs-archmap-responsive'
const RESPONSIVE_STYLE = `
<style id="${STYLE_ID}">
@media (max-width: 960px) {
  html:not([data-embed="true"]) .toolbar,
  html[data-present="true"]:not([data-embed="true"]) .toolbar {
    position: static;
    inset: auto;
    width: 100%;
    max-width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
    margin: 0 0 1rem;
    flex: none;
  }
  html:not([data-embed="true"]) .header,
  html[data-present="true"]:not([data-embed="true"]) .header {
    padding-right: 0;
  }
  html:not([data-embed="true"]) .toolbar .preset-menu,
  html:not([data-embed="true"]) .toolbar .export-menu {
    position: fixed;
    top: 1rem;
    right: 1rem;
    left: 1rem;
    width: auto;
    max-width: none;
    max-height: calc(100dvh - 2rem);
    overflow-y: auto;
  }
  html[data-present="true"]:not([data-embed="true"]) body {
    display: flex;
    flex-direction: column;
  }
  html[data-present="true"]:not([data-embed="true"]) .container {
    flex: 1 1 auto;
    min-height: 0;
    height: auto;
  }
}
</style>
`

export function normalizeArchmapResponsiveLayout(html) {
  if (!html.includes('id="archify-i18n-data"') || html.includes(`id="${STYLE_ID}"`)) return html
  return html.replace(/<\/head>/i, `${RESPONSIVE_STYLE}</head>`)
}

export async function normalizeArchmapResponsiveLayoutsInDirectory(directory) {
  let entries
  try {
    entries = await readdir(directory, { withFileTypes: true })
  } catch (error) {
    if (error.code === 'ENOENT') return 0
    throw error
  }
  let changed = 0
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith('.html') || entry.name.includes('.visual-check.')) continue
    const file = path.join(directory, entry.name)
    const original = await readFile(file, 'utf8')
    const normalized = normalizeArchmapResponsiveLayout(original)
    if (normalized === original) continue
    await writeFile(file, normalized)
    changed += 1
  }
  return changed
}
