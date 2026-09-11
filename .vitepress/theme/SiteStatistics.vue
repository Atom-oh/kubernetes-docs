<script setup>
import { computed, ref } from 'vue'
import { useData, withBase } from 'vitepress'
import { useSiteStatistics } from './use-site-statistics'

defineProps({ compact: Boolean })
const { lang } = useData()
const { snapshot, failed, reload } = useSiteStatistics()
const metric = ref('views')
const korean = computed(() => lang.value.startsWith('ko'))
const copy = computed(() => korean.value ? {
  title: '방문 통계', period: '최근 30일', visitors: '방문자', views: '문서 조회',
  details: '통계 자세히 보기', loading: '방문 통계를 불러오는 중입니다.',
  unavailable: '통계를 연결하고 있습니다. 연결 후 실제 집계가 표시됩니다.',
  error: '통계를 불러오지 못했습니다.', retry: '다시 불러오기',
  updated: '마지막 갱신', stale: '갱신 지연 · 마지막 집계 표시 중',
  trend: '일별 추이', daily: '일별 수치 보기', date: '날짜',
  zero: '선택 기간에 집계된 문서 조회가 아직 없습니다.',
  limited: 'GA4 임계값·표본 추출·집계 제한의 영향을 받을 수 있는 보고서입니다. 보고되지 않은 값은 —로 표시합니다.',
  note: '방문자는 이 기간에 문서 사이트를 방문한 GA4 총 사용자 수입니다. 같은 사용자가 여러 날 방문하므로 일별 방문자 수를 더한 값과 다를 수 있습니다.',
  source: 'GA4 · 하루 한 번 갱신',
  delay: '오늘을 제외한 최근 30일입니다. 보고서 처리 지연·광고 차단·동의 상태에 따라 실제 이용과 차이가 있을 수 있습니다.',
  event: '문서 조회수는 2026-09-10부터 수집하며, 문서를 열거나 다른 문서로 이동한 횟수를 집계합니다.'
} : {
  title: 'Visitor statistics', period: 'Last 30 days', visitors: 'Visitors', views: 'Document views',
  details: 'View statistics', loading: 'Loading visitor statistics.',
  unavailable: 'Statistics are being connected. Actual counts will appear once connected.',
  error: 'Statistics could not be loaded.', retry: 'Try again',
  updated: 'Last updated', stale: 'Update delayed · showing the last snapshot',
  trend: 'Daily activity', daily: 'View daily numbers', date: 'Date',
  zero: 'No document views have been reported for this period yet.',
  limited: 'GA4 reports thresholds, sampling, or aggregation limits for these results. Unreported values are shown as —.',
  note: 'Visitors are GA4 total users who visited this documentation site during the period. A person may visit on multiple days, so daily visitors do not add up to period visitors.',
  source: 'GA4 · updated daily',
  delay: 'The last 30 days exclude today. Reporting delays, ad blockers, and consent choices can affect the counts.',
  event: 'Document views have been collected since 2026-09-10. They count document opens and navigation between documents.'
})
const ready = computed(() => snapshot.value?.status === 'ready')
const limited = computed(() => ready.value && Object.values(snapshot.value.quality).some(Boolean))
const stale = computed(() => ready.value && Date.now() - Date.parse(snapshot.value.generatedAt) > 72 * 3600000)
const formatter = computed(() => new Intl.NumberFormat(korean.value ? 'ko-KR' : 'en-US'))
const number = value => value === null ? '—' : formatter.value.format(value)
const updated = computed(() => ready.value ? new Intl.DateTimeFormat(korean.value ? 'ko-KR' : 'en-US', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: snapshot.value.period.timeZone
}).format(new Date(snapshot.value.generatedAt)) : '')
const maximum = computed(() => ready.value ? Math.max(1, ...snapshot.value.daily.map(row => row[metric.value] ?? 0)) : 1)
const chartLabel = computed(() => `${copy.value.trend}: ${copy.value[metric.value]}`)
const statisticsLink = computed(() => withBase(`/${korean.value ? 'ko' : 'en'}/statistics`))
</script>

