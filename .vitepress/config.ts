import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import { summarySidebar } from './summary'
import { vitepressBuildScope } from './site-scope.mjs'

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
  base: '/kubernetes-docs/',
  srcDir: '.',
  srcExclude: vitepressBuildScope.srcExclude,
  rewrites: vitepressBuildScope.rewrites,
  ignoreDeadLinks: false,
  markdown: {
    languageAlias: {
      promql: 'sql',
      logql: 'sql',
      traceql: 'sql',
      rego: 'hcl',
      river: 'hcl'
    }
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
      themeConfig: { sidebar: summarySidebar('ko') }
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      themeConfig: { sidebar: summarySidebar('en') }
    }
  },
  themeConfig: {
    ...(DISABLE_SEARCH ? {} : { search: { provider: 'local' as const } }),
    outline: 'deep'
  }
})

export default DISABLE_MERMAID ? config : withMermaid(config)
