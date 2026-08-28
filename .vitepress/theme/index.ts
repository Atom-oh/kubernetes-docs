import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import { nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vitepress'
import { initQuizProgress } from './quiz-progress.mjs'
import './custom.css'

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
  setup() {
    const route = useRoute()
    let cleanupQuizProgress = () => {}

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

    onMounted(initPageEnhancements)
    watch(() => route.path, () => nextTick(initPageEnhancements))
    onUnmounted(() => cleanupQuizProgress())

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
