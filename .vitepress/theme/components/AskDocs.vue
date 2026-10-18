<script lang="ts">
import { ref } from 'vue'

type Source = { title: string; heading: string; url: string }
// waiting: no answer text yet; streaming: text is arriving; stopped: the reader pressed Stop;
// failed: the stream broke after some text arrived.
type Turn = { question: string; text: string; html: string; sources: Source[]; state: 'waiting' | 'streaming' | 'done' | 'stopped' | 'failed' }

// Module scope, so the conversation, and an answer that is still streaming, survive page changes
// inside the site (for example after opening one of the sources). A full reload starts over.
const turns = ref<Turn[]>([])
const conversationId = ref<string | null>(null)
const status = ref<'idle' | 'busy' | 'error'>('idle')
let controller: AbortController | null = null
</script>

<script setup lang="ts">
import { computed, nextTick } from 'vue'
import { useData } from 'vitepress'
import MarkdownIt from 'markdown-it'
import { readEvents } from '../ask-stream.mjs'

// Question box for the docs. Calls the same-origin API (CloudFront -> internal ALB -> private API
// Gateway -> Lambda), which streams the answer as server-sent events while Bedrock writes it; the API
// keeps earlier turns under conversationId so follow-up questions have context.
// Answers are Markdown from the model: raw HTML is disabled (escaped), and markdown-it rejects
// javascript:/vbscript:/file:/data: links by default. Images are turned off.
const md = new MarkdownIt({ html: false, linkify: false, typographer: false }).disable(['image'])
const COPY = {
  ko: { title: '문서에 질문하기', placeholder: '궁금한 내용을 입력하세요 (500자 이내)', followUp: '이어서 질문하세요', hint: 'Enter로 보내고 Shift+Enter로 줄을 바꿉니다.', ask: '질문', stop: '중지', reset: '새 대화', busy: '답변을 찾는 중…', sources: '참고 문서', stopped: '답변을 중지했습니다.', failed: '답변이 중간에 끊겼습니다. 다시 질문해 주세요.', error: '답변을 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.' },
  en: { title: 'Ask the docs', placeholder: 'Type your question (500 characters max)', followUp: 'Ask a follow-up question', hint: 'Enter sends, Shift+Enter adds a line.', ask: 'Ask', stop: 'Stop', reset: 'New conversation', busy: 'Searching the docs…', sources: 'Sources', stopped: 'Answer stopped.', failed: 'The answer was cut off. Please ask again.', error: 'Could not get an answer. Please try again shortly.' },
  cn: { title: '向文档提问', placeholder: '请输入您的问题（500 字以内）', followUp: '继续提问', hint: '按 Enter 发送，按 Shift+Enter 换行。', ask: '提问', stop: '停止', reset: '新对话', busy: '正在查找答案…', sources: '参考文档', stopped: '已停止回答。', failed: '回答中断了，请重新提问。', error: '无法获取答案，请稍后重试。' },
  jp: { title: 'ドキュメントに質問する', placeholder: '質問を入力してください（500 文字以内）', followUp: '続けて質問してください', hint: 'Enter で送信、Shift+Enter で改行します。', ask: '質問', stop: '停止', reset: '新しい会話', busy: '回答を探しています…', sources: '参考ドキュメント', stopped: '回答を停止しました。', failed: '回答が途中で途切れました。もう一度質問してください。', error: '回答を取得できませんでした。しばらくしてからもう一度お試しください。' },
  es: { title: 'Pregunta a la documentación', placeholder: 'Escribe tu pregunta (máximo 500 caracteres)', followUp: 'Haz otra pregunta', hint: 'Enter envía, Shift+Enter añade una línea.', ask: 'Preguntar', stop: 'Detener', reset: 'Nueva conversación', busy: 'Buscando en la documentación…', sources: 'Fuentes', stopped: 'Respuesta detenida.', failed: 'La respuesta se interrumpió. Vuelve a preguntar.', error: 'No se pudo obtener una respuesta. Inténtalo de nuevo en unos momentos.' },
} as const
// Page lang (ko-KR, en-US, zh-CN, ja-JP, es-ES) -> the API's locale keys, which follow the folder names.
const LOCALE_BY_LANG: Record<string, keyof typeof COPY> = { ko: 'ko', en: 'en', zh: 'cn', ja: 'jp', es: 'es' }
const { lang } = useData()
const locale = computed(() => LOCALE_BY_LANG[lang.value.slice(0, 2)] ?? 'en')
const copy = computed(() => COPY[locale.value])

const question = ref('')
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

// Re-render the Markdown at most once per frame while text streams in.
let frame = 0
function scheduleRender(turn: Turn) {
  if (frame) return
  frame = requestAnimationFrame(() => {
    frame = 0
    turn.html = md.render(turn.text)
  })
}

