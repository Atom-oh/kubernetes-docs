// Server-sent events from the docs Q&A API (infra/ask-docs/lambda/ask/server.py): yields
// { event, data } for each event as it arrives, with data parsed as JSON. Comment lines (": ok")
// are skipped. Events can be split across network chunks, so text is buffered until a blank line.
export async function* readEvents(body) {
  const reader = body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) return
      buffer += value
      let end
      while ((end = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, end)
        buffer = buffer.slice(end + 2)
        let event = 'message'
        const data = []
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
        }
        if (data.length) yield { event, data: JSON.parse(data.join('\n')) }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
