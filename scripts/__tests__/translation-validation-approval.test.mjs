import assert from 'node:assert/strict'
import test from 'node:test'
import { approveTranslationValidation, isTranslationPath } from '../approve-translation-validation.mjs'

function fixture({ run = {}, pull = {}, files, latest, approvalError } = {}) {
  const head = 'a'.repeat(40)
  const repository = { id: 1, default_branch: 'main' }
  const completePull = {
    state: 'open', user: { login: 'github-actions[bot]' }, changed_files: 2,
    head: { ref: 'docs/translate-sync', sha: head, repo: { id: 1 } },
    base: { ref: 'main', repo: { id: 1 } }, ...pull
  }
  const calls = []
  let reads = 0
  const github = {
    rest: {
      actions: {
        getWorkflowRun: async () => ({ data: {
          id: 12, event: 'pull_request', actor: { login: 'github-actions[bot]' },
          head_branch: 'docs/translate-sync', head_repository: { id: 1 },
          head_sha: head, path: '.github/workflows/pr-validate.yml',
          conclusion: 'action_required', status: 'completed',
          pull_requests: [{ number: 362 }], ...run
        } }),
        approveWorkflowRun: async args => {
          calls.push(args)
          if (approvalError) throw approvalError
        }
      },
      pulls: {
        get: async () => ({ data: ++reads === 2 && latest ? latest : completePull }),
        listFiles: () => {}
      }
    },
    paginate: async () => files || [
      { filename: 'jp/kernel/01-container-primitives.md' },
      { filename: '.github/translation-state.json' }
    ]
  }
  const context = { repo: { owner: 'Atom-oh', repo: 'kubernetes-docs' },
    payload: { repository, workflow_run: { id: 12 } } }
  return { github, context, calls, completePull }
}

test('translation-only bot checkpoint is approved with exact run identity', async () => {
  const input = fixture()
  assert.equal((await approveTranslationValidation(input)).approved, true)
  assert.deepEqual(input.calls, [{ owner: 'Atom-oh', repo: 'kubernetes-docs', run_id: 12 }])
})

test('forks, other actors, other branches and other workflows receive no approval', async () => {
  for (const run of [
    { head_repository: { id: 2 } }, { actor: { login: 'outsider' } },
    { head_branch: 'other' }, { path: '.github/workflows/deploy.yml' },
    { event: 'push' }, { pull_requests: [] }
  ]) {
    const input = fixture({ run })
    assert.equal((await approveTranslationValidation(input)).approved, false)
    assert.equal(input.calls.length, 0)
  }
})

test('untrusted pull identity, stale heads, and truncated files receive no approval', async () => {
  for (const pull of [
    { user: { login: 'outsider' } }, { state: 'closed' },
    { head: { ref: 'docs/translate-sync', sha: 'b'.repeat(40), repo: { id: 1 } } },
    { head: { ref: 'docs/translate-sync', sha: 'a'.repeat(40), repo: { id: 2 } } },
    { base: { ref: 'other', repo: { id: 1 } } }, { changed_files: 3 }
  ]) {
    const input = fixture({ pull })
    assert.equal((await approveTranslationValidation(input)).approved, false)
    assert.equal(input.calls.length, 0)
  }
})

test('executable and workflow changes, including renames out of scope, are rejected', async () => {
  for (const filename of ['package.json', 'scripts/run.mjs',
    '.github/workflows/pr-validate.yml', 'cn/../scripts/run.md']) {
    const input = fixture({ files: [
      { filename }, { filename: '.github/translation-state.json' }
    ] })
    assert.equal((await approveTranslationValidation(input)).approved, false)
    assert.equal(input.calls.length, 0)
  }
  const input = fixture({ files: [
    { filename: 'cn/a.md', previous_filename: '.github/workflows/run.yml' },
    { filename: '.github/translation-state.json' }
  ] })
  assert.equal((await approveTranslationValidation(input)).approved, false)
  assert.equal(input.calls.length, 0)
})

test('publisher advancing the PR during checks prevents approval', async () => {
  const original = fixture().completePull
  const input = fixture({ latest: { ...original,
    head: { ...original.head, sha: 'b'.repeat(40) } } })
  assert.equal((await approveTranslationValidation(input)).approved, false)
  assert.equal(input.calls.length, 0)
})

test('running checks and concurrently resolved approvals need no retry', async () => {
  const running = fixture({ run: { status: 'in_progress', conclusion: null } })
  assert.equal((await approveTranslationValidation(running)).approved, false)
  assert.equal(running.calls.length, 0)
  const error = Object.assign(new Error('This workflow run is not waiting for approval'), { status: 403 })
  const concurrent = fixture({ approvalError: error })
  assert.equal((await approveTranslationValidation(concurrent)).reason, 'approval already resolved')
})

test('translation paths permit existing batch outputs and reject other content', () => {
  for (const file of ['cn/SUMMARY.md', 'jp/quizzes/security/16-gwlb-geneve-inspection-quiz.md',
    'es/.gitbook/assets/en-eks-01-0.png', '.github/i18n-heading-map.json']) {
    assert.equal(isTranslationPath(file), true)
  }
  for (const file of ['en/a.md', '.aws/credentials', 'cn/./a.md', 'cn/assets/code.js']) {
    assert.equal(isTranslationPath(file), false)
  }
})
