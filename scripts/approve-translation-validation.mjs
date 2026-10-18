const branch = 'docs/translate-sync'
const bot = 'github-actions[bot]'

export function isTranslationPath(file) {
  if (file.split('/').some(part => part === '..' || part === '.')) return false
  return file === '.github/translation-state.json' ||
    file === '.github/i18n-heading-map.json' ||
    /^(cn|jp|es)\/[A-Za-z0-9_./-]+\.md$/.test(file) ||
    /^(cn|jp|es)\/\.gitbook\/assets\/[A-Za-z0-9_.-]+\.(png|svg|jpg|jpeg|webp|gif)$/i.test(file)
}

export async function approveTranslationValidation({ github, context }) {
  const repository = context.payload.repository
  const runId = context.payload.workflow_run?.id
  if (!repository?.id || !runId) return { approved: false, reason: 'missing event metadata' }

  const { data: run } = await github.rest.actions.getWorkflowRun({
    ...context.repo, run_id: runId
  })
  if (run.event !== 'pull_request' || run.actor?.login !== bot ||
      run.head_branch !== branch || run.head_repository?.id !== repository.id ||
      run.path !== '.github/workflows/pr-validate.yml') {
    return { approved: false, reason: 'not a trusted translation validation run' }
  }
  if (run.conclusion !== 'action_required' && run.status !== 'waiting') {
    return { approved: false, reason: 'not awaiting approval' }
  }
  if (run.pull_requests?.length !== 1) {
    return { approved: false, reason: 'run must reference one pull request' }
  }

  const pullNumber = run.pull_requests[0].number
  const parameters = { ...context.repo, pull_number: pullNumber }
  const { data: pull } = await github.rest.pulls.get(parameters)
  if (pull.state !== 'open' || pull.user?.login !== bot ||
      pull.head?.repo?.id !== repository.id || pull.base?.repo?.id !== repository.id ||
      pull.head?.ref !== branch || pull.base?.ref !== repository.default_branch ||
      pull.head?.sha !== run.head_sha) {
    return { approved: false, reason: 'pull request identity or head changed' }
  }

  const files = await github.paginate(github.rest.pulls.listFiles, {
    ...parameters, per_page: 100
  })
  if (!files.length || files.length !== pull.changed_files ||
      files.some(file => !isTranslationPath(file.filename) ||
        (file.previous_filename && !isTranslationPath(file.previous_filename)))) {
    return { approved: false, reason: 'changes exceed translation scope' }
  }

  // Do not approve an old checkpoint after the publisher has updated the PR.
  const { data: latest } = await github.rest.pulls.get(parameters)
  if (latest.state !== 'open' || latest.head?.sha !== run.head_sha ||
      latest.base?.ref !== repository.default_branch) {
    return { approved: false, reason: 'pull request advanced during verification' }
  }

  try {
    await github.rest.actions.approveWorkflowRun({ ...context.repo, run_id: runId })
  } catch (error) {
    // A maintainer or another run may have approved it while checks were running.
    if (error.status === 403 && /not waiting for approval/i.test(
      error.response?.data?.message || error.message || ''
    )) return { approved: false, reason: 'approval already resolved' }
    throw error
  }
  return { approved: true, runId, pullNumber, head: run.head_sha }
}
