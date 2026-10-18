import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { execFileSync, spawn, spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

export const batchBranch = 'docs/translate-sync'
export const statePath = '.github/translation-state.json'
const headingPath = '.github/i18n-heading-map.json'
const languages = ['cn', 'jp', 'es']
const legacyBranch = /^docs\/(?:translate-sync-[a-f0-9]+|translate-(?!sync$)[a-z0-9-]+)$/
const trees = new Map()

function run(root, command, args, binary = false) {
  return execFileSync(command, args, {
    cwd: root, encoding: binary ? null : 'utf8', maxBuffer: 64 * 1024 * 1024,
    stdio: ['ignore', 'pipe', 'pipe']
  })
}

function git(root, ...args) { return run(root, 'git', args).trim() }
function gh(root, ...args) { return run(root, 'gh', args).trim() }

function tree(root, ref) {
  const sha = git(root, 'rev-parse', ref)
  const key = `${root}:${sha}`
  if (!trees.has(key)) {
    const entries = new Map()
    for (const entry of run(root, 'git', ['ls-tree', '-rz', sha]).split('\0').filter(Boolean)) {
      const [info, name] = entry.split('\t')
      const [mode, type, oid] = info.split(' ')
      if (type === 'blob' && ['100644', '100755'].includes(mode)) entries.set(name, { oid, mode })
    }
    trees.set(key, entries)
  }
  return trees.get(key)
}

function blob(root, entry) {
  return entry ? run(root, 'git', ['cat-file', 'blob', entry.oid], true) : null
}

function translatedPath(file) {
  return /^(cn|jp|es)\/[A-Za-z0-9_./-]+\.md$/.test(file) &&
    !file.split('/').some(part => part === '..' || part === '.')
}

function sourcePath(file) {
  if (!translatedPath(file)) throw new Error(`Invalid translation path: ${file}`)
  return `en/${file.split('/').slice(1).join('/')}`
}

function allowedPath(file) {
  return file === statePath || file === headingPath || translatedPath(file) ||
    /^(cn|jp|es)\/\.gitbook\/assets\/[A-Za-z0-9_.-]+\.(png|svg|jpg|jpeg|webp|gif)$/i.test(file)
}

function readState(buffer) {
  if (!buffer) return { version: 1, sources: {}, pending: [] }
  const state = JSON.parse(buffer.toString())
  if (state.version !== 1 || !state.sources || !Array.isArray(state.pending)) {
    throw new Error('Invalid translation state')
  }
  if (state.sourceCommit && !/^[a-f0-9]{40,64}$/.test(state.sourceCommit)) throw new Error('Invalid source checkpoint')
  for (const [file, sha] of Object.entries(state.sources)) {
    if (!translatedPath(file) || !/^[a-f0-9]{40,64}$/.test(sha)) throw new Error('Invalid translation source record')
  }
  for (const file of state.pending) sourcePath(file)
  return state
}

function write(root, file, content) {
  if (!allowedPath(file)) throw new Error(`Refusing to write outside translation scope: ${file}`)
  const target = path.join(root, file)
  if (content === null) fs.rmSync(target, { force: true })
  else {
    fs.mkdirSync(path.dirname(target), { recursive: true })
    fs.writeFileSync(target, content)
  }
}

function writeState(root, state, pending) {
  state.sources = Object.fromEntries(Object.entries(state.sources).sort(([a], [b]) => a.localeCompare(b)))
  state.pending = [...pending].sort()
  const previous = readState(blob(root, tree(root, 'HEAD').get(statePath)))
  const sameSources = Object.keys(previous.sources).length === Object.keys(state.sources).length &&
    Object.entries(state.sources).every(([file, sha]) => previous.sources[file] === sha)
  const samePending = previous.pending.length === state.pending.length &&
    state.pending.every(file => previous.pending.includes(file))
  // A main commit without translation changes must not create a metadata-only PR.
  state.sourceCommit = sameSources && samePending && previous.sourceCommit
    ? previous.sourceCommit : git(root, 'rev-parse', 'HEAD')
  write(root, statePath, `${JSON.stringify(state, null, 2)}\n`)
}

function current(root, file) {
  const target = path.join(root, file)
  return fs.existsSync(target) ? fs.readFileSync(target) : null
}

function equal(a, b) { return a === null ? b === null : b !== null && a.equals(b) }

function mergeText(ours, base, theirs) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-merge-'))
  try {
    const files = ['ours', 'base', 'theirs'].map(name => path.join(directory, name))
    files.forEach((file, index) => fs.writeFileSync(file, [ours, base, theirs][index]))
    const result = spawnSync('git', ['merge-file', '-p', ...files], { maxBuffer: 64 * 1024 * 1024 })
    if (result.error) throw result.error
    if (result.status === 0) return result.stdout
    if (result.status > 0 && result.status < 128) return null
    throw new Error('Translation three-way merge failed')
  } finally { fs.rmSync(directory, { recursive: true, force: true }) }
}

