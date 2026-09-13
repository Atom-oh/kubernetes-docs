import assert from 'node:assert/strict'
import test from 'node:test'
import { createDocViewTracker, GA_ID } from '../../.vitepress/theme/analytics.mjs'

test('document views cover initial load and SPA navigation without duplicating GA4 page_view', () => {
  const events = []
  const first = 'https://www.atomai.click/kubernetes-docs/ko/llm-guide'
  const second = 'https://www.atomai.click/kubernetes-docs/ko/roadmap'
  const track = createDocViewTracker('https://www.google.com/', (...args) => events.push(args))
  assert.equal(events.length, 0)
  track(first, 'LLM과 함께 읽기')
  track(second, '가이드북 로드맵')
  assert.equal(events[0][1], 'docs_page_view')
  assert.equal(events[0][2].page_referrer, 'https://www.google.com/')
  assert.deepEqual(events[1], [
    'event', 'docs_page_view',
    {
      send_to: GA_ID,
      page_location: second,
      page_path: '/kubernetes-docs/ko/roadmap',
      page_title: '가이드북 로드맵',
      page_referrer: first
    }
  ])
  track(first, 'LLM과 함께 읽기')
  assert.equal(events[2][2].page_referrer, second)
  assert.ok(events.every(event => event[1] !== 'page_view'))
})

test('same-document renders and outline anchors do not inflate page views', () => {
  const events = []
  const url = 'https://www.atomai.click/kubernetes-docs/ko/roadmap'
  const track = createDocViewTracker('', (...args) => events.push(args))
  track(url + '#intro', 'Roadmap')
  track(url, 'Roadmap')
  track(url + '#next', 'Roadmap')
  assert.equal(events.length, 1)
  track(url + '?view=compact#top', 'Roadmap')
  assert.equal(events.length, 2)
  assert.equal(events[1][2].page_location, url + '?view=compact')
  track(url + '?view=compact#next', 'Roadmap')
  assert.equal(events.length, 2)
})
