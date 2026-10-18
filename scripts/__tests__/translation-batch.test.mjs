import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { prepareBatch, translateBatch, refreshBatch, publishBatch, checkpointBatch, statePath, batchBranch } from '../translation-batch.mjs'

const source = '# Source\n\nA complete paragraph about Kubernetes Pod scheduling and networking.\n'
const translated = source.replace('Source', 'Translated')

function fixture(t, files = { 'en/topic/page.md': source, 'cn/topic/page.md': translated }) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-batch-test-'))
  const root = path.join(directory, 'repo')
  fs.mkdirSync(root)
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }))
  const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8', stdio: 'pipe' }).trim()
  const write = (file, content) => {
    fs.mkdirSync(path.dirname(path.join(root, file)), { recursive: true })
    fs.writeFileSync(path.join(root, file), content)
  }
  const read = file => fs.readFileSync(path.join(root, file), 'utf8')
  const commit = () => { git('add', '.'); git('commit', '-qm', 'fixture'); return git('rev-parse', 'HEAD') }
  git('init', '-q', '--initial-branch=main')
  git('config', 'user.name', 'Fixture')
  git('config', 'user.email', 'fixture@example.invalid')
  git('config', 'commit.gpgsign', 'false')
  for (const [file, content] of Object.entries(files)) write(file, content)
  write('scripts/validate-translation.py', fs.readFileSync(fileURLToPath(new URL('../validate-translation.py', import.meta.url))))
  const before = commit()
  return { root, directory, git, write, read, commit, before, state: () => JSON.parse(read(statePath)) }
}

test('fresh pending translations survive main advancement and identical reruns avoid model calls', t => {
  const f = fixture(t)
  f.git('checkout', '-qb', 'pending')
  f.write('cn/topic/page.md', translated.replace('Translated', 'Pending translation'))
  const pending = f.commit()
  f.git('checkout', '-q', 'main')
  f.write('en/unrelated.md', source)
  f.commit()
  assert.deepEqual(prepareBatch(f.root, { refs: [pending], before: f.before }), [])
  assert.match(f.read('cn/topic/page.md'), /Pending translation/)
  f.git('checkout', '-qb', 'batch')
  const batch = f.commit()
  f.git('checkout', '-q', 'main')
  assert.deepEqual(prepareBatch(f.root, { refs: [batch], before: f.before }), [])
  assert.match(f.read('cn/topic/page.md'), /Pending translation/)
})

test('changed English source keeps current main translation and queues replacement instead of stale overlay', t => {
  const f = fixture(t)
  f.git('checkout', '-qb', 'old-translation')
  f.write('cn/topic/page.md', translated.replace('Translated', 'Stale translated content'))
  const pending = f.commit()
  f.git('checkout', '-q', 'main')
  f.write('en/topic/page.md', source + '\nNew source information.\n')
  f.commit()
  assert.deepEqual(prepareBatch(f.root, { refs: [pending] }), [['en/topic/page.md', 'cn/topic/page.md', 'cn']])
  assert.equal(f.read('cn/topic/page.md'), translated)
  assert.deepEqual(f.state().pending, ['cn/topic/page.md'])
})

test('overlapping locale edits preserve main and retry; non-overlapping edits merge without conflict markers', t => {
  const lines = Array.from({ length: 15 }, (_, i) => `line ${i}`).join('\n') + '\n'
  const f = fixture(t, { 'en/topic/page.md': source, 'cn/topic/page.md': lines, 'jp/topic/page.md': lines })
  f.git('checkout', '-qb', 'pending')
  for (const lang of ['cn', 'jp']) f.write(`${lang}/topic/page.md`, lines.replace('line 0', 'pending line'))
  const pending = f.commit()
  f.git('checkout', '-q', 'main')
  f.write('cn/topic/page.md', lines.replace('line 0', 'main line'))
  f.write('jp/topic/page.md', lines.replace('line 14', 'main last line'))
  f.commit()
  assert.deepEqual(prepareBatch(f.root, { refs: [pending] }), [['en/topic/page.md', 'cn/topic/page.md', 'cn']])
  assert.match(f.read('cn/topic/page.md'), /^main line/)
  assert.match(f.read('jp/topic/page.md'), /^pending line/)
  assert.match(f.read('jp/topic/page.md'), /main last line/)
  assert.doesNotMatch(f.read('jp/topic/page.md'), /<<<<<<<|>>>>>>>/)
})

