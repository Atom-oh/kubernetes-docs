import { spawn } from 'node:child_process'
import { createReadStream } from 'node:fs'
import {
  copyFile,
  mkdir,
  readdir,
  readFile,
  rm,
  writeFile
} from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  parseSitemap,
  SitemapStream,
  streamToPromise
} from 'sitemap'

import { supportedLocales } from '../.vitepress/site-scope.mjs'
import { generateLlmsFiles } from './generate-llms-txt.mjs'

const scriptPath = fileURLToPath(import.meta.url)
const projectRoot = path.resolve(path.dirname(scriptPath), '..')
const vitepressCli = path.join(
  projectRoot,
  'node_modules',
  'vitepress',
  'bin',
  'vitepress.js'
)

async function copyDirectoryContents(source, destination, skipSitemap = false) {
  await mkdir(destination, { recursive: true })

  for (const entry of await readdir(source, { withFileTypes: true })) {
    if (skipSitemap && entry.name === 'sitemap.xml') continue

    const sourcePath = path.join(source, entry.name)
    const destinationPath = path.join(destination, entry.name)

    if (entry.isDirectory()) {
      await copyDirectoryContents(sourcePath, destinationPath)
    } else {
      await copyFile(sourcePath, destinationPath)
    }
  }
}

async function mergeSitemaps(sitemapPaths, destination) {
  const items = (
    await Promise.all(
      sitemapPaths.map((sitemapPath) =>
        parseSitemap(createReadStream(sitemapPath))
      )
    )
  ).flat()
  const uniqueItems = [...new Map(items.map((item) => [item.url, item])).values()]
  const sitemapStream = new SitemapStream()

  for (const item of uniqueItems) sitemapStream.write(item)
  sitemapStream.end()

  await writeFile(destination, await streamToPromise(sitemapStream))
}

const NOINDEX_META = '<meta name="robots" content="noindex, follow">'

// The archmap viewers are standalone diagram pages linked from the docs. They
// are thin, duplicate the diagram already embedded in the article, and would
// otherwise compete with it in search. robots.txt is deliberately not used
// here: disallowing the path would stop crawlers from ever reading this tag.
export async function markArchmapsNoindex(destination) {
  const archmaps = path.join(destination, 'archmaps')
  let entries
  try {
    entries = await readdir(archmaps, { withFileTypes: true })
  } catch {
    return 0
  }

  let marked = 0
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith('.html')) continue
    const filePath = path.join(archmaps, entry.name)
    const html = await readFile(filePath, 'utf8')
    if (html.includes('name="robots"')) continue
    const headIndex = html.indexOf('<head>')
    if (headIndex === -1) continue
    const insertAt = headIndex + '<head>'.length
    await writeFile(
      filePath,
      `${html.slice(0, insertAt)}\n  ${NOINDEX_META}${html.slice(insertAt)}`
    )
    marked += 1
  }
  return marked
}

const SITE_ROOT = 'https://www.atomai.click/kubernetes-docs/'

// Locales that were once published here (five-locale build, .html URLs) and
// still sit in search indexes; those URLs now 404. Only ko/en are built, so
// each legacy URL gets a stub that redirects to the English twin — a 0-second
// meta refresh is treated as a permanent redirect by Google, which lets the
// stale entries hand their ranking to the live page instead of decaying as
// 404s. GitHub Pages has no server-side redirects, hence stubs.
export const LEGACY_LOCALES = ['cn', 'jp', 'es']

function redirectStub(target) {
  return [
    '<!doctype html>',
    '<html lang="en"><head><meta charset="utf-8">',
    `<meta http-equiv="refresh" content="0; url=${target}">`,
    `<link rel="canonical" href="${target}">`,
    '<title>Redirecting…</title></head>',
    `<body><a href="${target}">${target}</a></body></html>`,
    ''
  ].join('\n')
}

async function listHtmlFiles(directory, prefix = '') {
  const files = []
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name
    if (entry.isDirectory()) {
      files.push(...(await listHtmlFiles(path.join(directory, entry.name), relative)))
    } else if (entry.name.endsWith('.html')) {
      files.push(relative)
    }
  }
  return files
}

export async function writeLegacyLocaleRedirects(destination, sourceLocale = 'en') {
  let pages
  try {
    pages = await listHtmlFiles(path.join(destination, sourceLocale))
  } catch {
    return 0
  }

  let written = 0
  for (const page of pages) {
    const isIndex = page === 'index.html' || page.endsWith('/index.html')
    const cleanPath = isIndex
      ? page.slice(0, -'index.html'.length)
      : page.replace(/\.html$/, '')
    const target = `${SITE_ROOT}${sourceLocale}/${cleanPath}`
    const stub = redirectStub(target)

    // The old build had no README→index rewrite, so section indexes were
    // published as README.html; cover both spellings.
    const variants = isIndex
      ? [page, `${cleanPath}README.html`]
      : [page]

    for (const locale of LEGACY_LOCALES) {
      for (const variant of variants) {
        const filePath = path.join(destination, locale, variant)
        await mkdir(path.dirname(filePath), { recursive: true })
        await writeFile(filePath, stub)
        written += 1
      }
    }
  }
  return written
}

export async function mergeLocaleOutputs(localeOutputs, destination) {
  await rm(destination, { recursive: true, force: true })
  await mkdir(destination, { recursive: true })

  for (const localeOutput of localeOutputs) {
    await copyDirectoryContents(localeOutput, destination, true)
  }

  await mergeSitemaps(
    localeOutputs.map((localeOutput) => path.join(localeOutput, 'sitemap.xml')),
    path.join(destination, 'sitemap.xml')
  )

  const marked = await markArchmapsNoindex(destination)
  if (marked > 0) console.log(`Marked ${marked} archmap pages noindex`)

  const redirected = await writeLegacyLocaleRedirects(destination)
  if (redirected > 0) {
    console.log(`Wrote ${redirected} legacy ${LEGACY_LOCALES.join('/')} redirect stubs`)
  }
}

function runVitepressBuild(locale, outputDirectory) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        vitepressCli,
        'build',
        projectRoot,
        '--outDir',
        outputDirectory
      ],
      {
        cwd: projectRoot,
        env: {
          ...process.env,
          VITEPRESS_BUILD_LOCALE: locale
        },
        stdio: 'inherit'
      }
    )

    child.on('error', reject)
    child.on('exit', (code, signal) => {
      if (code === 0) {
        resolve()
        return
      }

      reject(
        new Error(
          `VitePress ${locale} build failed with ${
            signal ? `signal ${signal}` : `exit code ${code}`
          }`
        )
      )
    })
  })
}

async function buildAllLocales() {
  const stagingRoot = path.join(projectRoot, '.vitepress', '.locale-builds')
  const destination = path.join(projectRoot, '.vitepress', 'dist')
  const localeOutputs = supportedLocales.map((locale) =>
    path.join(stagingRoot, locale)
  )

  await rm(stagingRoot, { recursive: true, force: true })

  console.log('Generating llms.txt endpoints')
  generateLlmsFiles()

  try {
    for (const [index, locale] of supportedLocales.entries()) {
      console.log(
        `\n[${index + 1}/${supportedLocales.length}] Building ${locale} documentation`
      )
      await runVitepressBuild(locale, localeOutputs[index])
    }

    console.log('\nMerging locale build outputs')
    await mergeLocaleOutputs(localeOutputs, destination)
  } finally {
    await rm(stagingRoot, { recursive: true, force: true })
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === scriptPath) {
  buildAllLocales().catch((error) => {
    console.error(error)
    process.exitCode = 1
  })
}
