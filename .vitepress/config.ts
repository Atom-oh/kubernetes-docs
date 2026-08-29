import fs from 'node:fs'
import path from 'node:path'
import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import { summarySidebar } from './summary'
import { vitepressBuildScope } from './site-scope.mjs'
import { extractDescription, localeAlternates, normalizeReadmeHref } from './seo.mjs'

const GA_ID = 'G-GWVLEW5JLL'
const ADSENSE_CLIENT = 'ca-pub-6267917556914416'
const FAVICON = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="50" y="78" font-size="80" text-anchor="middle">☸️</text></svg>')}`

// Build-memory bisection toggles (all default OFF — normal builds are unaffected):
//   VP_DISABLE_SEARCH=1     drop local search (MiniSearch indexing of every page)
//   VP_DISABLE_MERMAID=1    skip the withMermaid wrapper (mermaid bundling)
const DISABLE_SEARCH = process.env.VP_DISABLE_SEARCH === '1'
const DISABLE_MERMAID = process.env.VP_DISABLE_MERMAID === '1'

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
          const html = new state.Token('html_block', '', 0)
          html.content =
            `<div class="archmap-embed">` +
            `<iframe src="/kubernetes-docs/archmaps/${base}.html" title="${base}" loading="lazy" allowfullscreen></iframe>` +
            `<p class="archmap-embed__caption"><a href="${href}" target="_blank" rel="noopener">${caption}</a></p>` +
            `</div>\n`
          let start = i
          // Drop the static PNG paragraph directly above (same diagram) — the
          // iframe replaces it on the VitePress site.
          const prevInline = tokens[i - 2]
          if (
            i >= 3 &&
            tokens[i - 3].type === 'paragraph_open' &&
            prevInline && prevInline.type === 'inline' && prevInline.children &&
            prevInline.children.some(
              (t) => t.type === 'image' && (t.attrGet('src') || '').includes(`${base}.png`)
            )
          ) {
            start = i - 3
          }
          tokens.splice(start, i + 3 - start, html)
          i = start
        }
      })
    }
  },
  transformPageData(pageData, { siteConfig }) {
    if (pageData.frontmatter.description) return
    const source = fs.readFileSync(
      path.join(siteConfig.srcDir, pageData.filePath),
      'utf8'
    )
    const description = extractDescription(source)
    if (description) pageData.description = description
  },
  transformHead({ pageData }) {
    return localeAlternates(pageData.relativePath).map(({ hreflang, href }) => [
      'link',
      { rel: 'alternate', hreflang, href }
    ])
  },
  sitemap: {
    hostname: 'https://www.atomai.click/kubernetes-docs/'
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
