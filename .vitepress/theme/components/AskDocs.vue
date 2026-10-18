<script setup lang="ts">
import { computed, ref } from 'vue'
import { useData } from 'vitepress'

// Question box for the docs. Calls the same-origin API (CloudFront -> internal ALB -> Lambda).
const { lang } = useData()
const locale = computed(() => (lang.value.startsWith('ko') ? 'ko' : 'en'))
const copy = computed(() =>
  locale.value === 'ko'
    ? { title: '문서에 질문하기', placeholder: '궁금한 내용을 입력하세요 (500자 이내)', ask: '질문', busy: '답변을 찾는 중…', sources: '참고 문서', error: '답변을 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.' }
    : { title: 'Ask the docs', placeholder: 'Type your question (500 characters max)', ask: 'Ask', busy: 'Searching the docs…', sources: 'Sources', error: 'Could not get an answer. Please try again shortly.' }
)

const question = ref('')
const answer = ref('')
const sources = ref<{ title: string; heading: string; url: string }[]>([])
const status = ref<'idle' | 'busy' | 'error'>('idle')

async function ask() {
  const q = question.value.trim()
  if (!q || status.value === 'busy') return
  status.value = 'busy'
  answer.value = ''
  sources.value = []
  try {
    const res = await fetch('/kubernetes-docs/api/ask', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ question: q.slice(0, 500), locale: locale.value }),
    })
    if (!res.ok) throw new Error(String(res.status))
    const data = await res.json()
    answer.value = data.answer ?? ''
    sources.value = data.sources ?? []
    status.value = 'idle'
  } catch {
    status.value = 'error'
  }
}
</script>

<template>
  <section class="ask-docs" aria-labelledby="ask-docs-title">
    <h2 id="ask-docs-title">{{ copy.title }}</h2>
    <form @submit.prevent="ask">
      <textarea v-model="question" rows="2" maxlength="500" :placeholder="copy.placeholder" :aria-label="copy.title" />
      <button type="submit" :disabled="status === 'busy' || !question.trim()">{{ copy.ask }}</button>
    </form>
    <p v-if="status === 'busy'" role="status">{{ copy.busy }}</p>
    <p v-if="status === 'error'" role="alert">{{ copy.error }}</p>
    <div v-if="answer" class="ask-answer">
      <p class="ask-answer-text">{{ answer }}</p>
      <div v-if="sources.length">
        <strong>{{ copy.sources }}</strong>
        <ul>
          <li v-for="s in sources" :key="s.url"><a :href="s.url">{{ s.title }}{{ s.heading && s.heading !== s.title ? ' · ' + s.heading : '' }}</a></li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ask-docs { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--vp-c-divider); }
.ask-docs h2 { font-size: 1.25rem; margin: 0 0 0.75rem; border: 0; }
.ask-docs form { display: flex; gap: 0.5rem; align-items: flex-start; }
.ask-docs textarea { flex: 1; font: inherit; padding: 0.5rem 0.75rem; border: 1px solid var(--vp-c-divider); border-radius: 6px; background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); resize: vertical; }
.ask-docs button { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid var(--vp-c-brand-1); background: var(--vp-c-brand-1); color: #fff; cursor: pointer; }
.ask-docs button:disabled { opacity: 0.5; cursor: not-allowed; }
.ask-answer { margin-top: 1rem; }
.ask-answer-text { white-space: pre-wrap; line-height: 1.7; }
.ask-answer ul { padding-left: 1.25rem; }
</style>
