import { spawn } from 'node:child_process'
import { createReadStream } from 'node:fs'
import {
  copyFile,
  mkdir,
  readdir,
  readFile,
  rename,
  rm,
  statfs,
  writeFile
} from 'node:fs/promises'
import { freemem } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  parseSitemap,
  SitemapStream,
  streamToPromise
} from 'sitemap'

import { supportedLocales } from '../.vitepress/site-scope.mjs'
import { generateLlmsFiles } from './generate-llms-txt.mjs'
import { normalizeArchmapFontsInDirectory } from './lib/archmap-fonts.mjs'
import { normalizeArchmapResponsiveLayoutsInDirectory } from './lib/archmap-responsive.mjs'
import { normalizeArchmapMotionInDirectory } from './lib/archmap-motion.mjs'

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

// Moves instead of copying so the merge does not hold a second copy of the
// site on disk. Falls back to copying across filesystems (EXDEV).
async function moveDirectoryContents(source, destination, skipSitemap = false) {
  await mkdir(destination, { recursive: true })

  for (const entry of await readdir(source, { withFileTypes: true })) {
    if (skipSitemap && entry.name === 'sitemap.xml') continue

    const sourcePath = path.join(source, entry.name)
    const destinationPath = path.join(destination, entry.name)

    try {
      await rename(sourcePath, destinationPath)
      continue
    } catch (error) {
      if (error.code === 'EXDEV') {
        if (entry.isDirectory()) await copyDirectoryContents(sourcePath, destinationPath)
        else await copyFile(sourcePath, destinationPath)
        continue
      }
      // A directory that already exists in the destination is merged entry by entry.
      if (!entry.isDirectory() || !['EEXIST', 'ENOTEMPTY'].includes(error.code)) throw error
    }
    await moveDirectoryContents(sourcePath, destinationPath)
  }
}

async function readAvailableMemoryBytes() {
  try {
    const meminfo = await readFile('/proc/meminfo', 'utf8')
    const kib = Number(meminfo.match(/^MemAvailable:\s+(\d+)\s+kB$/m)?.[1])
    if (Number.isFinite(kib)) return kib * 1024
  } catch {
    // not Linux: fall back to free memory, which under-reports page cache
  }
  return freemem()
}

const GIB = 1024 ** 3

// Refuses to start a build that would likely exhaust the host. The full
// two-locale build peaks at about 8 GB of heap per VitePress process and a few
// GB of disk for the staging and merged outputs.
export async function checkBuildResources({
  directory = projectRoot,
  minFreeDiskGb = Number(process.env.BUILD_MIN_FREE_DISK_GB ?? 6),
  minAvailableMemoryGb = Number(process.env.BUILD_MIN_AVAILABLE_MEMORY_GB ?? 10)
} = {}) {
  const fsStats = await statfs(directory)
  const freeDiskGb = (fsStats.bavail * fsStats.bsize) / GIB
  const availableMemoryGb = (await readAvailableMemoryBytes()) / GIB
  const problems = []
  if (freeDiskGb < minFreeDiskGb) {
    problems.push(`free disk ${freeDiskGb.toFixed(1)} GB < ${minFreeDiskGb} GB`)
  }
  if (availableMemoryGb < minAvailableMemoryGb) {
    problems.push(`available memory ${availableMemoryGb.toFixed(1)} GB < ${minAvailableMemoryGb} GB`)
  }
  return { freeDiskGb, availableMemoryGb, problems }
}

