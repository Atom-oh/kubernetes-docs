import { readFile, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

// Some Linux generic monospace fallbacks choose Droid Sans Fallback for only
// part of a Korean word, producing incomplete Hangul glyphs. Keep Latin
// monospace first, then name complete CJK families before generic fallbacks.
function cjkFamilies(fileName) {
  const locale = path.basename(fileName).split('-')[0]
  if (locale === 'jp') {
    return "'Noto Sans CJK JP', 'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic'"
  }
  if (locale === 'cn') {
    return "'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei'"
  }
  return "'Noto Sans CJK KR', 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic'"
}

export function archmapFontStack(fileName) {
  return `'JetBrains Mono', ${cjkFamilies(fileName)}, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`
}

export function normalizeArchmapFonts(html, fileName) {
  if (!html.includes('id="archify-i18n-data"')) return html
  // The same prefix occurs in the viewer CSS, SVG export CSS and canvas export
  // code. Replacing it consistently also keeps export measurement and drawing
  // on the same font stack. Already normalized files do not match again.
  return html.replaceAll(
    "'JetBrains Mono', ui-monospace",
    `'JetBrains Mono', ${cjkFamilies(fileName)}, ui-monospace`
  )
}

export async function normalizeArchmapFontsInDirectory(directory) {
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
    const normalized = normalizeArchmapFonts(original, entry.name)
    if (normalized === original) continue
    await writeFile(file, normalized)
    changed += 1
  }
  return changed
}
