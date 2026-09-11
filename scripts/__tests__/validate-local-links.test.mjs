import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  extractLocalTargets,
  requiresExplicitReadmeTarget,
  resolveLocalTarget,
  stripFencedCode,
  validateLocalLinks
} from '../validate-local-links.mjs'

test('stripFencedCode keeps line positions while removing fenced examples', () => {
  const source = [
    '[kept](./kept.md)',
    '```markdown',
    '[ignored](./missing.md)',
    '```',
    '<a href="./also-kept.md">kept</a>'
  ].join('\n')

  assert.equal(stripFencedCode(source), [
    '[kept](./kept.md)',
    '',
    '',
    '',
    '<a href="./also-kept.md">kept</a>'
  ].join('\n'))
})

test('extractLocalTargets ignores remote, anchor, and template links', () => {
  const source = [
    '[document](./guide.md)',
    '![image](../assets/diagram.png)',
    '<a href="./reference/">Reference</a>',
    '[remote](https://example.com)',
    '[anchor](#section)',
    '[template]({{ docs_url }})'
  ].join('\n')

  assert.deepEqual(
    extractLocalTargets(source).map(({ target, line }) => ({ target, line })),
    [
      { target: './guide.md', line: 1 },
      { target: '../assets/diagram.png', line: 2 },
      { target: './reference/', line: 3 }
    ]
  )
})

test('resolveLocalTarget supports Markdown files, README directories, and site-root paths', () => {
  const repositoryRoot = '/repo'
  const sourcePath = '/repo/ko/topic/page.md'

  assert.deepEqual(
    resolveLocalTarget(sourcePath, './guide.md#section', repositoryRoot),
    ['/repo/ko/topic/guide.md']
  )
  assert.deepEqual(
    resolveLocalTarget(sourcePath, './reference/', repositoryRoot),
    ['/repo/ko/topic/reference/README.md']
  )
  assert.deepEqual(
    resolveLocalTarget(sourcePath, '/kubernetes-docs/en/core/', repositoryRoot),
    ['/repo/en/core/README.md']
  )
  assert.equal(
    path.isAbsolute(resolveLocalTarget(sourcePath, '../asset.png', repositoryRoot)[0]),
    true
  )
})

test('requiresExplicitReadmeTarget flags local directory-style links', () => {
  assert.equal(requiresExplicitReadmeTarget('./reference/'), true)
  assert.equal(requiresExplicitReadmeTarget('../../observability/'), true)
  assert.equal(requiresExplicitReadmeTarget('./#section'), true)
  assert.equal(requiresExplicitReadmeTarget('./reference/README.md'), false)
  assert.equal(requiresExplicitReadmeTarget('https://example.com/reference/'), false)
})

test('absolute links to this repository main branch are checked against the checkout', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'repo-link-validation-'))
  try {
    fs.mkdirSync(path.join(root, 'en/core'), { recursive: true })
    fs.writeFileSync(path.join(root, 'en/core/page.md'), '# Page\n')
    fs.writeFileSync(path.join(root, 'en/README.md'), [
      '# Index',
      '[good](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/core/page.md#part)',
      '[missing](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/core/missing.md)',
      '[historical](https://github.com/Atom-oh/kubernetes-docs/blob/v1.0/en/old.md)',
      '[other repository](https://github.com/example/other/blob/main/missing.md)'
    ].join('\n'))
    const failures = await validateLocalLinks(root, ['en'])
    assert.equal(failures.length, 1)
    assert.equal(failures[0].target, 'https://github.com/Atom-oh/kubernetes-docs/blob/main/en/core/missing.md')
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})