function logResources(label, { freeDiskGb, availableMemoryGb }) {
  console.log(`[resources] ${label}: free disk ${freeDiskGb.toFixed(1)} GB, available memory ${availableMemoryGb.toFixed(1)} GB`)
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

const SITE_ROOT = 'https://docs.atomai.click/kubernetes-docs/'

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

// Search results still link to README.html from before the README→index
// rewrite, including in the ko/en locales that are still published.
async function writeReadmeRedirects(destination) {
  let written = 0
  for (const locale of supportedLocales) {
    let pages
    try {
      pages = await listHtmlFiles(path.join(destination, locale))
    } catch (error) {
      if (error.code === 'ENOENT') continue
      throw error
    }
    for (const page of pages) {
      if (page !== 'index.html' && !page.endsWith('/index.html')) continue
      const directory = page.slice(0, -'index.html'.length)
      const target = `${SITE_ROOT}${locale}/${directory}`
      try {
        await writeFile(
          path.join(destination, locale, directory, 'README.html'),
          redirectStub(target),
          { flag: 'wx' }
        )
        written += 1
      } catch (error) {
        if (error.code !== 'EEXIST') throw error
      }
    }
  }
  return written
}

// `move: true` consumes the locale outputs (used for the temporary staging
// builds); the default copies, which keeps the sources intact.
export async function mergeLocaleOutputs(localeOutputs, destination, { move = false } = {}) {
  await rm(destination, { recursive: true, force: true })
  await mkdir(destination, { recursive: true })

  const mergeContents = move ? moveDirectoryContents : copyDirectoryContents
  for (const localeOutput of localeOutputs) {
    await mergeContents(localeOutput, destination, true)
  }

  await mergeSitemaps(
    localeOutputs.map((localeOutput) => path.join(localeOutput, 'sitemap.xml')),
    path.join(destination, 'sitemap.xml')
  )

  const fontsUpdated = await normalizeArchmapFontsInDirectory(path.join(destination, 'archmaps'))
  if (fontsUpdated > 0) console.log(`Normalized CJK fonts in ${fontsUpdated} archmap viewers`)

  const layoutsUpdated = await normalizeArchmapResponsiveLayoutsInDirectory(path.join(destination, 'archmaps'))
  if (layoutsUpdated > 0) console.log(`Updated mobile toolbars in ${layoutsUpdated} archmap viewers`)

  const motionUpdated = await normalizeArchmapMotionInDirectory(path.join(destination, 'archmaps'))
  if (motionUpdated > 0) console.log(`Updated optional motion controls in ${motionUpdated} archmap viewers`)

  const marked = await markArchmapsNoindex(destination)
  if (marked > 0) console.log(`Marked ${marked} archmap pages noindex`)

  const redirected = await writeLegacyLocaleRedirects(destination)
  if (redirected > 0) {
    console.log(`Wrote ${redirected} legacy ${LEGACY_LOCALES.join('/')} redirect stubs`)
  }

  // Generate these after retired-locale redirects so compatibility aliases
  // are not mistaken for canonical English pages when those targets are built.
  const readmesRedirected = await writeReadmeRedirects(destination)
  if (readmesRedirected > 0) {
    console.log(`Wrote ${readmesRedirected} ko/en README redirect stubs`)
  }
}

let activeChild = null

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

    activeChild = child
    child.on('error', reject)
    child.on('exit', (code, signal) => {
      activeChild = null
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

  const preflight = await checkBuildResources()
  logResources('before build', preflight)
  // CI runners are ephemeral and sized for this job, so there it only logs.
  const enforce = process.env.CI !== 'true' && process.env.BUILD_SKIP_RESOURCE_CHECK !== '1'
  if (preflight.problems.length > 0 && enforce) {
    throw new Error(
      `Not enough resources for a full docs build (${preflight.problems.join('; ')}). ` +
        'Free space or run the build in GitHub Actions (docs-build workflow). ' +
        'Set BUILD_SKIP_RESOURCE_CHECK=1 to override.'
    )
  }

  // Ctrl-C or a kill would otherwise leave the multi-GB staging tree behind.
  const cleanupAndExit = (signal) => {
    activeChild?.kill(signal)
    rm(stagingRoot, { recursive: true, force: true }).finally(() => process.exit(128 + (signal === 'SIGINT' ? 2 : 15)))
  }
  process.once('SIGINT', cleanupAndExit)
  process.once('SIGTERM', cleanupAndExit)

  await rm(stagingRoot, { recursive: true, force: true })

  console.log('Generating llms.txt endpoints')
  generateLlmsFiles()

  try {
    for (const [index, locale] of supportedLocales.entries()) {
      console.log(
        `\n[${index + 1}/${supportedLocales.length}] Building ${locale} documentation`
      )
      await runVitepressBuild(locale, localeOutputs[index])
      logResources(`after ${locale} build`, await checkBuildResources())
    }

    console.log('\nMerging locale build outputs')
    await mergeLocaleOutputs(localeOutputs, destination, { move: true })
    logResources('after merge', await checkBuildResources())
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
