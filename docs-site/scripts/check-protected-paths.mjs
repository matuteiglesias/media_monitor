import { execFileSync } from 'node:child_process'
import process from 'node:process'

export const protectedPaths = [
  /^vercel\.json$/,
  /^apps\/news_site\//,
  /^scripts\/(?:build_site_snapshot|validate_site_snapshot|roll_site|publish_news_site)(?:\.|$)/,
]

export function changedPaths(base, head, cwd = process.cwd()) {
  return execFileSync('git', ['diff', '--name-only', `${base}...${head}`], { cwd, encoding: 'utf8' })
    .split(/\r?\n/).filter(Boolean)
}

export function protectedChanges(paths) { return paths.filter(file => protectedPaths.some(pattern => pattern.test(file))) }

const isMain = process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href
if (isMain) {
  const base = process.argv[2] || process.env.GITHUB_BASE_SHA
  const head = process.argv[3] || process.env.GITHUB_HEAD_SHA
  if (!base || !head) {
    console.log('Protected-path diff guard skipped: base/head Git SHA context is unavailable.')
    process.exit(0)
  }
  const changed = changedPaths(base, head)
  const blocked = protectedChanges(changed)
  if (blocked.length) {
    console.error(`Docs frontend change also modifies protected news deployment paths:\n${blocked.join('\n')}`)
    process.exit(1)
  }
  console.log(`Protected-path diff guard passed (${changed.length} changed paths inspected).`)
}