function overlay(root, file, base, incoming) {
  const ours = current(root, file)
  if (equal(ours, incoming)) return true
  if (equal(ours, base)) { write(root, file, incoming); return true }
  if (ours && base && incoming && file.endsWith('.md')) {
    const merged = mergeText(ours, base, incoming)
    if (merged) { write(root, file, merged); return true }
  }
  return false
}

function mergeHeadings(root, incoming) {
  const ours = JSON.parse((current(root, headingPath) || Buffer.from('{}')).toString())
  const theirs = JSON.parse(incoming.toString())
  for (const [heading, values] of Object.entries(theirs)) {
    ours[heading] = { ...values, ...ours[heading] }
  }
  write(root, headingPath, `${JSON.stringify(ours, null, 2)}\n`)
}

export function prepareBatch(root, { refs = [], before, section, langs = languages, fillMissing = false } = {}) {
  const main = tree(root, 'HEAD')
  const state = readState(blob(root, main.get(statePath)))
  const pending = new Set(state.pending)
  // Reviewed results already merged into main supersede older draft queues.
  // Keep this snapshot separate from records imported during reconciliation.
  const mainSources = { ...state.sources }
  const mainPending = new Set(state.pending)
  const mainCurrent = file => main.has(file) && main.has(sourcePath(file)) && !mainPending.has(file) &&
    mainSources[file] === main.get(sourcePath(file))?.oid
  const checkpoints = new Set([before, state.sourceCommit].filter(Boolean))
  for (const ref of refs) {
    const incoming = tree(root, ref)
    const base = tree(root, git(root, 'merge-base', 'HEAD', ref))
    const previous = readState(blob(root, incoming.get(statePath)))
    if (previous.sourceCommit) checkpoints.add(previous.sourceCommit)
    previous.pending.forEach(file => {
      if (!mainCurrent(file)) pending.add(file)
    })
    for (const file of new Set([...base.keys(), ...incoming.keys()])) {
      if (!allowedPath(file) || file === statePath || base.get(file)?.oid === incoming.get(file)?.oid) continue
      if (file === headingPath) {
        if (incoming.has(file)) mergeHeadings(root, blob(root, incoming.get(file)))
        continue
      }
      if (translatedPath(file)) {
        if (mainCurrent(file)) continue
        const src = sourcePath(file)
        const source = previous.sources[file] || incoming.get(src)?.oid
        if (!main.has(src)) {
          write(root, file, null); delete state.sources[file]; pending.delete(file)
          continue
        }
        if (source !== main.get(src).oid || !incoming.has(file)) {
          pending.add(file)
          continue
        }
        if (overlay(root, file, blob(root, base.get(file)), blob(root, incoming.get(file)))) {
          state.sources[file] = source
          if (!previous.pending.includes(file)) pending.delete(file)
        } else pending.add(file)
      } else {
        // Assets are reconciled against current English files after translation.
        overlay(root, file, blob(root, base.get(file)), blob(root, incoming.get(file)))
      }
    }
    for (const [file, sha] of Object.entries(previous.sources)) {
      if (!state.sources[file] && main.get(sourcePath(file))?.oid === sha &&
          equal(current(root, file), blob(root, incoming.get(file)))) state.sources[file] = sha
    }
  }

  for (const checkpoint of checkpoints) {
    const prior = tree(root, checkpoint)
    for (const src of new Set([...prior.keys(), ...main.keys()])) {
      if (!src.startsWith('en/') || !src.endsWith('.md') || prior.get(src)?.oid === main.get(src)?.oid) continue
      for (const lang of languages) {
        const file = `${lang}${src.slice(2)}`
        if (translatedPath(file) && current(root, file) &&
            (!main.has(src) || state.sources[file] !== main.get(src).oid)) pending.add(file)
      }
    }
  }
  for (const [file, sha] of Object.entries(state.sources)) {
    if (main.get(sourcePath(file))?.oid !== sha) pending.add(file)
  }
  if (section || fillMissing) {
    if ((section && !/^[a-z0-9-]+$/.test(section)) ||
        !langs.length || langs.some(lang => !languages.includes(lang))) {
      throw new Error('Invalid backfill section/languages')
    }
    for (const src of main.keys()) {
      if (!src.startsWith('en/') || !src.endsWith('.md')) continue
      if (!fillMissing &&
          ![`en/${section}/`, `en/quizzes/${section}/`, `en/labs/${section}/`].some(prefix => src.startsWith(prefix)) &&
          !['en/labs/README.md', 'en/quizzes/README.md'].includes(src)) continue
      for (const lang of langs) {
        const file = `${lang}${src.slice(2)}`
        if (!current(root, file)) pending.add(file)
      }
    }
  }

  const pairs = []
  for (const file of [...pending].sort()) {
    const src = sourcePath(file)
    if (!main.has(src)) {
      write(root, file, null); delete state.sources[file]; pending.delete(file)
    } else pairs.push([src, file, file.split('/')[0]])
  }
  writeState(root, state, pending)
  return pairs
}

