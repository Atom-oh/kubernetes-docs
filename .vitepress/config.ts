import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import { summarySidebar } from './summary'

const GA_ID = 'G-GWVLEW5JLL'
const ADSENSE_CLIENT = 'ca-pub-6267917556914416'
const FAVICON = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="50" y="78" font-size="80" text-anchor="middle">☸️</text></svg>')}`

// Build-memory bisection toggles (all default OFF — normal builds are unaffected):
//   VP_DISABLE_SEARCH=1     drop local search (MiniSearch indexing of every page)
//   VP_DISABLE_MERMAID=1    skip the withMermaid wrapper (mermaid bundling)
//   VP_LOCALES=ko,en        build only the listed locales, excluding the rest
const ALL_LOCALES = ['ko', 'en', 'cn', 'jp', 'es'] as const
const ACTIVE_LOCALES = process.env.VP_LOCALES
  ? process.env.VP_LOCALES.split(',').map(s => s.trim()).filter(l => (ALL_LOCALES as readonly string[]).includes(l))
  : [...ALL_LOCALES]
const EXCLUDED_LOCALES = ALL_LOCALES.filter(l => !ACTIVE_LOCALES.includes(l))
const DISABLE_SEARCH = process.env.VP_DISABLE_SEARCH === '1'
const DISABLE_MERMAID = process.env.VP_DISABLE_MERMAID === '1'

const localeConfig = (label: string, lang: string, dir: string) => ({
  label,
  lang,
  link: `/${dir}/`,
  themeConfig: { sidebar: summarySidebar(dir) }
})

const LOCALE_DEFS: Record<string, { label: string; lang: string }> = {
  ko: { label: '한국어', lang: 'ko-KR' },
  en: { label: 'English', lang: 'en-US' },
  cn: { label: '中文', lang: 'zh-CN' },
  jp: { label: '日本語', lang: 'ja-JP' },
  es: { label: 'Español', lang: 'es-ES' }
}

const config = defineConfig({
  title: 'Kubernetes & Amazon EKS Training',
  base: '/kubernetes-docs/',
  srcDir: '.',
  srcExclude: ['slide/**', 'CLAUDE.md', '**/SUMMARY.md', ...EXCLUDED_LOCALES.map(l => `${l}/**`)],
  rewrites: {
    'README.md': 'index.md',
    ...Object.fromEntries(ACTIVE_LOCALES.map(l => [`${l}/README.md`, `${l}/index.md`]))
  },
  ignoreDeadLinks: true,
  sitemap: {
    hostname: 'https://www.atomai.click/kubernetes-docs/'
  },
  head: [
    ['link', { rel: 'icon', href: FAVICON }],
    ['script', { async: '', src: `https://www.googletagmanager.com/gtag/js?id=${GA_ID}` }],
    ['script', {}, `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config','${GA_ID}');`],
    ['script', { async: '', src: `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`, crossorigin: 'anonymous' }]
  ],
  locales: Object.fromEntries(
    ACTIVE_LOCALES.map(l => [l, localeConfig(LOCALE_DEFS[l].label, LOCALE_DEFS[l].lang, l)])
  ),
  themeConfig: {
    ...(DISABLE_SEARCH ? {} : { search: { provider: 'local' as const } }),
    outline: 'deep'
  }
})

export default DISABLE_MERMAID ? config : withMermaid(config)
