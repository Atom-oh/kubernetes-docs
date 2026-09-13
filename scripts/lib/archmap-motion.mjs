import { readFile, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

// Some generated viewers expose only count/active when no guided views exist.
// Guard both optional methods before synchronizing a transition to still.
export function normalizeArchmapMotion(html) {
  if (!html.includes('id="archify-i18n-data"')) return html
  return html.replaceAll(
    'Archify.guidedViews && Archify.guidedViews.isPlaying())',
    "Archify.guidedViews && typeof Archify.guidedViews.isPlaying === 'function' && typeof Archify.guidedViews.pause === 'function' && Archify.guidedViews.isPlaying())"
  )
}

export async function normalizeArchmapMotionInDirectory(directory) {
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
    const normalized = normalizeArchmapMotion(original)
    if (normalized === original) continue
    await writeFile(file, normalized)
    changed += 1
  }
  return changed
}
