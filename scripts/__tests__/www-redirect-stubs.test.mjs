import assert from 'node:assert/strict'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'

import { writeWwwRedirectStubs } from '../www-redirect-stubs.mjs'

const refreshTarget = (html) => html.match(/http-equiv="refresh" content="0; url=([^"]+)"/)?.[1]

test('cn/jp/es pages on www become redirects to the same docs.atomai.click URL', async () => {
  const dist = await mkdtemp(path.join(tmpdir(), 'www-stubs-'))
  try {
    const existingStub = '<meta http-equiv="refresh" content="0; url=https://docs.atomai.click/kubernetes-docs/en/kernel/01">'
    const files = {
      'cn/index.html': '<html>cn home</html>',
      'cn/networking/calico/index.html': '<html>section</html>',
      'cn/networking/calico/02-architecture.html': '<html>page</html>',
      'cn/kernel/01.html': existingStub,
      'ko/basics/01.html': '<html>ko page</html>'
    }
    for (const [file, content] of Object.entries(files)) {
      await mkdir(path.dirname(path.join(dist, file)), { recursive: true })
      await writeFile(path.join(dist, file), content)
    }

    assert.equal(await writeWwwRedirectStubs(dist, ['cn', 'jp', 'es']), 3)

    const read = (file) => readFile(path.join(dist, file), 'utf8')
    assert.equal(refreshTarget(await read('cn/index.html')), 'https://docs.atomai.click/kubernetes-docs/cn/')
    assert.equal(refreshTarget(await read('cn/networking/calico/index.html')), 'https://docs.atomai.click/kubernetes-docs/cn/networking/calico/')
    assert.equal(refreshTarget(await read('cn/networking/calico/02-architecture.html')), 'https://docs.atomai.click/kubernetes-docs/cn/networking/calico/02-architecture')
    // An untranslated-page stub already points at English on docs.atomai.click: no second hop.
    assert.equal(await read('cn/kernel/01.html'), existingStub)
    // Other locales are untouched.
    assert.equal(await read('ko/basics/01.html'), '<html>ko page</html>')
  } finally {
    await rm(dist, { recursive: true, force: true })
  }
})
