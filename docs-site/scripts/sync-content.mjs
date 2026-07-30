import { cp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'

const root = path.resolve(import.meta.dirname, '../..')
const docs = path.join(root, 'docs')
const site = path.join(root, 'docs-site/.generated/site')
const scaffold = path.join(root, 'docs-site/scaffold')
const publicRoots = ['architecture', 'components', 'operations', 'reference', 'case-studies', 'maintenance']
const excludedPatterns = [
  /(^|\/)documentation_program\//, /(^|\/)notes\//, /(^|\/)legacy\//,
  /(^|\/)runbooks\//, /closure/i, /retrofit[_-]prompt/i, /(^|\/)storage\//,
  /(^|\/)data\//, /\.env(?:\.|$)/, /\.tfstate(?:\.|$)/
]

async function walk(dir, base = dir) {
  const out = []
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...await walk(full, base))
    else out.push(path.relative(base, full).split(path.sep).join('/'))
  }
  return out
}

try { await readdir(docs) } catch {
  throw new Error('Canonical ../docs is unavailable. In Vercel, enable “Include source files outside of the Root Directory in the Build Step”.')
}

await rm(path.dirname(site), { recursive: true, force: true })
await mkdir(site, { recursive: true })
await cp(scaffold, site, { recursive: true })

const all = await walk(docs)
const included = all.filter(file => file.endsWith('.md') && publicRoots.some(dir => file.startsWith(`${dir}/`)) && !excludedPatterns.some(rx => rx.test(file)))
const manifest = []
for (const file of included.sort()) {
  const source = path.join(docs, file)
  const destination = path.join(site, file)
  await mkdir(path.dirname(destination), { recursive: true })
  let content = await readFile(source, 'utf8')
  content = content.replace(/\]\(\.\.\/README\.md(#[^)]+)?\)/g, '](/start-here/$1)')
  content = content.replace(/\]\((\.\.\/)+(README\.md|AGENTS\.md|contracts\/[^)]+|infra\/[^)]+|apps\/[^)]+)\)/g,
    (_, ups, target) => `](https://github.com/matuteiglesias/media_monitor/blob/main/${target})`)
  await writeFile(destination, content)
  const route = `/${file.replace(/(?:\/index)?\.md$/, '')}`
  manifest.push({ source: `docs/${file}`, route, title: content.match(/^#\s+(.+)$/m)?.[1] ?? file })
}

const excluded = all.filter(file => file.endsWith('.md') && !included.includes(file)).sort().map(file => ({ source: `docs/${file}`, reason: 'outside curated public capability roots' }))
await writeFile(path.join(site, 'public-route-manifest.json'), JSON.stringify({ generatedAt: new Date().toISOString(), routes: manifest }, null, 2) + '\n')
await writeFile(path.join(site, 'exclusion-report.json'), JSON.stringify({ generatedAt: new Date().toISOString(), deliberateReplacements: [{ source: 'docs/README.md', publicRoute: '/start-here/', rationale: 'public front door omits internal documentation-program navigation' }], excluded }, null, 2) + '\n')
console.log(`Synced ${manifest.length} canonical pages; excluded ${excluded.length}.`)
