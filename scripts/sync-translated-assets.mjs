import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { extractLocalTargets, resolveLocalTarget, stripFencedCode } from './validate-local-links.mjs'

const IMAGE = /\.(png|jpe?g|gif|webp|svg|avif|ico)(?:[?#]|$)/i

function markdownFiles(directory) {
  if (!fs.existsSync(directory)) return []
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(directory, entry.name)
    return entry.isDirectory() ? markdownFiles(file) : entry.name.endsWith('.md') ? [file] : []
  })
}

function repairImagePaths(markdown, englishFile, translatedFile, root) {
  if (!fs.existsSync(englishFile)) return { text: markdown, changes: [] }
  const canonical = new Map()
  for (const { target } of extractLocalTargets(stripFencedCode(fs.readFileSync(englishFile, 'utf8')))) {
    if (!IMAGE.test(target)) continue
    if (!resolveLocalTarget(englishFile, target, root).some(file => fs.existsSync(file))) continue
    const key = path.basename(target.split(/[?#]/)[0]).toLowerCase()
    if (canonical.has(key) && canonical.get(key) !== target) canonical.set(key, null)
    else canonical.set(key, target)
  }
  const changes = []
  let fence = null
  const text = markdown.split('\n').map((line, index) => {
    const marker = line.match(/^\s*(?:>\s*)*(`{3,}|~{3,})/)
    if (marker) {
      if (!fence) fence = marker[1]
      else if (marker[1][0] === fence[0] && marker[1].length >= fence.length) fence = null
      return line
    }
    if (fence) return line
    // Work backwards so replacing a destination cannot shift earlier spans.
    for (const { target, targetStart, targetEnd } of extractLocalTargets(line).reverse()) {
      if (!IMAGE.test(target) || resolveLocalTarget(translatedFile, target, root).some(file => fs.existsSync(file))) continue
      const replacement = canonical.get(path.basename(target.split(/[?#]/)[0]).toLowerCase())
      if (!replacement || replacement === target) continue
      line = line.slice(0, targetStart) + replacement + line.slice(targetEnd)
      changes.push({ file: path.relative(root, translatedFile), line: index + 1, from: target, to: replacement })
    }
    return line
  }).join('\n')
  return { text, changes }
}

// Translation deliberately preserves source paths. Locale-owned images
// therefore need the same English bytes under the destination locale too.
// Copy only referenced assets; never modify translated prose or shared assets.
export function syncTranslatedAssets(root = process.cwd(), locales = ['cn', 'jp', 'es']) {
  const copied = []
  const unresolved = []
  const repairedLinks = []
  const seen = new Set()
  for (const locale of locales) {
    if (!['cn', 'jp', 'es'].includes(locale)) throw new Error(`Invalid translation locale: ${locale}`)
    const localeRoot = path.join(root, locale)
    for (const file of markdownFiles(localeRoot)) {
      const markdown = fs.readFileSync(file, 'utf8')
      const repaired = repairImagePaths(markdown, path.join(root, 'en', path.relative(localeRoot, file)), file, root)
      if (repaired.changes.length) {
        fs.writeFileSync(file, repaired.text)
        repairedLinks.push(...repaired.changes)
      }
      const source = stripFencedCode(repaired.text)
      for (const { target, line } of extractLocalTargets(source)) {
        if (!IMAGE.test(target)) continue
        const [destination] = resolveLocalTarget(file, target, root)
        if (!destination) continue
        const relative = path.relative(localeRoot, destination)
        if (relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
          if (!fs.existsSync(destination)) unresolved.push({ file: path.relative(root, file), line, target })
          continue
        }
        const englishAsset = path.join(root, 'en', relative)
        if (!fs.existsSync(englishAsset) || !fs.statSync(englishAsset).isFile()) {
          if (!fs.existsSync(destination)) unresolved.push({ file: path.relative(root, file), line, target })
          continue
        }
        if (seen.has(destination)) continue
        seen.add(destination)
        const bytes = fs.readFileSync(englishAsset)
        if (fs.existsSync(destination) && fs.readFileSync(destination).equals(bytes)) continue
        fs.mkdirSync(path.dirname(destination), { recursive: true })
        fs.writeFileSync(destination, bytes)
        copied.push({ source: path.relative(root, englishAsset), destination: path.relative(root, destination) })
      }
    }
  }
  return { copied, unresolved, repairedLinks }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = syncTranslatedAssets()
  console.log(`Synchronized ${result.copied.length} translated image asset(s).`)
  console.log(`Repaired ${result.repairedLinks.length} stale image path(s) from the English source.`)
  for (const item of result.unresolved) console.error(`${item.file}:${item.line} -> ${item.target}`)
  if (result.unresolved.length) process.exitCode = 1
}
