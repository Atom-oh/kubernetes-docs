import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

// Sync starts from a clean checkout, then removes destinations so translate.sh
// can replace them. A failed attempt must restore HEAD, never stage a deletion.
export function restoreFailedTranslations(files, root = process.cwd()) {
  const unique = [...new Set(files.map(file => file.trim()).filter(Boolean))]
  for (const file of unique) {
    if (!/^(cn|jp|es)\/.+\.md$/.test(file) || path.posix.normalize(file) !== file) {
      throw new Error(`Invalid translated document path: ${file}`)
    }
  }
  for (const file of unique) {
    execFileSync('git', ['--literal-pathspecs', 'restore', '--worktree', '--', file], { cwd: root })
  }
  return unique
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const files = fs.readFileSync(process.argv[2], 'utf8').split('\n')
  console.log(`Restored ${restoreFailedTranslations(files).length} failed translation(s).`)
}
