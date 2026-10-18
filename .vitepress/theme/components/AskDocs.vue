<script lang="ts">
import { ref } from 'vue'

type Source = { title: string; heading: string; url: string }
type Turn = { question: string; html: string; sources: Source[] }

// Module scope, so the conversation survives page changes inside the site (for example after
// opening one of the sources). A full reload starts a new conversation.
const turns = ref<Turn[]>([])
const conversationId = ref<string | null>(null)
</script>

<script setup lang="ts">
import { computed, nextTick } from 'vue'
import { useData } from 'vitepress'
import MarkdownIt from 'markdown-it'

// Question box for the docs. Calls the same-origin API (CloudFront -> internal ALB -> Lambda); the API
// keeps earlier turns under conversationId so follow-up questions have context.
// Answers are Markdown from the model: raw HTML is disabled (escaped), and markdown-it rejects
// javascript:/vbscript:/file:/data: links by default. Images are turned off.
const md = new MarkdownIt({ html: false, linkify: false, typographer: false }).disable(['image'])
const { lang } = useData()
const locale = computed(() => (lang.value.startsWith('ko') ? 'ko' : 'en'))
const copy = computed(() =>
  locale.value === 'ko'
    ? { title: '문서에 질문하기', placeholder: '궁금한 내용을 입력하세요 (500자 이내)', followUp: '이어서 질문하세요', hint: 'Enter로 보내고 Shift+Enter로 줄을 바꿉니다.', ask: '질문', reset: '새 대화', busy: '답변을 찾는 중…', sources: '참고 문서', error: '답변을 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.' }
    : { title: 'Ask the docs', placeholder: 'Type your question (500 characters max)', followUp: 'Ask a follow-up question', hint: 'Enter sends, Shift+Enter adds a line.', ask: 'Ask', reset: 'New conversation', busy: 'Searching the docs…', sources: 'Sources', error: 'Could not get an answer. Please try again shortly.' }
)

const question = ref('')
const pending = ref('')
const status = ref<'idle' | 'busy' | 'error'>('idle')
const input = ref<HTMLTextAreaElement | null>(null)
const thread = ref<HTMLElement | null>(null)

// Grow with the text up to the CSS max-height, then scroll inside.
function resize() {
  const el = input.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight + el.offsetHeight - el.clientHeight}px`
}

// Enter sends and Shift+Enter adds a line. An Enter that confirms Korean or Japanese IME
// composition is not a send (isComposing, or keyCode 229 in Safari).
function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Enter' || e.shiftKey || e.isComposing || e.keyCode === 229) return
  e.preventDefault()
  ask()
}

async function ask() {
  const q = question.value.trim()
  if (!q || status.value === 'busy') return
  status.value = 'busy'
  pending.value = q
  question.value = ''
  await nextTick()
  resize()
  try {
    const res = await fetch('/kubernetes-docs/api/ask', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ question: q.slice(0, 500), locale: locale.value, conversationId: conversationId.value ?? undefined }),
    })
    if (!res.ok) throw new Error(String(res.status))
    const data = await res.json()
    conversationId.value = data.conversationId ?? null
    turns.value.push({ question: q, html: md.render(data.answer ?? ''), sources: data.sources ?? [] })
    status.value = 'idle'
    pending.value = ''
    await nextTick()
    thread.value?.lastElementChild?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  } catch {
    question.value = q // keep the question so it can be sent again
    pending.value = ''
    status.value = 'error'
    await nextTick()
    resize()
  }
}

function reset() {
  turns.value = []
  conversationId.value = null
  status.value = 'idle'
  input.value?.focus()
}
</script>

<template>
  <section class="ask-docs" aria-labelledby="ask-docs-title">
    <div class="ask-head">
      <h2 id="ask-docs-title">{{ copy.title }}</h2>
      <button v-if="turns.length" type="button" class="ask-reset" :disabled="status === 'busy'" @click="reset">{{ copy.reset }}</button>
    </div>
    <div v-if="turns.length || pending" ref="thread" class="ask-thread" role="log" aria-live="polite">
      <article v-for="(t, i) in turns" :key="i" class="ask-turn">
        <p class="ask-question">{{ t.question }}</p>
        <!-- eslint-disable-next-line vue/no-v-html -- markdown-it with html disabled, see above -->
        <div class="ask-answer-text vp-doc" v-html="t.html" />
        <div v-if="t.sources.length" class="ask-sources">
          <strong>{{ copy.sources }}</strong>
          <!-- Numbered so they match the [n] citations in the answer. -->
          <ol>
            <li v-for="s in t.sources" :key="s.url"><a :href="s.url">{{ s.title }}{{ s.heading && s.heading !== s.title ? ' · ' + s.heading : '' }}</a></li>
          </ol>
        </div>
      </article>
      <article v-if="pending" class="ask-turn">
        <p class="ask-question">{{ pending }}</p>
        <p role="status">{{ copy.busy }}</p>
      </article>
    </div>
    <p v-if="status === 'error'" role="alert">{{ copy.error }}</p>
    <form @submit.prevent="ask">
      <textarea
        ref="input"
        v-model="question"
        rows="2"
        maxlength="500"
        :placeholder="turns.length ? copy.followUp : copy.placeholder"
        :aria-label="copy.title"
        aria-describedby="ask-docs-hint"
        @keydown="onKeydown"
        @input="resize"
      />
      <button type="submit" :disabled="status === 'busy' || !question.trim()">{{ copy.ask }}</button>
    </form>
    <p id="ask-docs-hint" class="ask-hint">{{ copy.hint }}</p>
  </section>
</template>

<style scoped>
.ask-docs { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--vp-c-divider); }
.ask-head { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.75rem; }
.ask-docs h2 { font-size: 1.25rem; margin: 0; border: 0; padding: 0; }
.ask-reset { font-size: 0.875rem; padding: 0.25rem 0.75rem; border-radius: 6px; border: 1px solid var(--vp-c-divider); background: transparent; color: var(--vp-c-text-2); cursor: pointer; }
.ask-reset:disabled { opacity: 0.5; cursor: not-allowed; }
.ask-thread { display: flex; flex-direction: column; gap: 1.25rem; margin-bottom: 1rem; }
.ask-turn { scroll-margin-top: calc(var(--vp-nav-height) + 1rem); }
.ask-question { margin: 0 0 0.5rem; padding: 0.5rem 0.75rem; border-radius: 6px; background: var(--vp-c-bg-soft); white-space: pre-wrap; overflow-wrap: anywhere; }
.ask-answer-text { line-height: 1.7; }
/* Outside .vp-doc, VitePress resets list markers and link colors. */
.ask-sources ol { list-style: decimal; padding-left: 1.5rem; margin: 0.25rem 0 0; }
.ask-sources a { color: var(--vp-c-brand-1); text-decoration: underline; text-underline-offset: 2px; }
.ask-docs form { display: flex; gap: 0.5rem; align-items: flex-end; }
.ask-docs textarea { flex: 1; font: inherit; padding: 0.5rem 0.75rem; border: 1px solid var(--vp-c-divider); border-radius: 6px; background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); resize: none; max-height: 240px; overflow-y: auto; }
.ask-docs button[type='submit'] { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid var(--vp-c-brand-1); background: var(--vp-c-brand-1); color: #fff; cursor: pointer; }
.ask-docs button[type='submit']:disabled { opacity: 0.5; cursor: not-allowed; }
.ask-hint { margin: 0.375rem 0 0; font-size: 0.8125rem; color: var(--vp-c-text-3); }
</style>
