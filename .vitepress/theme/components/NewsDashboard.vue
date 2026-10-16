<script setup>
import { computed, ref, watch } from 'vue'
import { useData } from 'vitepress'
import news from '../news.generated.json'
import {
  NEWS_TOPICS, NEWS_CATEGORIES, filterNews, heatmapCount,
  newsDocumentUrl, newsStats, newsWeeks, recentWeeks
} from '../../../scripts/lib/news-dashboard.mjs'

const { lang, site } = useData()
const locale = computed(() => lang.value.startsWith('ko') ? 'ko' : 'en')
const t = (ko, en) => locale.value === 'ko' ? ko : en
const data = computed(() => news.locales[locale.value])
const entries = computed(() => data.value.entries)
const topic = ref('')
const category = ref('')
const week = ref('')
const query = ref('')
const limit = ref(12)
const weeks = computed(() => newsWeeks(entries.value))
const chartWeeks = computed(() => recentWeeks(weeks.value[0]))
const filtered = computed(() => filterNews(entries.value, {
  topic: topic.value, category: category.value, week: week.value, query: query.value
}))
const stats = computed(() => newsStats(filtered.value))
const chartEntries = computed(() => filterNews(entries.value, { category: category.value, query: query.value }))
const topicEntries = computed(() => filterNews(entries.value, { category: category.value, week: week.value, query: query.value }))
const active = computed(() => Boolean(topic.value || category.value || week.value || query.value))

const topics = {
  kubernetes: ['Kubernetes', 'Kubernetes', 'K8s'],
  eks: ['Amazon EKS', 'Amazon EKS', 'EKS'],
  networking: ['네트워킹', 'Networking', 'NET'],
  mesh: ['서비스 메시', 'Service mesh', 'MESH'],
  gitops: ['GitOps', 'GitOps', 'GIT'],
  autoscaling: ['오토스케일링', 'Autoscaling', 'SCALE'],
  observability: ['관측성', 'Observability', 'OTEL'],
  security: ['보안', 'Security', 'SEC'],
  ai: ['AI / GPU', 'AI / GPU', 'AI'],
  ecosystem: ['CNCF / 기타', 'CNCF / Other', 'CNCF']
}
const categories = {
  security: ['보안 관련', 'Security'],
  breaking: ['호환성·지원 변경', 'Compatibility / support'],
  release: ['릴리스', 'Release'],
  preview: ['프리릴리스', 'Preview'],
  feature: ['새 기능·개선', 'Features / improvements'],
  community: ['커뮤니티', 'Community'],
  guide: ['가이드·블로그', 'Guides / blogs']
}
const topicName = key => t(topics[key][0], topics[key][1])
const categoryName = key => t(categories[key][0], categories[key][1])
const count = (key, period) => heatmapCount(chartEntries.value, key, period)
const topicCount = key => topicEntries.value.filter(entry => entry.topic === key).length
const cellLabel = (key, period) => `${topicName(key)}, ${period}, ${count(key, period)} ${t('기록', 'records')}`
const sourceName = url => new URL(url).hostname.replace(/^www\./, '')
const docLabel = document => {
  const parts = document.split('/')
  return (parts.at(-1) === 'README.md' ? parts.at(-2) : parts.at(-1).replace(/^\d+-|\.md$/g, ''))
    .replace(/-/g, ' ')
}
const detail = entry => {
  const start = entry.summary.search(/[（(]/)
  return start < 0 ? '' : entry.summary.slice(start + 1).replace(/[)）](?:\s*반영)?$/, '')
}

function reset() {
  topic.value = ''
  category.value = ''
  week.value = ''
  query.value = ''
}
function selectCell(key, period) {
  if (topic.value === key && week.value === period) {
    topic.value = ''
    week.value = ''
  } else {
    topic.value = key
    week.value = period
  }
}
watch([topic, category, week, query, locale], () => { limit.value = 12 })
watch(locale, reset)
</script>

