#!/usr/bin/env node
import { mkdir, writeFile, rename } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { refreshStatistics } from './lib/public-statistics.mjs'

const publicDirectory = fileURLToPath(new URL('../public/', import.meta.url))
const destination = `${publicDirectory}/site-statistics.json`
const result = await refreshStatistics({
  propertyId: process.env.GA4_PROPERTY_ID,
  accessToken: process.env.GA4_ACCESS_TOKEN
})
await mkdir(publicDirectory, { recursive: true })
await writeFile(`${destination}.tmp`, `${JSON.stringify(result.snapshot, null, 2)}\n`)
await rename(`${destination}.tmp`, destination)
console.log(`Public statistics: ${result.source}`)
if (result.source !== 'ga4') {
  console.warn('GA4 refresh unavailable; published snapshot is retained when valid. Check GA4/OIDC configuration.')
}
