import assert from 'node:assert/strict'
import test from 'node:test'

import {
  isPlaceholderPng,
  readPngDimensions
} from '../validate-image-assets.mjs'

function pngHeader(width, height) {
  const buffer = Buffer.alloc(24)
  buffer.set([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  buffer.write('IHDR', 12, 'ascii')
  buffer.writeUInt32BE(width, 16)
  buffer.writeUInt32BE(height, 20)
  return buffer
}

test('readPngDimensions reads the IHDR dimensions', () => {
  assert.deepEqual(readPngDimensions(pngHeader(1600, 900)), {
    width: 1600,
    height: 900
  })
})

test('isPlaceholderPng rejects tiny placeholder images', () => {
  assert.equal(isPlaceholderPng(pngHeader(1, 1)), true)
  assert.equal(isPlaceholderPng(pngHeader(1600, 900)), false)
})

test('readPngDimensions rejects non-PNG data', () => {
  assert.throws(() => readPngDimensions(Buffer.from('not a png')), /valid PNG/)
})