test('before-to-latest-main includes changes from replaced queued push events', t => {
  const f = fixture(t, {
    'en/topic/a.md': source, 'en/topic/b.md': source,
    'cn/topic/a.md': translated, 'jp/topic/b.md': translated
  })
  f.write('en/topic/a.md', source + '\nFirst push.\n')
  f.commit()
  f.write('en/topic/b.md', source + '\nSecond push.\n')
  f.commit()
  assert.deepEqual(prepareBatch(f.root, { before: f.before }), [
    ['en/topic/a.md', 'cn/topic/a.md', 'cn'], ['en/topic/b.md', 'jp/topic/b.md', 'jp']
  ])
})

test('persisted source checkpoint catches a dropped event even when next push before excludes it', t => {
  const f = fixture(t)
  prepareBatch(f.root)
  f.git('checkout', '-qb', 'batch')
  const batch = f.commit()
  f.git('checkout', '-q', 'main')
  f.write('en/topic/page.md', source + '\nUpdate in replaced pending event.\n')
  const beforeLatestPush = f.commit()
  f.write('en/unrelated.md', source)
  f.commit()
  assert.deepEqual(prepareBatch(f.root, { refs: [batch], before: beforeLatestPush }), [
    ['en/topic/page.md', 'cn/topic/page.md', 'cn']
  ])
})

test('backfill queues only missing requested-language section pages and intro pages', t => {
  const f = fixture(t, {
    'en/topic/page.md': source, 'cn/topic/page.md': translated,
    'en/topic/new.md': source, 'en/other/page.md': source,
    'en/labs/topic/lab.md': source, 'en/quizzes/README.md': source
  })
  assert.deepEqual(prepareBatch(f.root, { section: 'topic', langs: ['cn'] }), [
    ['en/labs/topic/lab.md', 'cn/labs/topic/lab.md', 'cn'],
    ['en/quizzes/README.md', 'cn/quizzes/README.md', 'cn'],
    ['en/topic/new.md', 'cn/topic/new.md', 'cn']
  ])
  assert.throws(() => prepareBatch(f.root, { section: '../en', langs: ['cn'] }), /Invalid/)
})

test('partial failures restore imported pending content, remove partial new pages and remain queued', async t => {
  const f = fixture(t, {
    'en/topic/page.md': source, 'en/topic/new.md': source, 'en/topic/good.md': source,
    'cn/topic/page.md': translated
  })
  const pairs = prepareBatch(f.root, { section: 'topic', langs: ['cn'] })
  pairs.push(['en/topic/page.md', 'cn/topic/page.md', 'cn'])
  f.write('cn/topic/page.md', translated.replace('Translated', 'Previously pending'))
  const failures = await translateBatch(f.root, pairs, (src, file) => {
    f.write(file, translated)
    if (!file.includes('good')) throw new Error('failed after partial output')
  })
  assert.deepEqual(failures.sort(), ['cn/topic/new.md', 'cn/topic/page.md'])
  assert.match(f.read('cn/topic/page.md'), /Previously pending/)
  assert.equal(fs.existsSync(path.join(f.root, 'cn/topic/new.md')), false)
  assert.equal(f.read('cn/topic/good.md'), translated)
  assert.deepEqual(f.state().pending, ['cn/topic/new.md', 'cn/topic/page.md'])
  assert.equal(f.state().sources['cn/topic/good.md'], f.git('rev-parse', 'HEAD:en/topic/good.md'))
})

test('structurally invalid translation is restored and retried', async t => {
  const f = fixture(t)
  f.write('en/topic/page.md', source + '\n```yaml\nkind: Pod\n```\n')
  f.commit()
  const pairs = prepareBatch(f.root, { before: f.before })
  const failures = await translateBatch(f.root, pairs, (src, file) => f.write(file, f.read(src).replace('kind: Pod', 'kind: Job')))
  assert.deepEqual(failures, ['cn/topic/page.md'])
  assert.equal(f.read('cn/topic/page.md'), translated)
  assert.deepEqual(f.state().pending, ['cn/topic/page.md'])
})

