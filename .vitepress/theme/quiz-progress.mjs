const STORAGE_PREFIX = 'vitepress-quiz-review:'

export function quizProgressKey(routePath) {
  const normalizedPath = routePath.replace(/\/+$/, '') || '/'
  return `${STORAGE_PREFIX}${normalizedPath}`
}

export function readReviewedAnswers(storage, key, total) {
  try {
    const parsed = JSON.parse(storage.getItem(key) || '[]')
    if (!Array.isArray(parsed)) return new Set()

    return new Set(
      parsed
        .filter((value) => Number.isInteger(value) && value >= 0 && value < total)
        .sort((left, right) => left - right)
    )
  } catch {
    return new Set()
  }
}

export function writeReviewedAnswers(storage, key, reviewedAnswers) {
  const values = [...reviewedAnswers].sort((left, right) => left - right)
  storage.setItem(key, JSON.stringify(values))
}

export function progressCopy(routePath, reviewed, total) {
  const isEnglish = routePath.startsWith('/en/')
  return isEnglish
    ? { label: 'Review progress', value: `${reviewed}/${total}`, reset: 'Reset progress' }
    : { label: '복습 진행', value: `${reviewed}/${total}`, reset: '진도 초기화' }
}

export function initQuizProgress(documentRoot, routePath, storage = window.localStorage) {
  if (!routePath.includes('/quizzes/')) return () => {}

  const content = documentRoot.querySelector('.vp-doc')
  if (!content) return () => {}

  const answers = [...content.querySelectorAll('details')]
  if (answers.length === 0) return () => {}

  content.querySelector('[data-quiz-progress]')?.remove()

  const document = content.ownerDocument
  const key = quizProgressKey(routePath)
  const reviewedAnswers = readReviewedAnswers(storage, key, answers.length)
  const panel = document.createElement('section')
  const heading = document.createElement('div')
  const label = document.createElement('span')
  const value = document.createElement('strong')
  const progress = document.createElement('div')
  const progressFill = document.createElement('span')
  const reset = document.createElement('button')

  panel.className = 'quiz-progress'
  panel.dataset.quizProgress = ''
  heading.className = 'quiz-progress__heading'
  label.className = 'quiz-progress__label'
  value.className = 'quiz-progress__value'
  progress.className = 'quiz-progress__track'
  progressFill.className = 'quiz-progress__fill'
  progress.setAttribute('role', 'progressbar')
  progress.setAttribute('aria-valuemin', '0')
  progress.setAttribute('aria-valuemax', String(answers.length))
  reset.className = 'quiz-progress__reset'
  reset.type = 'button'

  heading.append(label, value)
  progress.append(progressFill)
  panel.append(heading, progress, reset)
  answers[0].parentNode.insertBefore(panel, answers[0])

  const update = () => {
    const copy = progressCopy(routePath, reviewedAnswers.size, answers.length)
    const percentage = answers.length === 0
      ? 0
      : Math.round((reviewedAnswers.size / answers.length) * 100)

    label.textContent = copy.label
    value.textContent = copy.value
    reset.textContent = copy.reset
    reset.disabled = reviewedAnswers.size === 0
    progress.setAttribute('aria-label', copy.label)
    progress.setAttribute('aria-valuenow', String(reviewedAnswers.size))
    progressFill.style.width = `${percentage}%`

    answers.forEach((answer, index) => {
      answer.classList.toggle('quiz-answer-reviewed', reviewedAnswers.has(index))
    })
  }

  const listeners = answers.map((answer, index) => {
    const listener = () => {
      if (!answer.open || reviewedAnswers.has(index)) return
      reviewedAnswers.add(index)
      try {
        writeReviewedAnswers(storage, key, reviewedAnswers)
      } catch {
        // Progress remains available for the current page when storage is blocked.
      }
      update()
    }
    answer.addEventListener('toggle', listener)
    return listener
  })

  const resetListener = () => {
    reviewedAnswers.clear()
    try {
      storage.removeItem(key)
    } catch {
      // The in-memory state can still be reset when storage is blocked.
    }
    update()
  }
  reset.addEventListener('click', resetListener)
  update()

  return () => {
    answers.forEach((answer, index) => {
      answer.removeEventListener('toggle', listeners[index])
      answer.classList.remove('quiz-answer-reviewed')
    })
    reset.removeEventListener('click', resetListener)
    panel.remove()
  }
}
