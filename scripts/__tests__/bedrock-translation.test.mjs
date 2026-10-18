import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('Bedrock translation rejects incomplete output, wrong providers, and fatal model/credential errors', () => {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
  execFileSync('python3', ['-m', 'unittest', 'scripts/__tests__/test_bedrock_translation.py'], {
    cwd: root, stdio: 'pipe'
  })
})
