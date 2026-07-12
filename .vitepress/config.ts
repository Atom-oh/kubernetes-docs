import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import { summarySidebar } from './summary'

const GA_ID = 'G-GWVLEW5JLL'

export default withMermaid(defineConfig({
  title: 'Kubernetes & Amazon EKS Training',
  base: '/kubernetes-docs/',
  srcDir: '.',
  srcExclude: ['slide/**', 'CLAUDE.md', '**/SUMMARY.md'],
  rewrites: {
    'README.md': 'index.md',
    'ko/README.md': 'ko/index.md',
    'en/README.md': 'en/index.md',
    'cn/README.md': 'cn/index.md',
    'jp/README.md': 'jp/index.md',
    'es/README.md': 'es/index.md'
  },
  ignoreDeadLinks: true,
  sitemap: {
    hostname: 'https://www.atomai.click/kubernetes-docs/'
  },
  head: [
    ['script', { async: '', src: `https://www.googletagmanager.com/gtag/js?id=${GA_ID}` }],
    ['script', {}, `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config','${GA_ID}');`]
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
    },
    cn: {
      label: '中文',
      lang: 'zh-CN',
      link: '/cn/',
      themeConfig: { sidebar: summarySidebar('cn') }
    },
    jp: {
      label: '日本語',
      lang: 'ja-JP',
      link: '/jp/',
      themeConfig: { sidebar: summarySidebar('jp') }
    },
    es: {
      label: 'Español',
      lang: 'es-ES',
      link: '/es/',
      themeConfig: { sidebar: summarySidebar('es') }
    }
  },
  themeConfig: {
    search: { provider: 'local' },
    outline: 'deep'
  }
}))