test('a fatal provider error stops new calls, restores originals and leaves unattempted files queued', async t => {
  const f = fixture(t, {
    'en/topic/a.md': source, 'en/topic/b.md': source, 'en/topic/c.md': source,
    'cn/topic/a.md': translated, 'cn/topic/b.md': translated, 'cn/topic/c.md': translated
  })
  for (const name of ['a', 'b', 'c']) f.write(`en/topic/${name}.md`, source + '\nNew source information.\n')
  f.commit()
  const pairs = prepareBatch(f.root, { before: f.before })
  let calls = 0
  await assert.rejects(() => translateBatch(f.root, pairs, (src, file) => {
    calls++
    f.write(file, '# Partial\n')
    throw Object.assign(new Error('model unavailable'), { fatal: true })
  }), /model unavailable/)
  assert.equal(calls, 1)
  for (const name of ['a', 'b', 'c']) assert.equal(f.read(`cn/topic/${name}.md`), translated)
  assert.deepEqual(f.state().pending, ['cn/topic/a.md', 'cn/topic/b.md', 'cn/topic/c.md'])
  assert.deepEqual(f.state().sources, {})
})

test('main changes during translation invalidate affected outputs and queue newly changed pages', t => {
  const f = fixture(t, {
    'en/topic/page.md': source, 'cn/topic/page.md': translated,
    'en/topic/other.md': source, 'cn/topic/other.md': translated
  })
  f.git('checkout', '-qb', 'latest')
  f.write('en/topic/page.md', source + '\nEdited during translation.\n')
  f.write('en/topic/other.md', source + '\nNewly changed during translation.\n')
  const latest = f.commit()
  f.git('checkout', '-q', 'main')
  prepareBatch(f.root)
  f.write('cn/topic/page.md', translated.replace('Translated', 'Output now stale'))
  const state = f.state()
  state.sources['cn/topic/page.md'] = f.git('rev-parse', 'HEAD:en/topic/page.md')
  f.write(statePath, JSON.stringify(state))
  refreshBatch(f.root, latest)
  assert.equal(f.git('rev-parse', 'HEAD'), latest)
  assert.equal(f.read('cn/topic/page.md'), translated)
  assert.deepEqual(f.state().pending, ['cn/topic/other.md', 'cn/topic/page.md'])
})

test('valid outputs survive main refresh, including staged new backfill files', t => {
  const f = fixture(t, { 'en/topic/page.md': source })
  f.git('checkout', '-qb', 'latest')
  f.write('en/unrelated.md', source)
  const latest = f.commit()
  f.git('checkout', '-q', 'main')
  prepareBatch(f.root, { section: 'topic', langs: ['cn'] })
  f.write('cn/topic/page.md', translated)
  f.write(statePath, JSON.stringify({ version: 1, sources: { 'cn/topic/page.md': f.git('rev-parse', 'HEAD:en/topic/page.md') }, pending: [] }))
  f.git('add', 'cn', statePath)
  refreshBatch(f.root, latest)
  assert.equal(f.read('cn/topic/page.md'), translated)
  assert.deepEqual(f.state().pending, [])
})

test('deleted English pages remove translated counterpart and queued state', t => {
  const f = fixture(t)
  fs.rmSync(path.join(f.root, 'en/topic/page.md'))
  f.commit()
  assert.deepEqual(prepareBatch(f.root, { before: f.before }), [])
  assert.equal(fs.existsSync(path.join(f.root, 'cn/topic/page.md')), false)
  assert.deepEqual(f.state().pending, [])
})

