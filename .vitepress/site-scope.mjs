// Locales with hand-edited source text. llms.txt, the docs MCP server and the
// ko/en parity checks cover only these.
export const supportedLocales = ['ko', 'en']

// Machine translations of en (translation workflows). They are published too,
// but cover only part of en: pages they lack redirect to the English page and
// links to them point at English (scripts/build-vitepress-locales.mjs and
// .vitepress/translation-fallback.mjs).
export const translatedLocales = ['cn', 'jp', 'es']

// Every locale VitePress publishes, in language-menu order.
export const publishedLocales = [...supportedLocales, ...translatedLocales]

// Per-locale codes: page lang attribute, hreflang, Open Graph locale.
export const localeCodes = {
  ko: { lang: 'ko-KR', hreflang: 'ko', ogLocale: 'ko_KR' },
  en: { lang: 'en-US', hreflang: 'en', ogLocale: 'en_US' },
  cn: { lang: 'zh-CN', hreflang: 'zh-CN', ogLocale: 'zh_CN' },
  jp: { lang: 'ja-JP', hreflang: 'ja', ogLocale: 'ja_JP' },
  es: { lang: 'es-ES', hreflang: 'es', ogLocale: 'es_ES' }
}

const baseSrcExclude = [
  'README.md',
  'slide/**',
  'CLAUDE.md',
  'aws-architecture-review-request.md', // review material, not a guidebook page
  '**/SUMMARY.md',
  'docs/**', // internal plans/specs — never publish
  'assets/**', // diagram sources and maintenance READMEs are not articles
  'examples/**', // runnable code packages referenced by path, not pages; leaked into the sitemap
  'public/llms/**' // generated raw Markdown — copied as static files
]

export function createVitepressBuildScope(locale) {
  if (locale && !publishedLocales.includes(locale)) {
    throw new Error(`Unsupported VitePress locale: ${locale}`)
  }

  const locales = locale ? [locale] : publishedLocales
  const excludedPublishedLocales = publishedLocales
    .filter((publishedLocale) => !locales.includes(publishedLocale))
    .map((excludedLocale) => `${excludedLocale}/**`)

  return {
    locales,
    srcExclude: [...baseSrcExclude, ...excludedPublishedLocales],
    rewrites: Object.fromEntries(
      locales.flatMap((buildLocale) => [
        [`${buildLocale}/README.md`, `${buildLocale}/index.md`],
        // GitBook's section-index convention → clean directory URLs on VitePress
        [`${buildLocale}/:dir(.*)/README.md`, `${buildLocale}/:dir/index.md`]
      ])
    )
  }
}

const defaultScope = createVitepressBuildScope()

export const vitepressSrcExclude = defaultScope.srcExclude
export const vitepressRewrites = defaultScope.rewrites
export const vitepressBuildScope = createVitepressBuildScope(
  process.env.VITEPRESS_BUILD_LOCALE
)