async function ask() {
  const q = question.value.trim()
  if (!q || status.value === 'busy') return
  status.value = 'busy'
  question.value = ''
  turns.value.push({ question: q, text: '', html: '', sources: [], state: 'waiting' })
  const turn = turns.value[turns.value.length - 1] // the reactive copy
  await nextTick()
  resize()
  thread.value?.lastElementChild?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  const ctrl = new AbortController()
  controller = ctrl
  let sources: Source[] = []
  try {
    const res = await fetch('/kubernetes-docs/api/ask', {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
      body: JSON.stringify({ question: q.slice(0, 500), locale: locale.value, conversationId: conversationId.value ?? undefined }),
      signal: ctrl.signal,
    })
    if (!res.ok || !res.body) throw new Error(String(res.status))
    if (!res.headers.get('content-type')?.includes('text/event-stream')) {
      // A buffered JSON answer, from an API version that does not stream.
      const data = await res.json()
      conversationId.value = data.conversationId ?? null
      sources = data.sources ?? []
      turn.text = data.answer ?? ''
      turn.state = 'done'
    } else {
      for await (const { event, data } of readEvents(res.body)) {
        if (event === 'meta') {
          conversationId.value = data.conversationId ?? null
          sources = data.sources ?? []
        } else if (event === 'delta') {
          turn.text += data.text
          turn.state = 'streaming'
          scheduleRender(turn)
        } else if (event === 'done') {
          turn.state = 'done'
        } else if (event === 'error') {
          break
        }
      }
    }
    if (turn.state !== 'done') throw new Error('stream ended before the answer finished')
  } catch {
    if (ctrl.signal.aborted) {
      turn.state = 'stopped'
    } else if (!turn.text) {
      turns.value.pop()
      question.value = q // keep the question so it can be sent again
      status.value = 'error'
    } else {
      turn.state = 'failed'
    }
  } finally {
    cancelAnimationFrame(frame)
    frame = 0
    turn.html = md.render(turn.text)
    if (turn.state !== 'waiting') turn.sources = sources
    if (status.value === 'busy') status.value = 'idle'
    if (controller === ctrl) controller = null
    await nextTick()
    resize()
  }
}

function stop() {
  controller?.abort()
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
    <!-- aria-busy while streaming, so screen readers read the answer once instead of every update. -->
    <div v-if="turns.length" ref="thread" class="ask-thread" role="log" aria-live="polite" :aria-busy="status === 'busy'">
      <article v-for="(t, i) in turns" :key="i" class="ask-turn">
        <p class="ask-question">{{ t.question }}</p>
        <p v-if="t.state === 'waiting'" role="status" class="ask-waiting">{{ copy.busy }}</p>
        <!-- eslint-disable-next-line vue/no-v-html -- markdown-it with html disabled, see above -->
        <div v-else class="ask-answer-text vp-doc" :class="{ 'is-streaming': t.state === 'streaming' }" v-html="t.html" />
        <p v-if="t.state === 'stopped'" class="ask-note">{{ copy.stopped }}</p>
        <p v-else-if="t.state === 'failed'" class="ask-note" role="alert">{{ copy.failed }}</p>
        <div v-if="t.sources.length" class="ask-sources">
          <strong>{{ copy.sources }}</strong>
          <!-- Numbered so they match the [n] citations in the answer. -->
          <ol>
            <!-- Keyed by position: on cn/jp/es pages two sources can link the same translated page. -->
            <li v-for="(s, n) in t.sources" :key="n"><a :href="s.url">{{ s.title }}{{ s.heading && s.heading !== s.title ? ' · ' + s.heading : '' }}</a></li>
          </ol>
        </div>
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
      <button v-if="status === 'busy'" type="button" class="ask-stop" @click="stop">{{ copy.stop }}</button>
      <button v-else type="submit" :disabled="!question.trim()">{{ copy.ask }}</button>
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
.ask-waiting { color: var(--vp-c-text-2); }
/* A blinking caret after the text while the answer streams in. */
.ask-answer-text.is-streaming > :deep(:last-child)::after { content: '▍'; margin-left: 0.125rem; color: var(--vp-c-brand-1); animation: ask-caret 1s steps(1) infinite; }
@keyframes ask-caret { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .ask-answer-text.is-streaming > :deep(:last-child)::after { animation: none; } }
.ask-note { margin: 0.25rem 0 0; font-size: 0.875rem; color: var(--vp-c-text-2); }
/* Outside .vp-doc, VitePress resets list markers and link colors. */
.ask-sources ol { list-style: decimal; padding-left: 1.5rem; margin: 0.25rem 0 0; }
.ask-sources a { color: var(--vp-c-brand-1); text-decoration: underline; text-underline-offset: 2px; }
.ask-docs form { display: flex; gap: 0.5rem; align-items: flex-end; }
.ask-docs textarea { flex: 1; font: inherit; padding: 0.5rem 0.75rem; border: 1px solid var(--vp-c-divider); border-radius: 6px; background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); resize: none; max-height: 240px; overflow-y: auto; }
.ask-docs button[type='submit'] { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid var(--vp-c-brand-1); background: var(--vp-c-brand-1); color: #fff; cursor: pointer; }
.ask-docs button[type='submit']:disabled { opacity: 0.5; cursor: not-allowed; }
.ask-stop { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); cursor: pointer; }
.ask-hint { margin: 0.375rem 0 0; font-size: 0.8125rem; color: var(--vp-c-text-3); }
</style>
