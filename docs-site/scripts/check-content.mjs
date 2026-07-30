import { readFile, readdir, stat } from 'node:fs/promises'
import path from 'node:path'

const project = path.resolve(import.meta.dirname, '..')
const site = path.join(project, '.generated/site')
const root = path.resolve(project, '..')
const manifest = JSON.parse(await readFile(path.join(site, 'public-route-manifest.json'), 'utf8'))
const exclusions = JSON.parse(await readFile(path.join(site, 'exclusion-report.json'), 'utf8'))

async function walk(dir, base = dir) {
  const result = []
  for (const item of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, item.name)
    if (item.isDirectory()) result.push(...await walk(full, base))
    else result.push(path.relative(base, full).split(path.sep).join('/'))
  }
  return result
}

const files = await walk(site)
const markdown = files.filter(file => file.endsWith('.md'))
const errors = []
const routes = new Set()
for (const file of markdown) {
  const route = `/${file.replace(/(?:\/index)?\.md$/, '')}`
  if (routes.has(route)) errors.push(`duplicate generated route: ${route}`)
  routes.add(route)
}
routes.clear()
for (const entry of manifest.routes) {
  if (routes.has(entry.route)) errors.push(`duplicate route: ${entry.route}`)
  routes.add(entry.route)
  const text = await readFile(path.join(root, entry.source), 'utf8')
  if (!/^#\s+.+/m.test(text) || !/(?:>|-) \*\*Status:/m.test(text)) errors.push(`missing governed title/status metadata: ${entry.source}`)
}

const forbidden = /documentation_program|(?:^|\/)notes(?:\/|$)|(?:^|\/)legacy(?:\/|$)|closure|retrofit[_-]prompt|\.env(?:\.|$)|\.tfstate(?:\.|$)|storage\/buses|data\/pf_out/i
for (const file of files) {
  if (forbidden.test(file)) errors.push(`forbidden generated path: ${file}`)
}
for (const entry of manifest.routes) {
  if (forbidden.test(entry.source) || forbidden.test(entry.route)) errors.push(`internal manifest entry: ${entry.source}`)
}

const required = ['index.md', 'system/index.md', 'lanes/index.md', 'artifacts/index.md', 'operations/index.md', 'case-studies/index.md']
for (const file of required) if (!files.includes(file)) errors.push(`missing top-level route: ${file}`)

for (const file of markdown) {
  const full = path.join(site, file)
  const text = await readFile(full, 'utf8')
  if (/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|(?:password|token|secret)\s*[:=]\s*["'][^"']{8,}["']/i.test(text)) {
    errors.push(`possible secret material in ${file}`)
  }
  for (const match of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const href = match[1].split('#')[0]
    if (!href || /^(?:https?:|mailto:|\/)/.test(href)) continue
    const resolved = path.resolve(path.dirname(full), decodeURIComponent(href))
    const candidates = [resolved, `${resolved}.md`, path.join(resolved, 'index.md')]
    let found = false
    for (const candidate of candidates) { try { if ((await stat(candidate)).isFile()) found = true } catch {} }
    if (!found) errors.push(`dead relative link in ${file}: ${match[1]}`)
  }
}

const expected = JSON.parse(await readFile(path.join(project, 'scripts/isolation-baseline.json'), 'utf8'))
for (const [file, digest] of Object.entries(expected)) {
  const { createHash } = await import('node:crypto')
  const actual = createHash('sha256').update(await readFile(path.join(root, file))).digest('hex')
  if (actual !== digest) errors.push(`protected deployment file changed: ${file}`)
}
if (!exclusions.excluded.length) errors.push('exclusion report is empty')
if (errors.length) { console.error(errors.join('\n')); process.exit(1) }
console.log(`Content check passed: ${manifest.routes.length} canonical routes, ${markdown.length} rendered pages, ${exclusions.excluded.length} exclusions.`)
