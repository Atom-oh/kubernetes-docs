import assert from 'node:assert/strict'
import test from 'node:test'

import {
  extractDescription,
  localeAlternates,
  normalizeReadmeHref
} from '../../.vitepress/seo.mjs'

test('extractDescription returns the first body paragraph, skipping title and header quote', () => {
  const src = [
    '# Istio Traffic Management',
    '> **Last Updated**: August 1, 2026',
    '',
    'Istio routes traffic between services using VirtualService resources.',
    '',
    'Second paragraph should be ignored.'
  ].join('\n')

  assert.equal(
    extractDescription(src),
    'Istio routes traffic between services using VirtualService resources.'
  )
})

test('extractDescription strips markdown inline syntax', () => {
  const src = [
    '# Title',
    '',
    'Use **mTLS** with [Istio](https://istio.io) and `PeerAuthentication` to secure traffic.'
  ].join('\n')

  assert.equal(
    extractDescription(src),
    'Use mTLS with Istio and PeerAuthentication to secure traffic.'
  )
})

test('extractDescription skips frontmatter, code fences, images, and tables', () => {
  const src = [
    '---',
    'title: ignored',
    '---',
    '# Title',
    '',
    '![diagram](../assets/foo.svg)',
    '',
    '```bash',
    'kubectl get pods',
    '```',
    '',
    '| a | b |',
    '|---|---|',
    '| 1 | 2 |',
    '',
    'Real first paragraph here.'
  ].join('\n')

  assert.equal(extractDescription(src), 'Real first paragraph here.')
})

test('extractDescription truncates long text at a sentence boundary within 160 chars', () => {
  const first = 'This sentence is the opening statement of the document and stays intact.'
  const second =
    'This trailing sentence keeps going well beyond the limit so that the combined length of the paragraph clearly exceeds one hundred and sixty characters in total.'
  const out = extractDescription(`# T\n\n${first} ${second}`)

  assert.equal(out, first)
  assert.ok(out.length <= 160)
})

test('extractDescription truncates at a word boundary with ellipsis when no sentence fits', () => {
  const long = 'word '.repeat(60).trim()
  const out = extractDescription(`# T\n\n${long}`)

  assert.ok(out.length <= 160)
  assert.ok(out.endsWith('…'))
})

test('extractDescription stops at a quiz answer toggle instead of leaking the answer', () => {
  const src = [
    '# Quiz',
    '',
    '<details>',
    '<summary>정답 보기</summary>',
    '',
    '**정답: B**',
    '',
    '</details>'
  ].join('\n')

  assert.equal(extractDescription(src), undefined)
})

test('extractDescription keeps the intro paragraph that precedes a quiz answer toggle', () => {
  const src = [
    '# Quiz',
    '',
    'This quiz checks your understanding of Linux basics.',
    '',
    '1. Question text',
    '',
    '<details>',
    '<summary>정답 보기</summary>',
    '',
    '**정답: B**',
    '',
    '</details>'
  ].join('\n')

  assert.equal(extractDescription(src), 'This quiz checks your understanding of Linux basics.')
})

test('extractDescription returns undefined when there is no body paragraph', () => {
  assert.equal(extractDescription('# Only a title\n> **Last Updated**: today'), undefined)
})

test('normalizeReadmeHref maps README.md links to index.md, preserving anchors', () => {
  assert.equal(normalizeReadmeHref('./README.md'), './index.md')
  assert.equal(normalizeReadmeHref('README.md'), 'index.md')
  assert.equal(
    normalizeReadmeHref('../gitops/argocd/README.md'),
    '../gitops/argocd/index.md'
  )
  assert.equal(normalizeReadmeHref('README.md#section'), 'index.md#section')
  assert.equal(normalizeReadmeHref('/ko/networking/README.md'), '/ko/networking/index.md')
})

test('normalizeReadmeHref leaves non-README and external links untouched', () => {
  assert.equal(normalizeReadmeHref('./01-linux-basics.md'), './01-linux-basics.md')
  assert.equal(
    normalizeReadmeHref('https://github.com/foo/bar/blob/main/README.md'),
    'https://github.com/foo/bar/blob/main/README.md'
  )
  assert.equal(normalizeReadmeHref('NOT-README.md'), 'NOT-README.md')
})

const HOST = 'https://www.atomai.click/kubernetes-docs/'

test('localeAlternates cross-references ko and en with x-default on ko', () => {
  const fileExists = (p) => p === 'en/networking/cilium/README.md'
  const links = localeAlternates('ko/networking/cilium/index.md', { fileExists })

  assert.deepEqual(links, [
    { hreflang: 'ko', href: `${HOST}ko/networking/cilium/` },
    { hreflang: 'en', href: `${HOST}en/networking/cilium/` },
    { hreflang: 'x-default', href: `${HOST}ko/networking/cilium/` }
  ])
})

test('localeAlternates builds clean URLs for regular pages from the en side', () => {
  const fileExists = (p) => p === 'ko/basics/01-linux-basics.md'
  const links = localeAlternates('en/basics/01-linux-basics.md', { fileExists })

  assert.deepEqual(links, [
    { hreflang: 'ko', href: `${HOST}ko/basics/01-linux-basics` },
    { hreflang: 'en', href: `${HOST}en/basics/01-linux-basics` },
    { hreflang: 'x-default', href: `${HOST}ko/basics/01-linux-basics` }
  ])
})

test('localeAlternates returns nothing when the counterpart does not exist', () => {
  assert.deepEqual(
    localeAlternates('ko/only-in-ko.md', { fileExists: () => false }),
    []
  )
})

test('localeAlternates ignores pages outside the published locales', () => {
  assert.deepEqual(localeAlternates('index.md', { fileExists: () => true }), [])
})
