import { readFile, readdir, stat } from 'node:fs/promises'
import path from 'node:path'

async function exists(file) { try { return (await stat(file)).isDirectory() } catch { return false } }
async function walk(dir, base = dir) {
  const files = []
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) files.push(...await walk(full, base))
    else files.push(path.relative(base, full).split(path.sep).join('/'))
  }
  return files
}

/** Validate the docs product by structure and data flow, never sibling byte identity. */
export async function validateBuildIsolation({ project, root, site }) {
  const errors = []
  const configPath = path.join(project, 'vercel.json')
  const configText = await readFile(configPath, 'utf8')
  const config = JSON.parse(configText)
  if (config.outputDirectory !== 'dist') errors.push('docs vercel outputDirectory must be dist')
  if (config.buildCommand !== 'npm run build') errors.push('docs vercel buildCommand must be npm run build')
  if (config.rewrites?.some(rule => /(?:^|\/)web(?:\/|$)/.test(`${rule.source} ${rule.destination}`))) {
    errors.push('docs vercel config must not rewrite to /web')
  }

  const packageText = await readFile(path.join(project, 'package.json'), 'utf8')
  const syncText = await readFile(path.join(project, 'scripts/sync-content.mjs'), 'utf8')
  const ownedControlText = `${configText}\n${packageText}\n${syncText}`
  if (/apps\/news_site|npm\s+--prefix|validate_site_snapshot|publish_news_site|build_site_snapshot/.test(ownedControlText)) {
    errors.push('docs build controls invoke or import a news/publication build surface')
  }
  if (!/const docs = path\.join\(root, 'docs'\)/.test(syncText)) errors.push('sync source must be repository-root docs/')
  if (/readFile\([^\n]*(?:vercel\.json|apps\/news_site)|cp\([^\n]*(?:vercel\.json|apps\/news_site)/.test(syncText)) {
    errors.push('sync must not read or copy root/news deployment controls')
  }

  const manifest = JSON.parse(await readFile(path.join(site, 'public-route-manifest.json'), 'utf8'))
  for (const entry of manifest.routes) {
    if (!entry.source.startsWith('docs/') || entry.source.includes('..')) errors.push(`non-docs manifest source: ${entry.source}`)
    if (!entry.route.startsWith('/') || /(?:^|\/)web(?:\/|$)|apps\/news_site|storage\//.test(entry.route)) errors.push(`non-docs public route: ${entry.route}`)
  }

  // Paths are the exposure boundary. Canonical architecture prose may name a
  // news component, but no runtime file, snapshot, or /web route may be emitted.
  for (const output of [site, path.join(project, 'dist')]) {
    if (!await exists(output)) continue
    for (const file of await walk(output)) {
      if (/(?:^|\/)(?:web\/data|storage|apps\/news_site)(?:\/|$)|site_snapshot\.json|published_articles_latest\.jsonl/i.test(file)) {
        errors.push(`news runtime surface exposed in docs output: ${path.basename(output)}/${file}`)
      }
    }
  }
  return errors
}