export function recordBatch(root, pairs, failures = []) {
  const main = tree(root, 'HEAD')
  const state = readState(current(root, statePath))
  const pending = new Set(state.pending)
  const failed = new Set(failures)
  for (const [src, file, lang] of pairs) {
    if (sourcePath(file) !== src || file.split('/')[0] !== lang) throw new Error('Invalid translation pair')
    if (failed.has(file) || !current(root, file)) { pending.add(file); continue }
    run(root, 'python3', ['scripts/validate-translation.py', src, file])
    state.sources[file] = main.get(src).oid
    pending.delete(file)
  }
  writeState(root, state, pending)
}

export async function translateBatch(root, pairs, translate = (src, file, lang) =>
  new Promise((resolve, reject) => {
    const child = spawn('bash', ['scripts/translate.sh', src, file, lang], { cwd: root, stdio: 'inherit' })
    child.on('error', reject)
    child.on('close', code => code === 0 ? resolve() :
      reject(Object.assign(new Error(`Translation exited ${code}`), { fatal: code === 78 })))
  })) {
  for (const [src, file, lang] of pairs) {
    if (sourcePath(file) !== src || file.split('/')[0] !== lang) throw new Error('Invalid translation pair')
  }
  const failures = []
  const attempted = []
  let fatalError
  let index = 0
  const worker = async () => {
    while (index < pairs.length && !fatalError) {
      const [src, file, lang] = pairs[index++]
      attempted.push([src, file, lang])
      const original = current(root, file)
      write(root, file, null)
      try {
        await translate(src, file, lang)
        run(root, 'python3', ['scripts/validate-translation.py', src, file])
      } catch (error) {
        write(root, file, original)
        failures.push(file)
        console.warn(`Translation failed; preserved previous content: ${file}`)
        if (error.fatal) fatalError = error
      }
    }
  }
  await Promise.all([worker(), worker()])
  recordBatch(root, attempted, failures)
  if (fatalError) throw fatalError
  return failures
}

