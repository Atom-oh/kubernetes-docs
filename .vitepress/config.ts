import { defineConfig } from 'vitepress'
import { summarySidebar } from './summary'

const GA_ID = 'G-XXXXXXXXXX' // TODO: replace with the real GA4 measurement ID

export default defineConfig({
  title: 'Kubernetes & Amazon EKS Training',
  base: '/kubernetes-docs/',
  srcDir: '.',
  srcExclude: ['slide/**', 'CLAUDE.md', '**/SUMMARY.md'],
  rewrites: { 'README.md': 'index.md' },
  ignoreDeadLinks: true,
  head: [
    ['script', { async: '', src: `https://www.googletagmanager.com/gtag/js?id=${GA_ID}` }],
    ['script', {}, `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config','${GA_ID}');`]
  ],
  locales: {
    ko: {
      label: '한국어',
      lang: 'ko-KR',
      link: '/ko/README',
      themeConfig: { sidebar: summarySidebar('ko') }
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/README',
      themeConfig: { sidebar: summarySidebar('en') }
    }
  },
  themeConfig: {
    search: { provider: 'local' },
    outline: 'deep'
  }
})
