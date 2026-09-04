import fs from 'node:fs'
import path from 'node:path'
import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import { summarySidebar } from './summary'
import { vitepressBuildScope } from './site-scope.mjs'
import {
  breadcrumbTrail,
  canonicalUrl,
  extractDescription,
  extractLastUpdated,
  localeAlternates,
  normalizeReadmeHref,
  siteName,
  socialHeadTags,
  structuredData
} from './seo.mjs'

const GA_ID = 'G-GWVLEW5JLL'
const ADSENSE_CLIENT = 'ca-pub-6267917556914416'
const FAVICON = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="50" y="78" font-size="80" text-anchor="middle">☸️</text></svg>')}`

// Build-memory bisection toggles (all default OFF — normal builds are unaffected):
//   VP_DISABLE_SEARCH=1     drop local search (MiniSearch indexing of every page)
//   VP_DISABLE_MERMAID=1    skip the withMermaid wrapper (mermaid bundling)
const DISABLE_SEARCH = process.env.VP_DISABLE_SEARCH === '1'
const DISABLE_MERMAID = process.env.VP_DISABLE_MERMAID === '1'

// markdown-it gives us raw alt text; it lands in an HTML attribute and in
// element content, so both need escaping.
function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// Sitemap lastmod source: the document header date, keyed by clean URL path.
function buildLastUpdatedIndex() {
  const index = new Map<string, string>()
  const walk = (directory: string) => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const entryPath = path.join(directory, entry.name)
      if (entry.isDirectory()) {
        walk(entryPath)
        continue
      }
      if (!entry.name.endsWith('.md')) continue
      const lastUpdated = extractLastUpdated(fs.readFileSync(entryPath, 'utf8'))
      if (!lastUpdated) continue
      const relative = path.relative(process.cwd(), entryPath).split(path.sep).join('/')
      const clean = relative
        .replace(/\.md$/, '')
        .replace(/(^|\/)README$/, '$1')
        .replace(/(^|\/)index$/, '$1')
      index.set(normalizeSitemapUrl(clean), lastUpdated)
    }
  }
  for (const locale of ['ko', 'en']) {
    if (fs.existsSync(locale)) walk(locale)
  }
  return index
}

function normalizeSitemapUrl(url: string) {
  return url.replace(/^\/+/, '').replace(/\/+$/, '')
}

const lastUpdatedIndex = buildLastUpdatedIndex()

