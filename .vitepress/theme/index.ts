import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import { nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vitepress'
import { initQuizProgress } from './quiz-progress.mjs'
import { createDocViewTracker } from './analytics.mjs'
import StatisticsLayout from './StatisticsLayout.vue'
import './custom.css'

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void
  }
}

const LANG_SWITCH_LINK_SELECTOR = '.VPNavBarTranslations a, .VPNavScreenTranslations a'

// VitePress's SPA router corrupts route.data.relativePath (drops the
// `/kubernetes-docs/` base) when a client-side navigation's page-chunk lookup
// fails — e.g. a stale hashmap after a redeploy. The language switcher then
// rebuilds its next link from that corrupted path, and each click compounds
// another `kubernetes-docs/<locale>/` layer into the URL. A `target`
// attribute makes the router's click handler skip interception entirely, so
// the switch always does a normal full-page navigation instead.
const hardenLangSwitchLinks = () => {
  document.querySelectorAll(LANG_SWITCH_LINK_SELECTOR).forEach((a) => a.setAttribute('target', '_self'))
}

export default {
  extends: DefaultTheme,
  Layout: StatisticsLayout,
  setup() {
    const route = useRoute()
    const router = useRouter()
    let cleanupQuizProgress = () => {}
    let trackDocView = (_location: string, _title: string) => {}
    let originalAfterRouteChange: typeof router.onAfterRouteChange
    let previousAfterRouteChange: typeof router.onAfterRouteChange

    const afterRouteChange = async (to: string) => {
      await previousAfterRouteChange?.(to)
      await nextTick()
      trackDocView(window.location.href, document.title)
    }

    const initZoom = () => {
      // exclude images wrapped in a link — clicking those should navigate, not zoom
      mediumZoom('.vp-doc :not(a) > img', { background: 'var(--vp-c-bg)' })
    }

    const initPageEnhancements = () => {
      initZoom()
      hardenLangSwitchLinks()
      cleanupQuizProgress()
      cleanupQuizProgress = initQuizProgress(document, route.path)
    }

    onMounted(() => {
      trackDocView = createDocViewTracker(
        document.referrer,
        (...args: unknown[]) => window.gtag?.(...args)
      )
      // route.path omits query strings; the completion hook also covers
      // query-only navigation and browser back/forward.
      originalAfterRouteChange = router.onAfterRouteChange
      previousAfterRouteChange = originalAfterRouteChange ?? router.onAfterRouteChanged
      router.onAfterRouteChange = afterRouteChange
      initPageEnhancements()
      trackDocView(window.location.href, document.title)
    })
    watch(() => route.path, () => nextTick(initPageEnhancements))
    onUnmounted(() => cleanupQuizProgress())
    onUnmounted(() => {
      if (router.onAfterRouteChange === afterRouteChange) {
        router.onAfterRouteChange = originalAfterRouteChange
      }
    })

    // The mobile hamburger menu's translations panel only enters the DOM
    // once opened, after any route-change re-tagging has already run.
    let observer: MutationObserver | undefined
    onMounted(() => {
      observer = new MutationObserver(hardenLangSwitchLinks)
      observer.observe(document.body, { childList: true, subtree: true })
    })
    onUnmounted(() => observer?.disconnect())
  },
}
