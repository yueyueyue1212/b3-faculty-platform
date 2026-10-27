<template>
  <div ref="chartEl" class="base-chart" :style="{ height }" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{ option: any; height?: string }>(), {
  height: '310px',
})

const chartEl = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function render() {
  if (!chartEl.value) return
  if (!chart) {
    chart = echarts.init(chartEl.value)
  }
  chart.setOption(props.option || {}, true)
  chart.resize()
}

onMounted(() => {
  render()
  if (chartEl.value) {
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(chartEl.value)
  }
})

watch(
  () => props.option,
  () => render(),
  { deep: true },
)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>