test('imports ignore unrelated code, preserve heading decisions from main and reject out-of-scope state', t => {
  const f = fixture(t, {
    'en/topic/page.md': source, 'cn/topic/page.md': translated,
    '.github/i18n-heading-map.json': JSON.stringify({ Title: { cn: 'current' } })
  })
  f.git('checkout', '-qb', 'pending')
  f.write('unrelated.js', 'malicious change')
  f.write('.github/i18n-heading-map.json', JSON.stringify({ Title: { cn: 'older', jp: 'new' } }))
  const pending = f.commit()
  f.git('checkout', '-q', 'main')
  prepareBatch(f.root, { refs: [pending] })
  assert.equal(fs.existsSync(path.join(f.root, 'unrelated.js')), false)
  assert.deepEqual(JSON.parse(f.read('.github/i18n-heading-map.json')), { Title: { cn: 'current', jp: 'new' } })
  f.write(statePath, JSON.stringify({ version: 1, sources: {}, pending: ['cn/../en/source.md'] }))
  f.commit()
  assert.throws(() => prepareBatch(f.root), /Invalid translation path/)
})

function remoteAndGh(f) {
  // Real Git commits/pushes, with a local GitHub substitute to check PR ordering.
  const remote = path.join(f.directory, 'remote.git')
  execFileSync('git', ['init', '--bare', '-q', remote])
  f.git('remote', 'add', 'origin', remote)
  f.git('push', '-q', 'origin', 'main')
  for (const lang of ['jp', 'es']) f.write(`${lang}/.keep`, '')
  f.write('.github/i18n-heading-map.json', '{}\n')
  f.commit()
  f.git('push', '-q', 'origin', 'main')
  const bin = path.join(f.directory, 'bin')
  fs.mkdirSync(bin)
  const ghState = path.join(f.directory, 'gh-state.json')
  fs.writeFileSync(ghState, JSON.stringify({
    prs: [{ number: 1, headRefName: 'docs/translate-sync-abcdef', isDraft: false, isCrossRepository: false, createdAt: '2026-01-01' }],
    calls: []
  }))
  fs.writeFileSync(path.join(bin, 'gh'), `#!/usr/bin/env node
const fs = require('fs'), cp = require('child_process')
const file = ${JSON.stringify(ghState)}, state = JSON.parse(fs.readFileSync(file)), args = process.argv.slice(2)
state.calls.push(args)
if (args[0] === 'pr' && args[1] === 'list') console.log(JSON.stringify(state.prs.filter(pr => !state.hideNewFromList || pr.number !== 2)))
else if (args[0] === 'pr' && args[1] === 'create') {
  state.prs.push({ number: 2, headRefName: ${JSON.stringify(batchBranch)}, isDraft: args.includes('--draft'), isCrossRepository: false, createdAt: '2026-01-02' })
  console.log('https://github.com/Fixture/repo/pull/2')
} else if (args[0] === 'pr' && args[1] === 'close') {
  if (!state.prs.some(pr => pr.number === 2)) throw Error('closed before replacement PR')
  if (!cp.execFileSync('git', ['ls-remote', 'origin', ${JSON.stringify(batchBranch)}]).length) throw Error('closed before push')
  state.prs = state.prs.filter(pr => pr.number !== Number(args[2]))
} else if (args[0] === 'pr' && args[1] === 'ready') state.prs.find(pr => pr.number === Number(args[2])).isDraft = args.includes('--undo')
else if (!(args[0] === 'label' || args[0] === 'pr' && args[1] === 'edit')) throw Error('unsupported gh')
fs.writeFileSync(file, JSON.stringify(state))
`, { mode: 0o755 })
  const oldPath = process.env.PATH
  process.env.PATH = `${bin}:${oldPath}`
  return {
    remote,
    state: () => JSON.parse(fs.readFileSync(ghState)),
    update: values => fs.writeFileSync(ghState, JSON.stringify({ ...JSON.parse(fs.readFileSync(ghState)), ...values })),
    restore: () => { process.env.PATH = oldPath }
  }
}