function changedFiles(root) {
  return [...new Set([
    ...run(root, 'git', ['diff', '--name-only', '-z', 'HEAD']).split('\0'),
    ...run(root, 'git', ['ls-files', '--others', '--exclude-standard', '-z']).split('\0')
  ].filter(Boolean))]
}

export function refreshBatch(root, ref = 'origin/main') {
  const latest = git(root, 'rev-parse', ref)
  if (latest === git(root, 'rev-parse', 'HEAD')) return
  const base = tree(root, 'HEAD')
  const files = changedFiles(root)
  if (files.some(file => !allowedPath(file))) throw new Error('Unexpected non-translation changes')
  const saved = new Map(files.map(file => [file, current(root, file)]))
  const previous = readState(current(root, statePath))
  for (const file of files) {
    if (base.has(file)) run(root, 'git', ['restore', '--source=HEAD', '--staged', '--worktree', '--', file])
    else {
      run(root, 'git', ['rm', '--cached', '--ignore-unmatch', '--', file])
      write(root, file, null)
    }
  }
  run(root, 'git', ['checkout', '--detach', latest])
  const main = tree(root, 'HEAD')
  const state = readState(blob(root, main.get(statePath)))
  const pending = new Set([...state.pending, ...previous.pending])
  for (const [file, incoming] of saved) {
    if (file === statePath) continue
    if (file === headingPath) {
      if (incoming) mergeHeadings(root, incoming)
      continue
    }
    if (translatedPath(file)) {
      const src = sourcePath(file)
      if (!main.has(src)) {
        write(root, file, null); delete state.sources[file]; pending.delete(file)
      } else if (!incoming || previous.sources[file] !== main.get(src).oid ||
                 !overlay(root, file, blob(root, base.get(file)), incoming)) pending.add(file)
      else { state.sources[file] = previous.sources[file]; pending.delete(file) }
    } else overlay(root, file, blob(root, base.get(file)), incoming)
  }
  for (const [file, sha] of Object.entries(previous.sources)) {
    if (main.get(sourcePath(file))?.oid === sha && !pending.has(file)) state.sources[file] = sha
    else if (main.get(sourcePath(file))?.oid !== sha) pending.add(file)
  }
  for (const src of new Set([...base.keys(), ...main.keys()])) {
    if (!src.startsWith('en/') || !src.endsWith('.md') || base.get(src)?.oid === main.get(src)?.oid) continue
    for (const lang of languages) {
      const file = `${lang}${src.slice(2)}`
      if (translatedPath(file) && current(root, file) && state.sources[file] !== main.get(src)?.oid) pending.add(file)
    }
  }
  for (const file of [...pending]) {
    if (!main.has(sourcePath(file))) {
      write(root, file, null); delete state.sources[file]; pending.delete(file)
    }
  }
  writeState(root, state, pending)
}

function openBatches(root) {
  return JSON.parse(gh(root, 'pr', 'list', '--state', 'open', '--label', 'automated-translation',
    '--limit', '100', '--json', 'number,headRefName,createdAt,isDraft,isCrossRepository'))
    .filter(pr => !pr.isCrossRepository && (pr.headRefName === batchBranch || legacyBranch.test(pr.headRefName)))
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
}