<template>
  <section class="news-dashboard" :aria-label="t('소식 대시보드', 'News dashboard')">
    <div class="news-intro">
      <div>
        <span class="news-eyebrow">CLOUD NATIVE PULSE</span>
        <h2>{{ t('변화를 한눈에', 'Changes at a glance') }}</h2>
        <p>{{ t('분야와 주차를 선택하고, 관련 문서까지 이어서 읽어보세요.', 'Choose a topic and week, then explore the related guides.') }}</p>
      </div>
      <div class="news-latest">
        <span class="news-status-dot" aria-hidden="true"></span>
        <span>{{ t('최신 기록', 'Latest recorded week') }}<strong>{{ weeks[0] }}</strong></span>
      </div>
    </div>

    <div class="news-stats" :aria-label="t('선택한 기록의 요약', 'Summary of selected records')">
      <div class="news-stat">
        <span>{{ t('소식 기록', 'News records') }}</span><strong>{{ stats.records }}</strong>
        <small>{{ active ? t('선택 조건에 해당하는 기록', 'Records matching your filters') : t('전체 갱신 로그 기준', 'Across the complete update log') }}</small>
      </div>
      <div class="news-stat news-stat-security">
        <span>{{ t('보안 관련 기록', 'Security records') }}</span><strong>{{ stats.security }}</strong>
        <small>{{ t('CVE·보안 패치 관련', 'CVE and security patch updates') }}</small>
      </div>
      <div class="news-stat">
        <span>{{ t('연결된 문서', 'Linked guides') }}</span><strong>{{ stats.documents }}</strong>
        <small>{{ t('중복 문서 제외', 'Distinct document paths') }}</small>
      </div>
      <div class="news-stat">
        <span>{{ t('관련 문서 없는 기록', 'Records without a guide') }}</span><strong>{{ stats.unmatched }}</strong>
        <small>{{ t('로그 당시 자동 매칭 결과', 'Automated match at logging time') }}</small>
      </div>
    </div>

    <section class="news-activity" :aria-labelledby="`news-activity-${locale}`">
      <div class="news-section-heading">
        <div>
          <h3 :id="`news-activity-${locale}`">{{ t('8주간의 기록', 'Eight weeks of updates') }}</h3>
          <p>{{ t('칸을 누르면 해당 분야·주차의 기록을 볼 수 있습니다.', 'Select a cell to browse that topic and week.') }}</p>
        </div>
        <span class="news-period-range">{{ chartWeeks[0] }} — {{ chartWeeks.at(-1) }}</span>
      </div>
      <div class="news-table-scroll" tabindex="0" role="region" :aria-label="t('분야별 주간 기록 표', 'Weekly records by topic')">
        <table class="news-heatmap">
          <caption class="news-sr-only">{{ t('마지막 기록 주차를 기준으로 최근 8주의 기록 수. 빈 칸은 기록 없음입니다.', 'Record counts for eight weeks ending at the latest logged week. Empty cells mean no recorded entry.') }}</caption>
          <thead>
            <tr>
              <th scope="col">{{ t('분야', 'Topic') }}</th>
              <th v-for="period in chartWeeks" :key="period" scope="col" :title="period">{{ period.slice(5) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="key in NEWS_TOPICS" :key="key">
              <th scope="row"><span class="news-topic-dot" :data-topic="key" aria-hidden="true"></span>{{ topicName(key) }}</th>
              <td v-for="period in chartWeeks" :key="period">
                <button
                  type="button" class="news-cell" :data-topic="key"
                  :data-level="Math.min(count(key, period), 3)"
                  :aria-label="cellLabel(key, period)" :title="cellLabel(key, period)"
                  :aria-pressed="topic === key && week === period"
                  :disabled="count(key, period) === 0"
                  @click="selectCell(key, period)"
                >{{ count(key, period) || '·' }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="news-activity-footer">
        <span>{{ t('기록 주차 기준 · 발표일과 다를 수 있습니다.', 'Logging weeks may differ from publication dates.') }}</span>
        <span class="news-legend">
          {{ t('기록 수', 'Records') }}
          <i data-level="0">·</i><i data-level="1">1</i><i data-level="2">2</i><i data-level="3">3+</i>
        </span>
      </div>
    </section>

    <div class="news-topics" role="group" :aria-label="t('분야 필터', 'Topic filters')">
      <button type="button" :aria-pressed="topic === ''" @click="topic = ''">{{ t('전체', 'All') }}<span>{{ topicEntries.length }}</span></button>
      <button v-for="key in NEWS_TOPICS" :key="key" type="button" :aria-pressed="topic === key" @click="topic = topic === key ? '' : key">
        <span class="news-topic-dot" :data-topic="key" aria-hidden="true"></span>{{ topicName(key) }}<span>{{ topicCount(key) }}</span>
      </button>
    </div>

    <form class="news-toolbar" role="search" @submit.prevent>
      <label class="news-search">
        <span class="news-sr-only">{{ t('소식 검색', 'Search news') }}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>
        <input v-model="query" type="search" :placeholder="t('기능, 키워드, 버전 검색', 'Search features, keywords, versions')" />
      </label>
      <label class="news-select">
        <span>{{ t('변경 유형', 'Change type') }}</span>
        <select v-model="category">
          <option value="">{{ t('모든 변경', 'All changes') }}</option>
          <option v-for="key in NEWS_CATEGORIES" :key="key" :value="key">{{ categoryName(key) }}</option>
        </select>
      </label>
      <label class="news-select">
        <span>{{ t('기록 주차', 'Logging week') }}</span>
        <select v-model="week">
          <option value="">{{ t('전체 기간', 'All weeks') }}</option>
          <option v-for="period in weeks" :key="period" :value="period">{{ period }}</option>
        </select>
      </label>
    </form>

    <div class="news-results-heading">
      <p role="status" aria-live="polite" aria-atomic="true">
        <strong>{{ filtered.length }}</strong> {{ t('개의 기록', 'records') }}
        <span v-if="topic"> · {{ topicName(topic) }}</span>
        <span v-if="week"> · {{ week }}</span>
      </p>
      <button v-if="active" type="button" class="news-reset" @click="reset">{{ t('필터 초기화', 'Clear filters') }} <span aria-hidden="true">↺</span></button>
    </div>
    <div v-if="!filtered.length" class="news-empty">
      <strong>{{ t('조건에 맞는 기록이 없습니다.', 'No records match these filters.') }}</strong>
      <p>{{ t('다른 분야나 주차를 선택하거나 검색어를 바꿔보세요.', 'Try another topic, week, or search term.') }}</p>
      <button type="button" class="news-load-more" @click="reset">{{ t('전체 기록 보기', 'Show all records') }}</button>
    </div>
    <div v-else class="news-cards">
      <article v-for="entry in filtered.slice(0, limit)" :key="entry.id" class="news-card">
        <div class="news-card-meta">
          <span class="news-product" :data-topic="entry.topic">{{ topics[entry.topic][2] }}</span>
          <span>{{ topicName(entry.topic) }}</span>
          <span class="news-card-period">{{ entry.period }}</span>
        </div>
        <h3>{{ entry.title }}</h3>
        <p v-if="detail(entry)" class="news-card-detail">{{ detail(entry) }}</p>
        <div class="news-card-badges">
          <span class="news-category" :data-category="entry.category">{{ categoryName(entry.category) }}</span>
          <span v-if="entry.documents.length === 0" class="news-unmatched">{{ t('관련 문서 없음', 'No matched guide') }}</span>
        </div>
        <div class="news-card-links">
          <a v-for="document in entry.documents" :key="document" :href="newsDocumentUrl(site.base, locale, document)" :title="document">
            {{ t('문서', 'Guide') }} · {{ docLabel(document) }} <span aria-hidden="true">↗</span>
          </a>
          <a v-for="source in entry.sources" :key="source" :href="source" target="_blank" rel="noopener noreferrer">
            {{ t('원문', 'Source') }} · {{ sourceName(source) }} <span aria-hidden="true">↗</span>
          </a>
          <span v-if="entry.sources.length === 0" class="news-source-missing">{{ t('원문 링크가 없는 과거 기록', 'Historical record without a source link') }}</span>
        </div>
      </article>
    </div>
    <button v-if="filtered.length > limit" type="button" class="news-load-more" @click="limit += 12">
      {{ t('기록 더 보기', 'Show more records') }} <span>({{ Math.min(12, filtered.length - limit) }})</span> <span aria-hidden="true">↓</span>
    </button>
    <p class="news-data-note">{{ t('로그 기록 수를 집계합니다. 과거에는 한 발표가 문서별로 여러 줄 기록될 수 있어 원문 기사 수와 다릅니다. 유형은 기록의 키워드 기준입니다.', 'Counts reflect log entries. Older announcements may occupy several document-specific entries, so totals differ from distinct source articles. Types are classified by keywords in each record.') }}</p>
  </section>
</template>

<style scoped>
.news-dashboard {
  --news-border: var(--vp-c-divider);
  --news-surface: var(--vp-c-bg);
  --news-wash: var(--vp-c-bg-soft);
  --news-muted: var(--vp-c-text-2);
  margin: 32px 0 40px;
  color: var(--vp-c-text-1);
  font-size: 14px;
}
.news-dashboard h2, .news-dashboard h3, .news-dashboard p { margin: 0; border: 0; padding: 0; }
.news-intro { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 24px; }
.news-eyebrow { display: block; color: var(--vp-c-brand-1); font: 600 10px/1.4 var(--vp-font-family-mono); letter-spacing: .16em; margin-bottom: 10px; }
.news-intro h2 { font-size: 28px; font-weight: 750; letter-spacing: -.04em; line-height: 1.3; }
.news-intro p { margin-top: 8px; font-size: 13px; color: var(--news-muted); }
.news-latest { display: flex; align-items: center; gap: 9px; flex-shrink: 0; font-size: 11px; color: var(--news-muted); padding: 11px 14px; background: var(--news-wash); border: 1px solid var(--news-border); border-radius: 10px; line-height: 1.5; }
.news-latest strong { display: block; font: 600 13px/1.7 var(--vp-font-family-mono); color: var(--vp-c-text-1); }
.news-status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--vp-c-brand-1); }
.news-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 24px; }
.news-stat { display: flex; flex-direction: column; padding: 17px 18px; border: 1px solid var(--news-border); border-radius: 12px; background: var(--news-surface); }
.news-stat > span { font-size: 12px; color: var(--news-muted); }
.news-stat strong { margin: 9px 0 8px; font: 650 32px/1 var(--vp-font-family-mono); letter-spacing: -.06em; }
.news-stat small { font-size: 10px; line-height: 1.6; color: var(--news-muted); }
.news-stat-security strong { color: var(--vp-c-warning-1); }
.news-activity { border: 1px solid var(--news-border); border-radius: 14px; padding: 20px; background: var(--news-surface); margin-bottom: 24px; }
.news-section-heading { display: flex; gap: 16px; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.news-section-heading h3 { font-size: 16px; font-weight: 650; line-height: 1.5; }
.news-section-heading p { margin-top: 4px; color: var(--news-muted); font-size: 11px; }
.news-period-range { font: 10px/2 var(--vp-font-family-mono); color: var(--news-muted); white-space: nowrap; }
.news-table-scroll { overflow-x: auto; border-radius: 5px; }
.news-dashboard .news-heatmap { display: table; width: 100%; min-width: 490px; border-collapse: separate; border-spacing: 5px 4px; margin: 0; font-size: 12px; overflow: visible; }
.news-dashboard .news-heatmap tr { border: 0; background: transparent; }
.news-dashboard .news-heatmap th, .news-dashboard .news-heatmap td { border: 0; padding: 0; background: transparent; }
.news-heatmap thead th { text-align: center; font: 11px/2 var(--vp-font-family-mono); color: var(--news-muted); }
.news-heatmap thead th:first-child, .news-heatmap tbody th { text-align: left; font-family: var(--vp-font-family-base); white-space: nowrap; }
.news-heatmap tbody th { font-weight: 500; width: 138px; padding-right: 12px !important; }
.news-topic-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--topic-color); margin-right: 8px; flex-shrink: 0; }
[data-topic="kubernetes"] { --topic-color: #326ce5; }
[data-topic="eks"] { --topic-color: #c87516; }
[data-topic="networking"] { --topic-color: #128675; }
[data-topic="mesh"] { --topic-color: #8663ce; }
[data-topic="gitops"] { --topic-color: #cf6656; }
[data-topic="autoscaling"] { --topic-color: #a47827; }
[data-topic="observability"] { --topic-color: #ae5e91; }
[data-topic="security"] { --topic-color: #c34d5c; }
[data-topic="ai"] { --topic-color: #5973c2; }
[data-topic="ecosystem"] { --topic-color: #668493; }
.news-cell { display: block; width: 100%; min-width: 32px; height: 29px; border-radius: 5px; font: 600 12px/1 var(--vp-font-family-mono); border: 1px solid transparent; cursor: pointer; transition: background .15s, outline .15s; }
.news-cell[data-level="0"] { background: var(--news-wash); color: var(--news-muted); cursor: default; }
.news-cell[data-level="1"] { background: color-mix(in srgb, var(--topic-color) 15%, var(--news-surface)); color: var(--vp-c-text-1); }
.news-cell[data-level="2"] { background: color-mix(in srgb, var(--topic-color) 30%, var(--news-surface)); color: var(--vp-c-text-1); }
.news-cell[data-level="3"] { background: var(--topic-color); color: #fff; }
.news-cell:not(:disabled):hover { outline: 1px solid var(--topic-color); outline-offset: 2px; }
.news-cell[aria-pressed="true"] { outline: 2px solid var(--vp-c-text-1); outline-offset: 2px; }
.news-activity-footer { display: flex; gap: 12px; align-items: center; justify-content: space-between; margin-top: 14px; color: var(--news-muted); font-size: 10px; }
.news-legend { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
.news-legend i { font: 10px/18px var(--vp-font-family-mono); font-style: normal; text-align: center; width: 21px; height: 18px; border-radius: 3px; background: var(--news-wash); }
.news-legend i[data-level="1"] { background: var(--vp-c-brand-soft); }
.news-legend i[data-level="2"] { background: color-mix(in srgb, var(--vp-c-brand-1) 30%, var(--news-surface)); color: var(--vp-c-text-1); }
.news-legend i[data-level="3"] { background: var(--vp-c-brand-1); color: var(--vp-c-bg); }
.news-topics { display: flex; gap: 7px; flex-wrap: wrap; padding-bottom: 18px; }
.news-topics button { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px solid var(--news-border); border-radius: 7px; font-size: 11px; background: var(--news-surface); color: var(--news-muted); cursor: pointer; line-height: 1.5; }
.news-topics .news-topic-dot { margin-right: 0; width: 6px; height: 6px; }
.news-topics button > span:last-child:not(.news-topic-dot) { font: 10px/1 var(--vp-font-family-mono); color: var(--news-muted); }
.news-topics button[aria-pressed="true"] { border-color: var(--vp-c-brand-1); color: var(--vp-c-brand-1); background: var(--vp-c-brand-soft); }
.news-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) 180px 138px; gap: 10px; padding: 16px; border: 1px solid var(--news-border); background: var(--news-wash); border-radius: 10px; }
.news-search { display: flex; align-items: center; gap: 10px; padding: 0 12px; background: var(--news-surface); border: 1px solid var(--news-border); border-radius: 6px; align-self: end; min-height: 38px; }
.news-search svg { width: 17px; height: 17px; flex-shrink: 0; color: var(--news-muted); }
.news-search input { width: 100%; min-width: 0; font: inherit; font-size: 12px; background: transparent; padding: 8px 0; }
.news-search input::placeholder { color: var(--news-muted); }
.news-select { display: flex; flex-direction: column; gap: 4px; font-size: 10px; color: var(--news-muted); }
.news-select select { width: 100%; min-height: 38px; border: 1px solid var(--news-border); border-radius: 6px; background: var(--news-surface); color: var(--vp-c-text-1); font: 12px/1.5 var(--vp-font-family-base); padding: 7px 24px 7px 10px; appearance: auto; }
.news-results-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 20px 0 12px; font-size: 12px; color: var(--news-muted); }
.news-results-heading strong { font-family: var(--vp-font-family-mono); font-size: 15px; color: var(--vp-c-text-1); }
.news-reset { color: var(--vp-c-brand-1); cursor: pointer; font-size: 11px; }
.news-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.news-card { display: flex; flex-direction: column; padding: 20px; border: 1px solid var(--news-border); border-radius: 12px; background: var(--news-surface); min-width: 0; }
.news-card-meta { display: flex; align-items: center; gap: 8px; color: var(--news-muted); font-size: 10px; margin-bottom: 14px; }
.news-product { font: 700 9px/24px var(--vp-font-family-mono); background: color-mix(in srgb, var(--topic-color) 14%, var(--news-surface)); color: var(--vp-c-text-1); padding: 0 6px; border-radius: 5px; letter-spacing: -.03em; }
.news-card-period { margin-left: auto; white-space: nowrap; font-family: var(--vp-font-family-mono); font-size: 10px; }
.news-card h3 { font-size: 15px; font-weight: 650; line-height: 1.65; letter-spacing: -.015em; overflow-wrap: anywhere; }
.news-card .news-card-detail { font-size: 12px; line-height: 1.8; color: var(--news-muted); margin-top: 10px; overflow-wrap: anywhere; }
.news-card-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 16px; padding-bottom: 14px; }
.news-category, .news-unmatched { display: inline-block; font-size: 10px; line-height: 1.5; padding: 3px 7px; border-radius: 4px; background: var(--news-wash); color: var(--news-muted); }
.news-category[data-category="security"], .news-category[data-category="breaking"] { background: var(--vp-c-warning-soft); color: var(--vp-c-warning-1); }
.news-category[data-category="release"], .news-category[data-category="feature"] { background: var(--vp-c-brand-soft); color: var(--vp-c-brand-1); }
.news-card-links { display: flex; flex-direction: column; gap: 6px; border-top: 1px solid var(--news-border); padding-top: 12px; margin-top: auto; }
.news-card-links a { font-size: 10px; text-decoration: none; line-height: 1.6; font-weight: 500; overflow-wrap: anywhere; }
.news-card-links a:hover { text-decoration: underline; }
.news-source-missing { color: var(--news-muted); font-size: 10px; }
.news-load-more { display: block; padding: 9px 18px; border: 1px solid var(--news-border); border-radius: 7px; background: var(--news-surface); color: var(--vp-c-text-1); font-size: 12px; margin: 20px auto 0; cursor: pointer; }
.news-load-more:hover { border-color: var(--vp-c-brand-1); }
.news-load-more span { margin-left: 5px; }
.news-dashboard .news-data-note { font-size: 10px; line-height: 1.8; color: var(--news-muted); margin-top: 20px; }
.news-empty { text-align: center; padding: 40px 16px; border: 1px dashed var(--news-border); border-radius: 12px; }
.news-empty strong { font-size: 14px; }
.news-empty p { margin-top: 8px; font-size: 12px; color: var(--news-muted); }
.news-dashboard button:focus-visible, .news-dashboard select:focus-visible, .news-dashboard input:focus-visible, .news-table-scroll:focus-visible, .news-card-links a:focus-visible { outline: 2px solid var(--vp-c-brand-1); outline-offset: 3px; }
.news-sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0; }
@media (max-width: 960px) {
  .news-stats { gap: 8px; }
  .news-stat { padding: 14px 12px; }
  .news-section-heading { flex-direction: column; gap: 4px; }
  .news-toolbar { grid-template-columns: minmax(0, 1fr) 150px 122px; padding: 12px; }
}
@media (max-width: 680px) {
  .news-intro { align-items: flex-start; gap: 12px; }
  .news-intro h2 { font-size: 24px; }
  .news-intro p { font-size: 12px; }
  .news-latest { padding: 8px 10px; font-size: 9px; }
  .news-latest strong { font-size: 11px; }
  .news-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .news-stat strong { font-size: 28px; }
  .news-activity { padding: 15px 12px; }
  .news-activity-footer { flex-direction: column; align-items: flex-start; gap: 8px; }
  .news-toolbar { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .news-search { grid-column: 1 / -1; }
  .news-cards { grid-template-columns: minmax(0, 1fr); }
  .news-card { padding: 18px; }
}
@media (prefers-reduced-motion: reduce) { .news-cell { transition: none; } }
</style>
