import assert from 'node:assert/strict'
import test from 'node:test'

import {
  progressCopy,
  quizProgressKey,
  readReviewedAnswers,
  writeReviewedAnswers
} from '../../.vitepress/theme/quiz-progress.mjs'

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null
    },
    setItem(key, value) {
      values.set(key, value)
    },
    removeItem(key) {
      values.delete(key)
    },
    value(key) {
      return values.get(key)
    }
  }
}

test('quizProgressKey is stable across trailing slash variants', () => {
  assert.equal(
    quizProgressKey('/ko/quizzes/core/01-cluster-architecture-quiz/'),
    quizProgressKey('/ko/quizzes/core/01-cluster-architecture-quiz')
  )
})

test('readReviewedAnswers filters invalid and out-of-range entries', () => {
  const key = quizProgressKey('/ko/quizzes/core/example')
  const storage = memoryStorage({
    [key]: JSON.stringify([3, 1, 1, -1, 9, '2'])
  })

  assert.deepEqual([...readReviewedAnswers(storage, key, 5)], [1, 3])
})

test('readReviewedAnswers tolerates corrupt storage', () => {
  const key = quizProgressKey('/en/quizzes/core/example')
  const storage = memoryStorage({ [key]: '{not-json' })

  assert.deepEqual([...readReviewedAnswers(storage, key, 5)], [])
})

test('writeReviewedAnswers persists a sorted unique list', () => {
  const key = quizProgressKey('/en/quizzes/core/example')
  const storage = memoryStorage()

  writeReviewedAnswers(storage, key, new Set([4, 1, 3]))

  assert.equal(storage.value(key), '[1,3,4]')
})

test('progressCopy localizes Korean and English labels', () => {
  assert.deepEqual(progressCopy('/ko/quizzes/core/example', 2, 10), {
    label: '복습 진행',
    value: '2/10',
    reset: '진도 초기화'
  })
  assert.deepEqual(progressCopy('/en/quizzes/core/example', 2, 10), {
    label: 'Review progress',
    value: '2/10',
    reset: 'Reset progress'
  })
})
