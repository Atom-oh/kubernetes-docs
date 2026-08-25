export const supportedLocales = ['ko', 'en']

const baseSrcExclude = [
  'README.md',
  'slide/**',
  'CLAUDE.md',
  '**/SUMMARY.md',
  'cn/**',
  'jp/**',
  'es/**'
]

export function createVitepressBuildScope(locale) {
  if (locale && !supportedLocales.includes(locale)) {
    throw new Error(`Unsupported VitePress locale: ${locale}`)
  }

  const locales = locale ? [locale] : supportedLocales
  const excludedPublishedLocales = supportedLocales
    .filter((supportedLocale) => !locales.includes(supportedLocale))
    .map((excludedLocale) => `${excludedLocale}/**`)

  return {
    locales,
    srcExclude: [...baseSrcExclude, ...excludedPublishedLocales],
    rewrites: Object.fromEntries(
      locales.map((buildLocale) => [
        `${buildLocale}/README.md`,
        `${buildLocale}/index.md`
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
