<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps<{ graph: string, id: string }>()
const svg = ref('')
let stopped = false
let observer: MutationObserver | undefined
let renderNumber = 0

async function render() {
  const { default: mermaid } = await import('mermaid')
  const currentRender = ++renderNumber
  const dark = document.documentElement.classList.contains('dark')
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: dark ? 'dark' : 'base',
    themeVariables: dark ? undefined : {
      primaryColor: '#efe5d1',
      primaryTextColor: '#172536',
      lineColor: '#a43e2f'
    }
  })
  const result = await mermaid.render(`${props.id}-${currentRender}`, decodeURIComponent(props.graph))
  if (!stopped && currentRender === renderNumber) {
    svg.value = result.svg
    await nextTick()
    result.bindFunctions?.(document.querySelector(`[data-mermaid-id="${props.id}"]`) as HTMLElement)
  }
}

onMounted(() => {
  observer = new MutationObserver(records => {
    if (records.some(record => record.attributeName === 'class')) void render()
  })
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  void render()
})

onUnmounted(() => {
  stopped = true
  observer?.disconnect()
})
</script>

<template><div class="mermaid" :data-mermaid-id="id" v-html="svg" /></template>