<template>
  <section class="site-statistics" :class="{ 'site-statistics--compact': compact }" :aria-label="copy.title">
    <div class="statistics-heading">
      <span class="statistics-eyebrow">{{ copy.period }}</span>
      <a v-if="compact" :href="statisticsLink" class="statistics-link">{{ copy.details }} <span aria-hidden="true">↗</span></a>
      <span v-else class="statistics-source">{{ copy.source }}</span>
    </div>

    <div v-if="!ready" class="statistics-status" role="status">
      <template v-if="failed">
        {{ copy.error }} <button type="button" class="statistics-retry" @click="reload">{{ copy.retry }}</button>
      </template>
      <template v-else>{{ snapshot ? copy.unavailable : copy.loading }}</template>
    </div>

    <template v-else>
      <dl class="statistics-totals">
        <div v-for="key in ['visitors', 'views']" :key="key" class="statistics-card">
          <dt>{{ copy[key] }}</dt>
          <dd>{{ number(snapshot.totals[key]) }}</dd>
        </div>
      </dl>
      <p class="statistics-period">
        <time>{{ snapshot.period.start }}</time> – <time>{{ snapshot.period.end }}</time>
        <span> · {{ snapshot.period.timeZone }}</span>
      </p>
      <p class="statistics-updated">{{ copy.updated }}: <time :datetime="snapshot.generatedAt">{{ updated }}</time></p>
      <p v-if="stale" class="statistics-warning" role="status">{{ copy.stale }}</p>
      <p v-if="limited" class="statistics-warning">{{ copy.limited }}</p>

      <template v-if="!compact">
        <p v-if="snapshot.totals.views === 0" class="statistics-status">{{ copy.zero }}</p>
        <div class="statistics-chart-heading">
          <h2>{{ copy.trend }}</h2>
          <div class="statistics-switch" :aria-label="copy.trend">
            <button v-for="key in ['views', 'visitors']" :key="key" type="button"
              :aria-pressed="metric === key" @click="metric = key">{{ copy[key] }}</button>
          </div>
        </div>
        <div class="statistics-chart" role="img" :aria-label="chartLabel">
          <div class="statistics-scale">{{ number(maximum) }}</div>
          <div class="statistics-bars">
            <div v-for="row in snapshot.daily" :key="row.date" class="statistics-bar-slot"
              :title="`${row.date}: ${number(row[metric])} ${copy[metric]}`">
              <div v-if="row[metric] !== null" class="statistics-bar"
                :style="{ height: `${row[metric] / maximum * 100}%` }" />
              <span v-else class="statistics-missing">—</span>
            </div>
          </div>
          <div class="statistics-chart-dates">
            <time>{{ snapshot.period.start }}</time>
            <time>{{ snapshot.period.end }}</time>
          </div>
        </div>
        <details class="statistics-daily">
          <summary>{{ copy.daily }}</summary>
          <table>
            <thead><tr><th scope="col">{{ copy.date }}</th><th scope="col">{{ copy.visitors }}</th><th scope="col">{{ copy.views }}</th></tr></thead>
            <tbody>
              <tr v-for="row in [...snapshot.daily].reverse()" :key="row.date">
                <th scope="row">{{ row.date }}</th><td>{{ number(row.visitors) }}</td><td>{{ number(row.views) }}</td>
              </tr>
            </tbody>
          </table>
        </details>
        <div class="statistics-explanation">
          <p>{{ copy.note }}</p>
          <p>{{ copy.delay }}</p>
          <p>{{ copy.event }}</p>
        </div>
      </template>
    </template>
  </section>
</template>

