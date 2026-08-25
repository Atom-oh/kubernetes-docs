#!/usr/bin/env node

import { existsSync } from 'node:fs'
import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const REMOTE_OR_DYNAMIC_TARGET = /^(?:[a-z][a-z0-9+.-]*:|\/\/|#|\{\{|\{%)/i

export function stripFencedCode(markdown) {
  let activeFence = null

  return markdown
    .split('\n')
    .map((line) => {
      const fence = line.match(/^\s*(`{3,}|~{3,})/)
      if (!fence) return activeFence ? '' : line

      const marker = fence[1][0]
      if (!activeFence) activeFence = marker
      else if (activeFence === marker) activeFence = null
      return ''
    })
    .join('\n')
}

function lineNumberAt(source, index) {
  return source.slice(0, index).split('\n').length
}

function isLocalTarget(target) {
  return target && !REMOTE_OR_DYNAMIC_TARGET.test(target)
}

export function extractLocalTargets(markdown) {
  const matches = []
  const patterns = [
    /!?\[[^\]]*]\(\s*(?:<([^>]+)>|([^\s)]+))/g,
    /<(?:a|img)\b[^>]*?\b(?:href|src)=["']([^"']+)["'][^>]*>/gi,
    /^\s*\[[^\]]+]:\s*(?:<([^>]+)>|(\S+))/gm
  ]

  for (const pattern of patterns) {
    for (const match of markdown.matchAll(pattern)) {
      const target = (match[1] || match[2] || '').trim()
      if (!isLocalTarget(target)) continue
      matches.push({
        target,
        line: lineNumberAt(markdown, match.index),
        index: match.index
      })
    }
  }

  return matches.sort((left, right) => left.index - right.index)
}

function withoutQueryOrFragment(target) {
  const end = target.search(/[?#]/)
  const value = end === -1 ? target : target.slice(0, end)
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

export function requiresExplicitReadmeTarget(target) {
  if (!isLocalTarget(target)) return false
  return withoutQueryOrFragment(target).endsWith('/')
}

export function resolveLocalTarget(sourcePath, target, repositoryRoot) {
  const cleanTarget = withoutQueryOrFragment(target)
  if (!cleanTarget) return []

  let resolved
  if (cleanTarget.startsWith('/kubernetes-docs/')) {
    resolved = path.join(repositoryRoot, cleanTarget.slice('/kubernetes-docs/'.length))
  } else if (cleanTarget.startsWith('/')) {
    resolved = path.join(repositoryRoot, cleanTarget.slice(1))
  } else {
    resolved = path.resolve(path.dirname(sourcePath), cleanTarget)
  }

  if (cleanTarget.endsWith('/')) {
    return [path.join(resolved, 'README.md')]
  }

  if (path.extname(resolved)) {
    return [resolved]
  }

  return [resolved, `${resolved}.md`, path.join(resolved, 'README.md')]
}

async function collectMarkdownFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await collectMarkdownFiles(entryPath))
    else if (entry.isFile() && entry.name.endsWith('.md')) files.push(entryPath)
  }

  return files
}

export async function validateLocalLinks(repositoryRoot, locales = ['ko', 'en']) {
  const failures = []

  for (const locale of locales) {
    const localeRoot = path.join(repositoryRoot, locale)
    const files = await collectMarkdownFiles(localeRoot)

    for (const sourcePath of files) {
      const markdown = stripFencedCode(await readFile(sourcePath, 'utf8'))
      for (const link of extractLocalTargets(markdown)) {
        const candidates = resolveLocalTarget(sourcePath, link.target, repositoryRoot)
        if (
          !requiresExplicitReadmeTarget(link.target) &&
          candidates.length > 0 &&
          candidates.some((candidate) => existsSync(candidate))
        ) {
          continue
        }

        failures.push({
          sourcePath,
          line: link.line,
          target: link.target,
          candidates
        })
      }
    }
  }

  return failures
}

async function main() {
  const repositoryRoot = path.resolve(process.cwd())
  const locales = process.argv.slice(2)
  const failures = await validateLocalLinks(
    repositoryRoot,
    locales.length > 0 ? locales : ['ko', 'en']
  )

  if (failures.length === 0) {
    console.log('Local link validation passed for ko/en.')
    return
  }

  for (const failure of failures) {
    const source = path.relative(repositoryRoot, failure.sourcePath)
    console.error(`${source}:${failure.line} -> ${failure.target}`)
  }
  console.error(`Found ${failures.length} broken local link(s).`)
  process.exitCode = 1
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await main()
}