export function publishBatch(root, { draft = true } = {}) {
  run(root, 'git', ['fetch', 'origin', 'main'])
  if (git(root, 'rev-parse', 'HEAD') !== git(root, 'rev-parse', 'origin/main')) {
    throw new Error('main changed after preparation/review; pending work remains in the draft batch. Re-run.')
  }
  if (changedFiles(root).some(file => !allowedPath(file))) throw new Error('Unexpected non-translation changes')
  run(root, 'git', ['add', '--', 'cn', 'jp', 'es', statePath, headingPath])
  if (!git(root, 'diff', '--cached', '--name-only')) return null
  const oldHead = git(root, 'ls-remote', '--heads', 'origin', `refs/heads/${batchBranch}`).split(/\s/)[0]
  const tracked = spawnSync('git', ['show-ref', '--verify', '--hash', `refs/remotes/origin/${batchBranch}`],
    { cwd: root, encoding: 'utf8' })
  if (tracked.error) throw tracked.error
  const expected = tracked.status === 0 ? tracked.stdout.trim() : ''
  if (oldHead !== expected) throw new Error('Translation branch changed after preparation; re-run to preserve its updates.')
  const prior = openBatches(root)
  const existing = prior.find(pr => pr.headRefName === batchBranch)
  if (draft && existing && !existing.isDraft) gh(root, 'pr', 'ready', String(existing.number), '--undo')
  run(root, 'git', ['checkout', '-B', batchBranch])
  run(root, 'git', ['-c', 'user.name=github-actions[bot]', '-c', 'user.email=github-actions[bot]@users.noreply.github.com',
    'commit', '-m', draft ? 'docs: queue pending GitBook translations' : 'docs: sync GitBook translations'])
  run(root, 'git', ['push', `--force-with-lease=refs/heads/${batchBranch}:${oldHead}`, 'origin', `HEAD:refs/heads/${batchBranch}`])
  const state = readState(current(root, statePath))
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-pr-'))
  let number
  try {
    const body = path.join(directory, 'body.md')
    fs.writeFileSync(body, [
      'GitBook용 cn/jp/es 번역을 최신 main 기준으로 하나의 PR에 누적합니다.',
      '',
      '본문·목차 번역 모델: Bedrock Mantle `openai.gpt-6-luna` (us-east-1). VitePress 게시 언어: ko/en.',
      `대기 또는 재시도 대상: ${state.pending.length}개.`,
      '',
      draft ? '번역·품질 검토가 완료되면 자동으로 리뷰 가능한 상태로 전환됩니다.' :
        '최종 diff가 85/100 이상 품질 검토를 통과했습니다. 실패한 대상은 대기열에 남겨 재시도합니다.'
    ].join('\n'))
    gh(root, 'label', 'create', 'automated-translation', '--color', '1D76DB', '--description', 'Automated GitBook translations', '--force')
    if (existing) {
      number = existing.number
      gh(root, 'pr', 'edit', String(number), '--title', 'docs: sync GitBook translations (cn/jp/es)', '--body-file', body)
      if (!draft && existing.isDraft) gh(root, 'pr', 'ready', String(number))
    } else {
      const args = ['pr', 'create', '--base', 'main', '--head', batchBranch, '--title',
        'docs: sync GitBook translations (cn/jp/es)', '--label', 'automated-translation', '--body-file', body]
      if (draft) args.push('--draft')
      // Search/list indexes can lag behind PR creation; use its returned URL.
      const created = gh(root, ...args).match(/\/pull\/(\d+)\s*$/)
      if (!created) throw new Error('PR created but its number could not be parsed')
      number = Number(created[1])
    }
  } finally { fs.rmSync(directory, { recursive: true, force: true }) }
  // Close only same-repository legacy automation PRs after their changes/queue
  // have been persisted in the replacement branch. Never delete their branches.
  for (const pr of prior.filter(pr => legacyBranch.test(pr.headRefName))) gh(root, 'pr', 'close', String(pr.number))
  return number
}

export function checkpointBatch(root) {
  run(root, 'git', ['fetch', 'origin', 'main'])
  refreshBatch(root)
  publishBatch(root, { draft: true })
  const snapshot = git(root, 'rev-parse', 'HEAD')
  run(root, 'git', ['checkout', '--detach', 'origin/main'])
  // Keep the complete pending diff visible for the next chunk and final review.
  prepareBatch(root, { refs: [snapshot] })
}

