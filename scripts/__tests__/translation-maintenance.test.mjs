import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { restoreFailedTranslations } from '../restore-failed-translations.mjs'
import { syncTranslatedAssets } from '../sync-translated-assets.mjs'

test('failed translations restore deleted or partial originals without reverting successful translations', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-restore-'))
  try {
    fs.mkdirSync(path.join(root, 'jp'))
    for (const name of ['deleted', 'partial', 'successful']) fs.writeFileSync(path.join(root, 'jp', `${name}.md`), `# Original ${name}\n`)
    const git = args => execFileSync('git', args, { cwd: root, stdio: 'pipe' })
    git(['init', '-q'])
    git(['add', 'jp'])
    git(['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture'])
    fs.rmSync(path.join(root, 'jp/deleted.md'))
    fs.writeFileSync(path.join(root, 'jp/partial.md'), '# Incomplete')
    fs.writeFileSync(path.join(root, 'jp/successful.md'), '# New translation\n')
    restoreFailedTranslations(['jp/deleted.md', 'jp/partial.md', 'jp/partial.md', ''], root)
    assert.equal(fs.readFileSync(path.join(root, 'jp/deleted.md'), 'utf8'), '# Original deleted\n')
    assert.equal(fs.readFileSync(path.join(root, 'jp/partial.md'), 'utf8'), '# Original partial\n')
    assert.equal(fs.readFileSync(path.join(root, 'jp/successful.md'), 'utf8'), '# New translation\n')
    assert.throws(() => restoreFailedTranslations(['en/source.md'], root), /Invalid/)
    assert.throws(() => restoreFailedTranslations(['jp/../en/source.md'], root), /Invalid/)
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})

test('referenced locale images are copied from English without modifying prose or duplicating shared assets', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-assets-'))
  try {
    for (const directory of ['en/.gitbook/assets', 'cn/topic', 'assets']) fs.mkdirSync(path.join(root, directory), { recursive: true })
    const prose = '# 本文\n\n![图](../.gitbook/assets/en-diagram.png)\n\n![共享](../../assets/shared.svg)\n\n```md\n![example](../.gitbook/assets/nonexistent.png)\n```\n'
    fs.writeFileSync(path.join(root, 'cn/topic/page.md'), prose)
    fs.writeFileSync(path.join(root, 'en/.gitbook/assets/en-diagram.png'), 'image bytes')
    fs.writeFileSync(path.join(root, 'assets/shared.svg'), '<svg/>')
    const result = syncTranslatedAssets(root)
    assert.equal(result.copied.length, 1)
    assert.deepEqual(result.unresolved, [])
    assert.equal(fs.readFileSync(path.join(root, 'cn/.gitbook/assets/en-diagram.png'), 'utf8'), 'image bytes')
    assert.equal(fs.readFileSync(path.join(root, 'cn/topic/page.md'), 'utf8'), prose)
    assert.deepEqual(syncTranslatedAssets(root).copied, [])
    fs.writeFileSync(path.join(root, 'en/.gitbook/assets/en-diagram.png'), 'updated image')
    assert.equal(syncTranslatedAssets(root).copied.length, 1)
    assert.equal(fs.readFileSync(path.join(root, 'cn/.gitbook/assets/en-diagram.png'), 'utf8'), 'updated image')
    fs.appendFileSync(path.join(root, 'cn/topic/page.md'), '\n![missing](../../assets/missing.svg)\n')
    assert.equal(syncTranslatedAssets(root).unresolved.length, 1)
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})

test('stale image case and relative depth follow the English source while translated prose and code remain intact', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-paths-'))
  try {
    for (const directory of ['en/.gitbook/assets', 'en/topic', 'jp/topic']) fs.mkdirSync(path.join(root, directory), { recursive: true })
    fs.writeFileSync(path.join(root, 'en/.gitbook/assets/en-readme-0.png'), 'image')
    fs.writeFileSync(path.join(root, 'en/topic/page.md'), '# English\n\n![Diagram](../.gitbook/assets/en-readme-0.png)\n')
    const translated = '# 日本語\n\n![図](../../.gitbook/assets/en-README-0.png)\n\n```md\n![example](../../.gitbook/assets/en-README-0.png)\n```\n'
    fs.writeFileSync(path.join(root, 'jp/topic/page.md'), translated)
    const assetOnly = syncTranslatedAssets(root, ['jp'], { repairPaths: false })
    assert.deepEqual(assetOnly.repairedLinks, [])
    assert.equal(assetOnly.unresolved.length, 1)
    assert.equal(fs.readFileSync(path.join(root, 'jp/topic/page.md'), 'utf8'), translated)
    const result = syncTranslatedAssets(root)
    assert.equal(result.repairedLinks.length, 1)
    assert.deepEqual(result.unresolved, [])
    assert.equal(fs.readFileSync(path.join(root, 'jp/topic/page.md'), 'utf8'),
      translated.replace('![図](../../.gitbook/assets/en-README-0.png)', '![図](../.gitbook/assets/en-readme-0.png)'))
    assert.equal(fs.readFileSync(path.join(root, 'jp/.gitbook/assets/en-readme-0.png'), 'utf8'), 'image')
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})