const config = defineConfig({
  title: 'Cloud Native Operations',
  description:
    'Hands-on Kubernetes and Amazon EKS training — core concepts, networking, service mesh, observability, quizzes, and labs.',
  base: '/kubernetes-docs/',
  srcDir: '.',
  srcExclude: vitepressBuildScope.srcExclude,
  rewrites: vitepressBuildScope.rewrites,
  cleanUrls: true,
  ignoreDeadLinks: false,
  markdown: {
    languageAlias: {
      promql: 'sql',
      logql: 'sql',
      traceql: 'sql',
      rego: 'hcl',
      river: 'hcl'
    },
    config(md) {
      // Content links target README.md (GitBook convention). The README→index
      // rewrites change the emitted routes, but VitePress does not map link
      // hrefs through rewrites — normalize them here so rendered links match.
      md.core.ruler.push('readme_links', (state) => {
        for (const blockToken of state.tokens) {
          if (blockToken.type !== 'inline' || !blockToken.children) continue
          for (const token of blockToken.children) {
            if (token.type !== 'link_open') continue
            const href = token.attrGet('href')
            if (href) token.attrSet('href', normalizeReadmeHref(href))
          }
        }
      })
      // Archify diagrams: the shared markdown embeds a static PNG followed by
      // an "interactive diagram" link to public/archmaps/ (GitBook shows both
      // as-is). On the VitePress site, replace that pair with an inline iframe
      // so the animated interactive viewer renders directly in the page.
      md.core.ruler.push('archify_embed', (state) => {
        const tokens = state.tokens
        const ARCHMAP = /https?:\/\/[^/]+\/kubernetes-docs\/archmaps\/([a-z0-9-]+)\.html/
        for (let i = 0; i < tokens.length; i++) {
          if (tokens[i].type !== 'paragraph_open') continue
          const inline = tokens[i + 1]
          if (!inline || inline.type !== 'inline' || !inline.children) continue
          const open = inline.children.find((t) => t.type === 'link_open')
          const href = open && open.attrGet('href')
          const match = href && href.match(ARCHMAP)
          if (!match) continue
          const base = match[1]
          const caption = base.startsWith('ko-') ? '전체 화면으로 열기 ↗' : 'Open full screen ↗'
          // The static PNG paragraph directly above describes the same diagram.
          // The iframe replaces the image, but its alt text is the only prose
          // description of the diagram on the page — keep it as the accessible
          // name and as indexable text instead of dropping it with the image.
          let alt = ''
          // Tag the static PNG paragraph directly above (same diagram) instead
          // of dropping it. On wide screens CSS hides it and only the iframe
          // shows; under 768px the iframe is hidden and this PNG takes over,
          // because the viewer's toolbar and nodes get clipped at that width
          // with no way to scroll to them. Keeping the original tokens (rather
          // than emitting a raw <img>) lets VitePress rewrite the asset path as
          // usual, and medium-zoom still picks it up for tap-to-zoom.
          const prevInline = tokens[i - 2]
          if (
            i >= 3 &&
            tokens[i - 3].type === 'paragraph_open' &&
            prevInline && prevInline.type === 'inline' && prevInline.children
          ) {
            const image = prevInline.children.find(
              (t) => t.type === 'image' && (t.attrGet('src') || '').includes(`${base}.png`)
            )
            if (image) {
              alt = image.attrGet('alt') || image.content || ''
              const existing = tokens[i - 3].attrGet('class')
              tokens[i - 3].attrSet(
                'class',
                existing ? `${existing} archmap-embed__fallback` : 'archmap-embed__fallback'
              )
            }
          }
          const html = new state.Token('html_block', '', 0)
          html.content =
            `<figure class="archmap-embed">` +
            `<iframe src="/kubernetes-docs/archmaps/${base}.html" title="${escapeHtml(alt || base)}" loading="lazy" allowfullscreen></iframe>` +
            `<figcaption class="archmap-embed__caption">` +
            (alt ? `<span class="archmap-embed__alt">${escapeHtml(alt)}</span>` : '') +
            `<a href="${href}" target="_blank" rel="noopener">${caption}</a>` +
            `</figcaption>` +
            `</figure>\n`
          // Replace only the link paragraph; the PNG paragraph above stays.
          tokens.splice(i, 3, html)
        }
      })
    }
  },
  transformPageData(pageData, { siteConfig }) {
    const source = fs.readFileSync(
      path.join(siteConfig.srcDir, pageData.filePath),
      'utf8'
    )
    if (!pageData.frontmatter.description) {
      const description = extractDescription(source)
      if (description) pageData.description = description
    }
    // Carried on frontmatter so transformHead can date the structured data
    // without re-reading the file.
    const lastUpdated = extractLastUpdated(source)
    if (lastUpdated) pageData.frontmatter.lastUpdatedISO = lastUpdated
  },
  transformHead({ pageData }) {
    // The 404 page is a rendering shell, not a document: it must not be
    // indexed and has nothing to be canonical to.
    if (pageData.relativePath === '404.md') {
      return [['meta', { name: 'robots', content: 'noindex' }]]
    }

    const url = canonicalUrl(pageData.relativePath)
    const locale = pageData.relativePath.split('/')[0]
    const title = pageData.title || siteName
    const description = pageData.description || pageData.frontmatter.description
    const crumbs = breadcrumbTrail(pageData.relativePath, pageData.title)

    return [
      ['link', { rel: 'canonical', href: url }],
      ...localeAlternates(pageData.relativePath).map(({ hreflang, href }) => [
        'link',
        { rel: 'alternate', hreflang, href }
      ]),
      ...socialHeadTags({ title, description, url, locale }),
      [
        'script',
        { type: 'application/ld+json' },
        structuredData({
          title,
          description,
          url,
          locale,
          lastUpdated: pageData.frontmatter.lastUpdatedISO,
          crumbs
        })
      ]
    ]
  },
  sitemap: {
    hostname: 'https://www.atomai.click/kubernetes-docs/',
    // Stamp each entry with the document's own "last updated" header so
    // recrawls follow real edits instead of the whole tree looking equally old.
    transformItems: (items) =>
      items.map((item) => {
        const lastmod = lastUpdatedIndex.get(normalizeSitemapUrl(item.url))
        return lastmod ? { ...item, lastmod } : item
      })
  },
  head: [
    ['link', { rel: 'icon', href: FAVICON }],
    ['script', { async: '', src: `https://www.googletagmanager.com/gtag/js?id=${GA_ID}` }],
    ['script', {}, `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config','${GA_ID}');`],
    ['script', { async: '', src: `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`, crossorigin: 'anonymous' }]
  ],
  locales: {
    ko: {
      label: '한국어',
      lang: 'ko-KR',
      link: '/ko/',
      description:
        '쿠버네티스와 Amazon EKS 실무 학습 자료 — 핵심 개념, 네트워킹, 서비스 메시, 옵저버빌리티, 퀴즈와 실습 랩까지 한 곳에서.',
      themeConfig: { sidebar: summarySidebar('ko') }
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      description:
        'Hands-on Kubernetes and Amazon EKS training — core concepts, networking, service mesh, observability, quizzes, and labs.',
      themeConfig: { sidebar: summarySidebar('en') }
    }
  },
  themeConfig: {
    ...(DISABLE_SEARCH ? {} : { search: { provider: 'local' as const } }),
    outline: 'deep'
  }
})

export default DISABLE_MERMAID ? config : withMermaid(config)
