import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'

import {
  extractLocalTargets,
  requiresExplicitReadmeTarget,
  resolveLocalTarget,
  stripFencedCode
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