test('translation validation rejects changed code and link targets even when counts and size match', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-fidelity-'))
  const validator = fileURLToPath(new URL('../validate-translation.py', import.meta.url))
  try {
    const source = '# Source\n\nA source paragraph for this example.\n\n```yaml\napiVersion: v1\nkind: Pod\n```\n\n[Reference](https://example.org/reference)\n'
    const translated = source.replace('# Source', '# Translated').replace('A source paragraph', 'A translated paragraph')
    const src = path.join(root, 'source.md'), dst = path.join(root, 'translated.md')
    fs.writeFileSync(src, source)
    fs.writeFileSync(dst, translated)
    execFileSync('python3', [validator, src, dst], { stdio: 'pipe' })
    fs.writeFileSync(dst, translated.replace('kind: Pod', 'kind: Job'))
    assert.throws(() => execFileSync('python3', [validator, src, dst], { stdio: 'pipe' }))
    fs.writeFileSync(dst, translated.replace('example.org/reference', 'example.org/different'))
    assert.throws(() => execFileSync('python3', [validator, src, dst], { stdio: 'pipe' }))
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})

test('translation validation preserves both poster and video destinations of linked images', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-video-links-'))
  const validator = fileURLToPath(new URL('../validate-translation.py', import.meta.url))
  try {
    const source = '# Demo\n\nThe recorded video is a functional check in a simulated environment.\n\n[![Recorded demo](poster.jpg)](https://presentation.atomai.click/demo.mp4)\n\n[![Second demo](<second.jpg>)](<https://presentation.atomai.click/second.mp4>)\n'
    const translated = source.replace('# Demo', '# 演示').replace('Recorded demo', '实录演示').replace('Second demo', '第二个演示')
    const src = path.join(root, 'source.md'), dst = path.join(root, 'translated.md')
    fs.writeFileSync(src, source)
    fs.writeFileSync(dst, translated)
    execFileSync('python3', [validator, src, dst], { stdio: 'pipe' })
    for (const changed of [
      translated.replace('/demo.mp4', '/wrong.mp4'),
      translated.replace('/second.mp4', '/different.mp4'),
      translated.replace('[![实录演示](poster.jpg)](https://presentation.atomai.click/demo.mp4)', '![实录演示](poster.jpg)'),
      translated.replace('poster.jpg', 'wrong.jpg')
    ]) {
      fs.writeFileSync(dst, changed)
      assert.throws(() => execFileSync('python3', [validator, src, dst], { stdio: 'pipe' }),
        error => /link\/image target mismatch/.test(error.stderr.toString()))
    }
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})

test('complete Chinese prose can be shorter than English without accepting an empty summary', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-chinese-size-'))
  const validator = fileURLToPath(new URL('../validate-translation.py', import.meta.url))
  try {
    fs.mkdirSync(path.join(root, 'cn'))
    const source = '# Source\n\nThe operator reconciles the declared cluster state. It observes resource changes, creates the required workload objects, and reports status. Use matching software versions and verify permissions before deployment. A successful reconciliation does not prove that every application request succeeds.\n'
    const translated = '# 说明\n\nOperator 将实际集群状态协调至声明状态，观察资源变化，创建所需的工作负载对象并报告状态。部署前，应使用匹配的软件版本并验证权限。协调成功并不能证明每个应用请求都能成功。\n'
    const src = path.join(root, 'source.md'), dst = path.join(root, 'cn/page.md')
    assert.ok(translated.length / source.length < 0.4)
    fs.writeFileSync(src, source)
    fs.writeFileSync(dst, translated)
    execFileSync('python3', [validator, src, dst], { stdio: 'pipe' })
    fs.writeFileSync(dst, '# 说明\n\n略。\n')
    assert.throws(() => execFileSync('python3', [validator, src, dst], { stdio: 'pipe' }))
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})

test('image path repair changes only link destinations, preserving repeated paths in inline code and labels', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translation-target-spans-'))
  try {
    for (const directory of ['en/.gitbook/assets', 'en/topic', 'jp/topic']) fs.mkdirSync(path.join(root, directory), { recursive: true })
    fs.writeFileSync(path.join(root, 'en/.gitbook/assets/diagram.png'), 'image')
    fs.writeFileSync(path.join(root, 'en/topic/page.md'), '![Diagram](../.gitbook/assets/diagram.png)\n')
    const translated = [
      '`../../.gitbook/assets/diagram.png` ![../../.gitbook/assets/diagram.png](../../.gitbook/assets/diagram.png "../../.gitbook/assets/diagram.png") ![Again](../../.gitbook/assets/diagram.png)',
      '<img alt="../../.gitbook/assets/diagram.png" src="../../.gitbook/assets/diagram.png">',
      '[../../.gitbook/assets/diagram.png]: <../../.gitbook/assets/diagram.png>'
    ].join('\n')
    fs.writeFileSync(path.join(root, 'jp/topic/page.md'), translated)
    const result = syncTranslatedAssets(root)
    assert.equal(result.repairedLinks.length, 4)
    assert.deepEqual(result.unresolved, [])
    assert.equal(fs.readFileSync(path.join(root, 'jp/topic/page.md'), 'utf8'), [
      '`../../.gitbook/assets/diagram.png` ![../../.gitbook/assets/diagram.png](../.gitbook/assets/diagram.png "../../.gitbook/assets/diagram.png") ![Again](../.gitbook/assets/diagram.png)',
      '<img alt="../../.gitbook/assets/diagram.png" src="../.gitbook/assets/diagram.png">',
      '[../../.gitbook/assets/diagram.png]: <../.gitbook/assets/diagram.png>'
    ].join('\n'))
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})
