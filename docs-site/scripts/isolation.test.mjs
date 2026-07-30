import assert from 'node:assert/strict'
import { execFileSync, spawnSync } from 'node:child_process'
import { mkdtemp, readFile, writeFile, mkdir } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { protectedChanges } from './check-protected-paths.mjs'

test('formatting and newline normalization are not protected changes', () => {
  assert.deepEqual(protectedChanges(['docs-site/vercel.json', 'docs-site/README.md']), [])
})

test('protected path ownership is explicit', () => {
  assert.deepEqual(protectedChanges(['vercel.json', 'apps/news_site/package.json', 'scripts/build_site_snapshot.py']), ['vercel.json', 'apps/news_site/package.json', 'scripts/build_site_snapshot.py'])
})

test('edit links use a CSP-safe string pattern', async () => {
  const config = await readFile(new URL('../scaffold/.vitepress/config.mts', import.meta.url), 'utf8')
  assert.match(config, /editLink:\s*\{\s*pattern:\s*['"]https:\/\/github\.com\/matuteiglesias\/media_monitor\/edit\/main\/docs\/:path['"]/)
  assert.doesNotMatch(config, /editLink:\s*\{\s*pattern:\s*\(/)
})

test('CLI guard passes docs-only diff and fails a protected synthetic diff', async () => {
  const repo = await mkdtemp(path.join(os.tmpdir(), 'docs-isolation-'))
  execFileSync('git', ['init', '-q'], { cwd: repo }); execFileSync('git', ['config', 'user.email', 'test@example.com'], { cwd: repo }); execFileSync('git', ['config', 'user.name', 'Test'], { cwd: repo })
  await mkdir(path.join(repo, 'docs-site')); await writeFile(path.join(repo, 'README.md'), 'base\n'); execFileSync('git', ['add', '.'], { cwd: repo }); execFileSync('git', ['commit', '-qm', 'base'], { cwd: repo }); const base = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repo, encoding: 'utf8' }).trim()
  await writeFile(path.join(repo, 'docs-site/README.md'), 'docs\n'); execFileSync('git', ['add', '.'], { cwd: repo }); execFileSync('git', ['commit', '-qm', 'docs'], { cwd: repo }); const docsHead = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repo, encoding: 'utf8' }).trim()
  assert.equal(spawnSync(process.execPath, [new URL('./check-protected-paths.mjs', import.meta.url).pathname, base, docsHead], { cwd: repo }).status, 0)
  await writeFile(path.join(repo, 'vercel.json'), '{}\n'); execFileSync('git', ['add', '.'], { cwd: repo }); execFileSync('git', ['commit', '-qm', 'protected'], { cwd: repo }); const protectedHead = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repo, encoding: 'utf8' }).trim()
  assert.equal(spawnSync(process.execPath, [new URL('./check-protected-paths.mjs', import.meta.url).pathname, base, protectedHead], { cwd: repo }).status, 1)
})
