import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('Knative troubleshooting updates create a new Revision and route the demo service to it', async () => {
  const source = await readFile(new URL('../../ko/autoscaling/03-knative.md', import.meta.url), 'utf8')
  const patches = [...source.matchAll(/kubectl patch ksvc order-api -n knative-demo --type merge -p '\s*([\s\S]*?)'/g)]
    .map(match => JSON.parse(match[1]))
    .filter(patch => patch.spec?.template?.metadata?.annotations)
  assert.equal(patches.length, 2)
  for (const patch of patches) {
    const name = patch.spec.template.metadata.name
    assert.ok(name === null || (typeof name === 'string' && !['order-api-v1', 'order-api-v2', 'order-api-green'].includes(name)),
      'the patch must clear or replace the existing immutable Revision name')
    assert.ok(patch.spec.traffic?.some(target =>
      target.percent === 100 &&
      (target.latestRevision === true || (name && target.revisionName === name))),
    'the new configuration must receive the demo service traffic')
  }
})
