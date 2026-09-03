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