test('publishing persists replacement before closing old PRs and updates the same branch/PR on rerun', t => {
  const f = fixture(t)
  const gh = remoteAndGh(f)
  t.after(gh.restore)
  prepareBatch(f.root, { section: 'topic', langs: ['jp'] })
  assert.equal(publishBatch(f.root), 2)
  assert.equal(gh.state().prs.length, 1)
  assert.equal(gh.state().prs[0].headRefName, batchBranch)
  assert.equal(gh.state().prs[0].isDraft, true)
  assert.deepEqual(JSON.parse(f.git('show', `origin/${batchBranch}:${statePath}`)).pending, ['jp/topic/page.md'])
  const snapshot = f.git('rev-parse', 'HEAD')
  f.git('checkout', '-q', '--detach', 'origin/main')
  prepareBatch(f.root, { refs: [snapshot] })
  f.write('jp/topic/page.md', translated)
  f.write(statePath, JSON.stringify({
    version: 1, sources: { 'jp/topic/page.md': f.git('rev-parse', 'HEAD:en/topic/page.md') }, pending: []
  }))
  assert.equal(publishBatch(f.root, { draft: false }), 2)
  assert.equal(gh.state().calls.filter(call => call[0] === 'pr' && call[1] === 'create').length, 1)
  assert.equal(gh.state().prs[0].isDraft, false)
  assert.equal(f.git('merge-base', 'HEAD', 'origin/main'), f.git('rev-parse', 'origin/main'))
})

test('publishing refuses a newly advanced main and never closes legacy PRs', t => {
  const f = fixture(t)
  const gh = remoteAndGh(f)
  t.after(gh.restore)
  const currentMain = f.git('rev-parse', 'HEAD')
  f.write('en/new.md', source)
  f.commit()
  f.git('push', '-q', 'origin', 'main')
  f.git('checkout', '-q', '--detach', currentMain)
  prepareBatch(f.root)
  assert.throws(() => publishBatch(f.root), /main changed/)
  assert.equal(gh.state().calls.length, 0)
})

test('PR creation succeeds even while GitHub list search cannot see the new PR', t => {
  const f = fixture(t)
  const gh = remoteAndGh(f)
  t.after(gh.restore)
  gh.update({ hideNewFromList: true })
  prepareBatch(f.root)
  assert.equal(publishBatch(f.root), 2)
  assert.equal(gh.state().prs[0].number, 2)
  assert.equal(gh.state().calls.filter(call => call[0] === 'pr' && call[1] === 'list').length, 1)
})

test('chunk checkpoint preserves completed work and retry queue when the next run resumes', async t => {
  const f = fixture(t)
  const gh = remoteAndGh(f)
  t.after(gh.restore)
  const pairs = prepareBatch(f.root, { section: 'topic', langs: ['jp', 'es'] })
  checkpointBatch(f.root)
  await translateBatch(f.root, [pairs[0]], (src, file) => f.write(file, translated))
  checkpointBatch(f.root)
  const saved = f.git('rev-parse', `origin/${batchBranch}`)
  assert.equal(gh.state().prs[0].isDraft, true)
  assert.deepEqual(JSON.parse(f.git('show', `${saved}:${statePath}`)).pending, ['jp/topic/page.md'])
  // A fresh checkout should only translate the unfinished target, while the
  // final review still sees the completed chunk.
  f.git('restore', '--worktree', '--', 'cn', 'jp', 'es', '.github/i18n-heading-map.json')
  fs.rmSync(path.join(f.root, statePath), { force: true })
  fs.rmSync(path.join(f.root, 'es/topic/page.md'), { force: true })
  assert.deepEqual(prepareBatch(f.root, { refs: [saved] }), [['en/topic/page.md', 'jp/topic/page.md', 'jp']])
  assert.equal(f.read('es/topic/page.md'), translated)
})

test('publishing rejects a translation branch edited since the prepared snapshot', t => {
  const f = fixture(t)
  const gh = remoteAndGh(f)
  t.after(gh.restore)
  prepareBatch(f.root)
  publishBatch(f.root)
  const snapshot = f.git('rev-parse', 'HEAD')
  // Simulate an independent writer advancing origin without updating this
  // checkout's remote-tracking ref.
  f.git('checkout', '-qb', 'other-writer')
  f.write('cn/topic/page.md', translated.replace('Translated', 'Other writer'))
  const other = f.commit()
  f.git('push', '-q', '--force', gh.remote, `HEAD:refs/heads/${batchBranch}`)
  f.git('checkout', '-q', '--detach', 'origin/main')
  prepareBatch(f.root, { refs: [snapshot] })
  assert.throws(() => publishBatch(f.root), /branch changed/)
  assert.equal(f.git('ls-remote', 'origin', batchBranch).split(/\s/)[0], other)
})
