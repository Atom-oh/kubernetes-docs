import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import { nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vitepress'
import { initQuizProgress } from './quiz-progress.mjs'
import './custom.css'

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
      cleanupQuizProgress()
      cleanupQuizProgress = initQuizProgress(document, route.path)
    }

    onMounted(initPageEnhancements)
    watch(() => route.path, () => nextTick(initPageEnhancements))
    onUnmounted(() => cleanupQuizProgress())
  },
}
