<script setup>
import DefaultTheme from 'vitepress/theme'
import { useData } from 'vitepress'
import SiteStatistics from './SiteStatistics.vue'

const { page } = useData()
</script>

<template>
  <DefaultTheme.Layout>
    <template #doc-footer-before>
      <SiteStatistics v-if="!page.relativePath.endsWith('/statistics.md')" compact />
    </template>
  </DefaultTheme.Layout>
</template>
