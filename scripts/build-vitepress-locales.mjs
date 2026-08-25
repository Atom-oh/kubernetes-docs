import { spawn } from 'node:child_process'
import { createReadStream } from 'node:fs'
import {
  copyFile,
  mkdir,
  readdir,
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
