import { onMounted, shallowRef } from 'vue'
import { withBase } from 'vitepress'
import { createStatisticsLoader, parseStatisticsSnapshot } from './statistics-data.mjs'

const snapshot = shallowRef<ReturnType<typeof parseStatisticsSnapshot> | null>(null)
const failed = shallowRef(false)
const load = createStatisticsLoader({
  getUrl: () => withBase('/site-statistics.json'),
  onSnapshot: (value: ReturnType<typeof parseStatisticsSnapshot>) => { snapshot.value = value },
  onError: (value: boolean) => { failed.value = value }
})

export function useSiteStatistics() {
  onMounted(load)
  return { snapshot, failed, reload: load }
}
