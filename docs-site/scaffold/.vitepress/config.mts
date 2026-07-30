import { defineConfig } from 'vitepress'
import container from 'markdown-it-container'
import path from 'node:path'

const siteUrl = (process.env.DOCS_SITE_URL || '').replace(/\/$/, '')

export default defineConfig({
  title: 'Media Monitor',
  description: 'Engineering documentation for an evidence-driven editorial pipeline.',
  lang: 'en-US',
  outDir: path.resolve(import.meta.dirname, '../../../dist'),
  cleanUrls: true,
  lastUpdated: true,
  ignoreDeadLinks: false,
  markdown: {
    config(md) {
      const fence = md.renderer.rules.fence!
      md.renderer.rules.fence = (tokens, index, options, env, self) => {
        const token = tokens[index]
        if (['mermaid', 'mmd'].includes(token.info.trim())) {
          return `<MermaidDiagram id="mermaid-${index}" graph="${encodeURIComponent(token.content)}" />`
        }
        return fence(tokens, index, options, env, self)
      }
      for (const kind of ['contract', 'human-gate', 'failure', 'evidence', 'current-status']) {
        md.use(container, kind, {
          render(tokens, index) {
            if (tokens[index].nesting === 1) {
              const title = tokens[index].info.trim().slice(kind.length).trim() || kind.replace('-', ' ')
              return `<div class="custom-block ${kind}"><p class="custom-block-title">${md.utils.escapeHtml(title)}</p>\n`
            }
            return '</div>\n'
          }
        })
      }
    }
  },
  sitemap: siteUrl ? { hostname: siteUrl } : undefined,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/signal-mark.svg' }],
    ['meta', { name: 'theme-color', content: '#a43e2f' }]
  ],
  themeConfig: {
    notFound: { title: 'Signal lost.', quote: 'The requested dispatch is not in the public documentation edition.', linkText: 'Return to the front page' },
    logo: '/signal-mark.svg',
    siteTitle: 'Media Monitor / Field Manual',
    search: { provider: 'local', options: { detailedView: true, miniSearch: { searchOptions: { fuzzy: 0.2, prefix: true } } } },
    nav: [
      { text: 'Start Here', link: '/start-here/' },
      { text: 'System', link: '/system/' },
      { text: 'Lanes', link: '/lanes/' },
      { text: 'Artifacts & Contracts', link: '/artifacts/' },
      { text: 'Operations', link: '/operations/' },
      { text: 'Case Studies', link: '/case-studies/' },
      { text: 'GitHub', link: 'https://github.com/matuteiglesias/media_monitor' }
    ],
    sidebar: {
      '/system/': [{ text: 'System', items: [
        { text: 'Overview', link: '/system/' }, { text: 'End-to-end architecture', link: '/architecture/system-overview' },
        { text: 'Ownership boundaries', link: '/architecture/lane-and-owner-boundaries' }, { text: 'Artifact state', link: '/architecture/artifact-ladder-and-state' },
        { text: 'Identity & replay', link: '/architecture/identity-provenance-and-replay' }, { text: 'Trust boundaries', link: '/architecture/trust-boundaries' }
      ]}],
      '/architecture/': [{ text: 'Architecture', items: [
        { text: 'System overview', link: '/architecture/system-overview' }, { text: 'Lane boundaries', link: '/architecture/lane-and-owner-boundaries' },
        { text: 'Artifact ladder', link: '/architecture/artifact-ladder-and-state' }, { text: 'Identity & replay', link: '/architecture/identity-provenance-and-replay' },
        { text: 'Trust boundaries', link: '/architecture/trust-boundaries' }
      ]}],
      '/lanes/': [{ text: 'Lanes', items: [{ text: 'Lane map', link: '/lanes/' }, { text: 'Acquire', link: '/components/news-acquire' }, { text: 'Enrich', link: '/components/news-enrich' }, { text: 'Editorial', link: '/components/news-editorial' }, { text: 'News site', link: '/components/news-site' }] }],
      '/components/': [{ text: 'Owner guides', items: [{ text: 'Acquire', link: '/components/news-acquire' }, { text: 'Enrich', link: '/components/news-enrich' }, { text: 'Editorial', link: '/components/news-editorial' }, { text: 'News site', link: '/components/news-site' }] }],
      '/artifacts/': [{ text: 'Artifacts & Contracts', items: [{ text: 'Guide', link: '/artifacts/' }, { text: 'Contracts & schemas', link: '/reference/contracts-and-schemas' }, { text: 'Buses, indexes & storage', link: '/reference/buses-indexes-and-storage' }, { text: 'Commands', link: '/reference/command-matrix' }, { text: 'Configuration', link: '/reference/configuration' }, { text: 'Status semantics', link: '/reference/status-and-error-semantics' }] }],
      '/reference/': [{ text: 'Reference', items: [{ text: 'Contracts & schemas', link: '/reference/contracts-and-schemas' }, { text: 'Buses, indexes & storage', link: '/reference/buses-indexes-and-storage' }, { text: 'Commands', link: '/reference/command-matrix' }, { text: 'Configuration', link: '/reference/configuration' }, { text: 'Status semantics', link: '/reference/status-and-error-semantics' }] }],
      '/operations/': [{ text: 'Operations', items: [{ text: 'Operations desk', link: '/operations/' }, { text: 'Local lanes', link: '/operations/local-lane-operation' }, { text: 'Sensing bundles', link: '/operations/sensing-run-bundles' }, { text: 'Compaction & recovery', link: '/operations/sensing-compaction-and-recovery' }, { text: 'AWS sensing', link: '/operations/aws-sensing-deployment' }, { text: 'Editorial last mile', link: '/operations/editorial-human-last-mile' }, { text: 'Site snapshot & Vercel', link: '/operations/site-snapshot-and-vercel' }] }],
      '/case-studies/': [{ text: 'Case Studies', items: [{ text: 'Case-study desk', link: '/case-studies/' }, { text: 'AWS immutable sensing', link: '/case-studies/aws-immutable-sensing-retrofit' }, { text: 'Deterministic publication', link: '/case-studies/deterministic-site-publication' }] }]
    },
    outline: { level: [2, 3], label: 'On this page' },
    editLink: { pattern: ({ filePath }) => ['architecture/', 'components/', 'operations/', 'reference/', 'case-studies/', 'maintenance/'].some(prefix => filePath.startsWith(prefix)) ? `https://github.com/matuteiglesias/media_monitor/edit/main/docs/${filePath}` : undefined, text: 'Edit canonical source on GitHub' },
    lastUpdated: { text: 'Source updated', formatOptions: { dateStyle: 'medium' } },
    socialLinks: [{ icon: 'github', link: 'https://github.com/matuteiglesias/media_monitor' }],
    footer: { message: 'Documentation presentation only — runtime authority remains in source and contracts.', copyright: 'Media Monitor' }
  },
})