function syncNewNavigation(root, pairs) {
  const sections = new Map()
  for (const [src, file, lang] of pairs) {
    if (!current(root, file)) continue
    const parts = src.split('/')
    const section = ['labs', 'quizzes'].includes(parts[1]) ? parts[2] : parts[1]
    if (!/^[a-z0-9-]+$/.test(section)) continue
    if (!sections.has(section)) sections.set(section, new Set())
    sections.get(section).add(lang)
  }
  for (const [section, langs] of sections) {
    for (const lang of langs) run(root, 'python3', ['scripts/sync-nav.py', section, lang])
  }
}

async function main() {
  const root = process.cwd()
  const command = process.argv[2]
  const pairsPath = process.env.TRANSLATION_PAIRS || '/tmp/pairs.txt'
  const failuresPath = process.env.TRANSLATION_FAILURES || '/tmp/translate-failures.txt'
  if (command === 'prepare') {
    run(root, 'git', ['fetch', 'origin', 'main'])
    run(root, 'git', ['checkout', '--detach', 'origin/main'])
    const prior = openBatches(root)
    for (const pr of prior) run(root, 'git', ['fetch', 'origin', pr.headRefName])
    // A merged/closed batch branch can still exist. Fetch it for the lease,
    // without importing its superseded results.
    if (!prior.some(pr => pr.headRefName === batchBranch) &&
        git(root, 'ls-remote', '--heads', 'origin', `refs/heads/${batchBranch}`)) {
      run(root, 'git', ['fetch', 'origin', batchBranch])
    }
    let before = process.env.TRANSLATION_BEFORE
    if (before && /^0+$/.test(before)) before = undefined
    if (!before) before = 'HEAD~1'
    if (before) before = git(root, 'merge-base', before, 'HEAD')
    const pairs = prepareBatch(root, {
      refs: prior.map(pr => `origin/${pr.headRefName}`), before,
      fillMissing: true,
      langs: languages
    })
    fs.writeFileSync(pairsPath, pairs.map(pair => pair.join(' ')).join('\n') + (pairs.length ? '\n' : ''))
    if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, `pair_count=${pairs.length}\n`)
    checkpointBatch(root)
    console.log(`Translation batch prepared: ${pairs.length} targets`)
  } else if (command === 'record') {
    const pairs = fs.readFileSync(pairsPath, 'utf8').trim().split('\n').filter(Boolean).map(line => line.split(' '))
    const failures = fs.existsSync(failuresPath) ? fs.readFileSync(failuresPath, 'utf8').trim().split('\n').filter(Boolean) : []
    recordBatch(root, pairs, failures)
  } else if (command === 'translate') {
    const pairs = fs.readFileSync(pairsPath, 'utf8').trim().split('\n').filter(Boolean).map(line => line.split(' '))
    const failures = []
    // Long queues can exceed runner lifetime. Persist validated results after
    // each 12 destinations, retaining draft status until the whole diff review.
    for (let index = 0; index < pairs.length; index += 12) {
      const chunk = pairs.slice(index, index + 12)
      const missing = chunk.filter(([, file]) => !current(root, file))
      failures.push(...await translateBatch(root, chunk))
      syncNewNavigation(root, missing)
      run(root, 'node', ['scripts/sync-translated-assets.mjs'])
      checkpointBatch(root)
      console.log(`Saved draft progress: ${Math.min(index + 12, pairs.length)}/${pairs.length} targets`)
    }
    fs.writeFileSync(failuresPath, failures.join('\n') + (failures.length ? '\n' : ''))
  } else if (command === 'refresh') {
    run(root, 'git', ['fetch', 'origin', 'main'])
    refreshBatch(root)
  } else if (command === 'publish') {
    console.log(`Translation PR: ${publishBatch(root, { draft: false }) ?? 'no changes'}`)
  } else throw new Error('Usage: translation-batch.mjs prepare|translate|record|refresh|publish')
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error.message); process.exitCode = 1 })
}
