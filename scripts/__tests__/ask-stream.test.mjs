import assert from 'node:assert/strict'
import test from 'node:test'

import { readEvents } from '../../.vitepress/theme/ask-stream.mjs'

function streamOf(parts) {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const part of parts) controller.enqueue(typeof part === 'string' ? encoder.encode(part) : part)
      controller.close()
    }
  })
}

async function collect(body) {
  const events = []
  for await (const e of readEvents(body)) events.push(e)
  return events
}

test('reads events that arrive split across chunks, and skips comments', async () => {
  const meta = 'event: meta\ndata: {"conversationId":"abc","sources":[]}\n\n'
  const events = await collect(streamOf([': ok\n\n', meta.slice(0, 17), meta.slice(17), 'event: delta\ndata: {"text":"안녕', '"}\n\nevent: done\ndata: {}\n\n']))
  assert.deepEqual(events, [
    { event: 'meta', data: { conversationId: 'abc', sources: [] } },
    { event: 'delta', data: { text: '안녕' } },
    { event: 'done', data: {} }
  ])
})

test('decodes a multi-byte character split between chunks', async () => {
  const bytes = new TextEncoder().encode('event: delta\ndata: {"text":"한"}\n\n')
  const cut = bytes.indexOf(0xed) + 1 // inside the 3-byte UTF-8 sequence for 한
  const events = await collect(streamOf([bytes.slice(0, cut), bytes.slice(cut)]))
  assert.deepEqual(events, [{ event: 'delta', data: { text: '한' } }])
})

test('ignores an unfinished event at the end of the stream', async () => {
  const events = await collect(streamOf(['event: delta\ndata: {"text":"a"}\n\nevent: delta\ndata: {"te']))
  assert.deepEqual(events, [{ event: 'delta', data: { text: 'a' } }])
})
