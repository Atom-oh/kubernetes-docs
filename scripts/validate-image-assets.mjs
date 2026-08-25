#!/usr/bin/env node

import { existsSync } from 'node:fs'
import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { resolveLocalTarget, stripFencedCode } from './validate-local-links.mjs'

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
const REMOTE_OR_DYNAMIC_TARGET = /^(?:[a-z][a-z0-9+.-]*:|\/\/|\{\{|\{%)/i

export function readPngDimensions(buffer) {
  if (
    buffer.length < 24 ||
    !buffer.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE) ||
    buffer.toString('ascii', 12, 16) !== 'IHDR'
  ) {
    throw new Error('Image is not a valid PNG with an IHDR header.')
  }

  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20)
  }
}

export function isPlaceholderPng(buffer, minimumDimension = 16) {
  const { width, height } = readPngDimensions(buffer)
  return width < minimumDimension || height < minimumDimension
}

function extractPngTargets(markdown) {
  const targets = []
  const patterns = [
    /!\[[^\]]*]\(\s*(?:<([^>]+)>|([^\s)]+))/g,
    /<img\b[^>]*?\bsrc=["']([^"']+)["'][^>]*>/gi
  ]

  for (const pattern of patterns) {
    for (const match of markdown.matchAll(pattern)) {
      const target = (match[1] || match[2] || '').trim()
      if (
        target.toLowerCase().split(/[?#]/, 1)[0].endsWith('.png') &&
        !REMOTE_OR_DYNAMIC_TARGET.test(target)
      ) {
        targets.push(target)
      }
    }
  }

  return targets
}

async function collectFiles(directory, predicate) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await collectFiles(entryPath, predicate))
    else if (entry.isFile() && predicate(entryPath)) files.push(entryPath)
  }

  return files
}

export async function validateImageAssets(repositoryRoot, locales = ['ko', 'en']) {
  const imagePaths = new Set()

  for (const locale of locales) {
    const localeRoot = path.join(repositoryRoot, locale)
    const markdownFiles = await collectFiles(localeRoot, (file) => file.endsWith('.md'))

    for (const sourcePath of markdownFiles) {
      const markdown = stripFencedCode(await readFile(sourcePath, 'utf8'))
      for (const target of extractPngTargets(markdown)) {
        const imagePath = resolveLocalTarget(sourcePath, target, repositoryRoot)
          .find((candidate) => existsSync(candidate))
        if (imagePath) imagePaths.add(imagePath)
      }
    }
  }

  const generatedDirectory = path.join(repositoryRoot, 'assets/generated-diagrams')
  if (existsSync(generatedDirectory)) {
    const generatedPngs = await collectFiles(
      generatedDirectory,
      (file) => file.toLowerCase().endsWith('.png')
    )
    generatedPngs.forEach((file) => imagePaths.add(file))
  }

  const failures = []
  for (const imagePath of imagePaths) {
    const buffer = await readFile(imagePath)
    try {
      if (isPlaceholderPng(buffer)) {
        failures.push({
          imagePath,
          ...readPngDimensions(buffer)
        })
      }
    } catch (error) {
      failures.push({
        imagePath,
        error: error.message
      })
    }
  }

  return failures
}

async function main() {
  const repositoryRoot = path.resolve(process.cwd())
  const failures = await validateImageAssets(repositoryRoot)

  if (failures.length === 0) {
    console.log('Referenced PNG validation passed for ko/en.')
    return
  }

  for (const failure of failures) {
    const imagePath = path.relative(repositoryRoot, failure.imagePath)
    const detail = failure.error || `${failure.width}x${failure.height}`
    console.error(`${imagePath}: ${detail}`)
  }
  console.error(`Found ${failures.length} invalid or placeholder PNG asset(s).`)
  process.exitCode = 1
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await main()
}