<style scoped>
.site-statistics { margin: 24px 0; color: var(--vp-c-text-1); word-break: keep-all; overflow-wrap: anywhere; }
.statistics-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.statistics-eyebrow { font-size: 13px; font-weight: 650; color: var(--vp-c-text-2); }
.statistics-source { font-size: 12px; color: var(--vp-c-text-2); }
.statistics-link { font-size: 13px; color: var(--vp-c-brand-1); text-decoration: none; }
.statistics-totals { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 0; }
.statistics-card { border: 1px solid var(--vp-c-divider); border-radius: 12px; padding: 22px 24px; background: var(--vp-c-bg-soft); }
.statistics-card dt { font-size: 14px; color: var(--vp-c-text-2); }
.statistics-card dd { margin: 12px 0 0; font-size: clamp(26px, 4vw, 38px); line-height: 1.2; font-weight: 650; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.statistics-period, .statistics-updated { margin: 12px 0 0; font-size: 12px; line-height: 1.6; color: var(--vp-c-text-2); }
.statistics-updated { margin-top: 2px; }
.statistics-warning { color: var(--vp-c-warning-1); font-size: 13px; line-height: 1.7; }
.statistics-status { border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg-soft); border-radius: 10px; padding: 18px; font-size: 14px; line-height: 1.7; }
.statistics-retry { color: var(--vp-c-brand-1); text-decoration: underline; padding: 4px 8px; }
.statistics-chart-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin: 36px 0 20px; }
.statistics-chart-heading h2 { font-size: 18px; line-height: 1.4; border: 0; margin: 0; padding: 0; }
.statistics-switch { display: flex; gap: 4px; padding: 4px; border-radius: 10px; background: var(--vp-c-bg-soft); }
.statistics-switch button { padding: 8px 12px; min-height: 40px; border-radius: 7px; font-size: 13px; color: var(--vp-c-text-2); }
.statistics-switch button[aria-pressed="true"] { background: var(--vp-c-bg); color: var(--vp-c-brand-1); box-shadow: 0 1px 4px #0001; }
button:focus-visible, a:focus-visible, summary:focus-visible { outline: 2px solid var(--vp-c-brand-1); outline-offset: 3px; }
.statistics-chart { margin: 0 0 24px; }
.statistics-scale { font-size: 12px; font-variant-numeric: tabular-nums; color: var(--vp-c-text-2); margin-bottom: 8px; }
.statistics-bars { display: flex; height: 180px; gap: clamp(2px, .8vw, 8px); border-bottom: 1px solid var(--vp-c-divider); background: repeating-linear-gradient(to top, transparent, transparent calc(50% - 1px), var(--vp-c-divider) calc(50% - 1px), var(--vp-c-divider) 50%); }
.statistics-bar-slot { display: flex; align-items: flex-end; justify-content: center; flex: 1 1 0; min-width: 0; height: 100%; }
.statistics-bar { width: 100%; max-width: 22px; background: var(--vp-c-brand-2); border-radius: 3px 3px 0 0; }
.statistics-bar-slot:hover .statistics-bar { background: var(--vp-c-brand-1); }
.statistics-missing { font-size: 10px; color: var(--vp-c-text-3); }
.statistics-chart-dates { display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: var(--vp-c-text-2); }
.statistics-daily { padding: 12px 0; border-top: 1px solid var(--vp-c-divider); border-bottom: 1px solid var(--vp-c-divider); }
.statistics-daily summary { cursor: pointer; font-size: 14px; font-weight: 600; }
.statistics-daily table { display: table; width: 100%; font-size: 13px; font-variant-numeric: tabular-nums; }
.statistics-daily th:not(:first-child), .statistics-daily td { text-align: right; }
.statistics-explanation { margin-top: 24px; color: var(--vp-c-text-2); font-size: 13px; line-height: 1.8; }
.statistics-explanation p { margin: 8px 0; }
.site-statistics--compact { margin: 32px 0 24px; padding-top: 20px; border-top: 1px solid var(--vp-c-divider); }
.site-statistics--compact .statistics-card { padding: 14px 18px; }
.site-statistics--compact .statistics-card dd { font-size: 25px; margin-top: 6px; }
@media (max-width: 480px) {
  .statistics-totals { gap: 10px; }
  .statistics-card { padding: 16px; }
  .statistics-chart-heading { gap: 12px; }
  .statistics-daily th, .statistics-daily td { padding: 8px; }
}
</style>
