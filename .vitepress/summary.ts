import fs from 'node:fs'
import path from 'node:path'

// Parses SUMMARY.md (GitBook nav format) into a VitePress sidebar.
// Input: `## Section` headers, `* [Title](path.md)` items, nested by indent.
export function summarySidebar(lang: string) {
  const src = fs.readFileSync(path.join(__dirname, '..', lang, 'SUMMARY.md'), 'utf8')
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
      ? { text: m[2], link: m[3] === 'README.md' ? `/${lang}/` : `/${lang}/${m[3].replace(/\.md$/, '')}` }
      : { text: m[4].trim(), collapsed: true }
    item.items = []
    stack[stack.length - 1].items.push(item)
    stack.push({ indent, items: item.items })
  }
  // Leaves get an empty items array from the loop above; strip it so they render as plain links.
  const prune = (list: any[]) => list.forEach(i => { i.items?.length ? prune(i.items) : delete i.items })
  prune(sidebar)
  return sidebar
}
