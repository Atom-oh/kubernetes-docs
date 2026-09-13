import assert from 'node:assert/strict'
import os from 'node:os'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'

test('MCP from an unrelated cwd searches the real corpus and returns cited, paginated Markdown', async () => {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [fileURLToPath(new URL('../docs-mcp.mjs', import.meta.url))],
    cwd: os.tmpdir(),
    stderr: 'pipe'
  })
  const client = new Client({ name: 'docs-integration-test', version: '1.0.0' })
  let stderr = ''
  transport.stderr.on('data', chunk => { stderr += chunk.toString() })
  try {
    await client.connect(transport)
    const { tools } = await client.listTools()
    assert.deepEqual(tools.map(tool => tool.name).sort(), ['fetch', 'search'])
    assert.ok(tools.every(tool => tool.annotations.readOnlyHint))
    const search = await client.callTool({
      name: 'search', arguments: { query: 'gp3', locale: 'en', section: 'storage', limit: 3 }
    })
    assert.equal(search.isError, undefined)
    const data = JSON.parse(search.content[0].text)
    assert.ok(data.results.length > 0)
    assert.ok(data.results.length <= 3)
    const hit = data.results.find(result => result.id.includes('01-ebs-gp2-gp3-benchmark'))
    assert.ok(hit, 'known gp2/gp3 benchmark must be discoverable')
    assert.ok(hit.url.startsWith('https://www.atomai.click/kubernetes-docs/en/'))
    assert.ok(hit.markdownUrl.endsWith('.md'))
    const first = await client.callTool({ name: 'fetch', arguments: { id: hit.id, maxLength: 500 } })
    const page = JSON.parse(first.content[0].text)
    assert.equal(page.text.length, 500)
    assert.equal(page.nextOffset, 500)
    assert.equal(page.sha256, hit.sha256)
    assert.equal(page.url, hit.url)
    const second = await client.callTool({
      name: 'fetch', arguments: { id: hit.id, offset: page.nextOffset, maxLength: 500 }
    })
    assert.equal(JSON.parse(second.content[0].text).offset, 500)
    for (const args of [{ id: '../../package.json' }, { id: hit.id, maxLength: 999999 }]) {
      const result = await client.callTool({ name: 'fetch', arguments: args })
      assert.equal(result.isError, true)
    }
    const empty = await client.callTool({ name: 'search', arguments: { query: ' ' } })
    assert.equal(empty.isError, true)
    const korean = await client.callTool({
      name: 'search', arguments: { query: '스토리지 gp3', locale: 'ko', limit: 3 }
    })
    assert.ok(JSON.parse(korean.content[0].text).results.length > 0)
    assert.equal(stderr, '')
  } catch (error) {
    throw new Error(`${error.message}\nServer stderr: ${stderr}`, { cause: error })
  } finally {
    await client.close()
  }
})
