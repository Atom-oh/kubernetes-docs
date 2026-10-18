import fs from 'node:fs'
import path from 'node:path'

// Parses SUMMARY.md (GitBook nav format) into a VitePress sidebar.
// Input: `## Section` headers, `* [Title](path.md)` items, nested by indent.
// Entries whose page does not exist are left out: cn/jp/es SUMMARY.md files
// list the whole en tree, but only part of it is translated yet.
export function summarySidebar(lang: string) {
  const localeRoot = path.join(__dirname, '..', lang)
  const src = fs.readFileSync(path.join(localeRoot, 'SUMMARY.md'), 'utf8')
  const sidebar: any[] = []
  let stack: { indent: number; items: any[] }[] = []

  for (const line of src.split('\n')) {
    const h = line.match(/^## (.+)/)
    if (h) {
      const group = { text: h[1].trim(), collapsed: true, items: [] as any[] }
      sidebar.push(group)
      stack = [{ indent: -1, items: group.items }]
      continue
    }
    const m = line.match(/^( *)\* (?:\[(.+?)\]\((.+?)\)|(.+))/)
    if (!m || !stack.length) continue
    const indent = m[1].length
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) stack.pop()
    const item: any = m[3]
      ? { text: m[2], link: `/${lang}/${m[3].replace(/(^|\/)README\.md$/, '$1').replace(/\.md$/, '')}`, source: m[3] }
      : { text: m[4].trim(), collapsed: true }
    item.items = []
    stack[stack.length - 1].items.push(item)
    stack.push({ indent, items: item.items })
  }
  // Drop links to missing pages (keeping their children), then label-only
  // entries and groups left with nothing under them.
  const keep = (list: any[]): any[] =>
    list.flatMap(i => {
      const items = keep(i.items ?? [])
      if (i.link && !fs.existsSync(path.join(localeRoot, i.source.replace(/[?#].*$/, '')))) return items
      if (!i.link && !items.length) return []
      const { source, ...item } = i
      return [{ ...item, items }]
    })
  // Leaves get an empty items array from the loop above; strip it so they render as plain links.
  const prune = (list: any[]) => list.forEach(i => { i.items?.length ? prune(i.items) : delete i.items })
  const kept = keep(sidebar)
  prune(kept)
  return kept
}
