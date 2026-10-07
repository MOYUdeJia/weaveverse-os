<script setup>
// 图表区块：用原生 SVG 画折线或柱状图，不依赖图表库。
import { computed, ref, watch } from 'vue'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'delete'])

const WIDTH = 360
const HEIGHT = 200
const PAD = { left: 42, right: 12, top: 16, bottom: 36 }

const chartType = ref('line')
const unit = ref('')
const points = ref([])
const draft = ref({ label: '', value: 0 })

watch(
  () => props.block,
  () => {
    const content = props.block.content || {}
    chartType.value = content.chart_type === 'bar' ? 'bar' : 'line'
    unit.value = content.unit || ''
    points.value = (content.data || []).map((point) => ({
      label: point.label || '',
      value: Number(point.value) || 0,
    }))
  },
  { immediate: true, deep: true },
)

const geometry = computed(() => {
  const plotWidth = WIDTH - PAD.left - PAD.right
  const plotHeight = HEIGHT - PAD.top - PAD.bottom
  const values = points.value.map((point) => point.value)
  let min = Math.min(...values)
  let max = Math.max(...values)
  if (chartType.value === 'bar') {
    min = Math.min(min, 0)
    max = Math.max(max, 0)
  }
  if (min === max) {
    min -= 1
    max += 1
  }
  const span = max - min
  const yOf = (value) => PAD.top + (1 - (value - min) / span) * plotHeight
  const baseline = yOf(0)
  const count = points.value.length
  const slot = count > 0 ? plotWidth / count : plotWidth
  const barWidth = Math.min(28, slot * 0.55)

  const marks = points.value.map((point, index) => {
    const lineX = count === 1 ? PAD.left + plotWidth / 2 : PAD.left + (index / (count - 1)) * plotWidth
    const barX = PAD.left + slot * index + (slot - barWidth) / 2
    const y = yOf(point.value)
    const top = Math.min(y, baseline)
    return {
      ...point,
      lineX,
      barX,
      y,
      barY: top,
      barHeight: Math.max(Math.abs(baseline - y), 1),
      labelX: chartType.value === 'bar' ? barX + barWidth / 2 : lineX,
    }
  })

  return {
    baseline,
    barWidth,
    axisBottom: HEIGHT - PAD.bottom,
    polyline: marks.map((mark) => `${mark.lineX},${mark.y}`).join(' '),
    marks,
    min,
    max,
  }
})

function payload(next = {}) {
  return {
    chart_type: next.chartType ?? chartType.value,
    unit: next.unit ?? unit.value,
    data: (next.points ?? points.value).map(({ label, value }) => ({
      label,
      value: Number(value),
    })),
  }
}

function persist(next) {
  if (next.chartType) {
    chartType.value = next.chartType
  }
  if (next.unit !== undefined) {
    unit.value = next.unit
  }
  if (next.points) {
    points.value = next.points
  }
  emit('save', payload(next))
}

function addPoint() {
  const label = draft.value.label.trim()
  if (!label || !Number.isFinite(Number(draft.value.value))) {
    return
  }
  persist({ points: [...points.value, { label, value: Number(draft.value.value) }] })
  draft.value = { label: '', value: 0 }
}

function updatePoint(index, patch) {
  persist({
    points: points.value.map((point, pointIndex) => (pointIndex === index ? { ...point, ...patch } : point)),
  })
}

function removePoint(index) {
  persist({ points: points.value.filter((_, pointIndex) => pointIndex !== index) })
}

function confirmDelete() {
  if (window.confirm('确定删除这个图表区块吗？')) {
    emit('delete')
  }
}

function formatTick(value) {
  const rounded = Math.round(value * 100) / 100
  return Number.isInteger(rounded) ? String(rounded) : String(rounded)
}
</script>

<template>
  <article class="rounded-md border border-black/10 bg-white/80 p-4 shadow-sm">
    <div class="mb-3 flex items-center justify-between gap-3">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-moss">图表</p>
      <button type="button" class="grid h-8 w-8 place-items-center rounded-md hover:bg-black/5" title="删除" @click="confirmDelete">
        🗑️
      </button>
    </div>

    <div class="mb-3 flex flex-wrap gap-2">
      <select
        :value="chartType"
        class="h-9 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss"
        @change="persist({ chartType: $event.target.value })"
      >
        <option value="line">折线图</option>
        <option value="bar">柱状图</option>
      </select>
      <input
        :value="unit"
        class="h-9 w-24 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss"
        placeholder="单位"
        @change="persist({ unit: $event.target.value.trim() })"
      />
    </div>

    <p v-if="points.length === 0" class="py-8 text-center text-sm text-ink/50">暂无数据</p>
    <svg v-else :viewBox="`0 0 ${WIDTH} ${HEIGHT}`" class="h-52 w-full" role="img" aria-label="图表">
      <line :x1="PAD.left" :y1="PAD.top" :x2="PAD.left" :y2="geometry.axisBottom" stroke="#16201d" stroke-opacity="0.35" />
      <line :x1="PAD.left" :y1="geometry.axisBottom" :x2="WIDTH - PAD.right" :y2="geometry.axisBottom" stroke="#16201d" stroke-opacity="0.35" />
      <text :x="PAD.left - 6" :y="PAD.top + 4" text-anchor="end" fill="#16201d" fill-opacity="0.55" font-size="10">
        {{ formatTick(geometry.max) }}{{ unit ? ` ${unit}` : '' }}
      </text>
      <text :x="PAD.left - 6" :y="geometry.axisBottom" text-anchor="end" fill="#16201d" fill-opacity="0.55" font-size="10">
        {{ formatTick(geometry.min) }}
      </text>
      <template v-if="chartType === 'bar'">
        <rect
          v-for="(mark, index) in geometry.marks"
          :key="`bar-${index}`"
          :x="mark.barX"
          :y="mark.barY"
          :width="geometry.barWidth"
          :height="mark.barHeight"
          fill="#3f6f57"
          rx="2"
        />
      </template>
      <template v-else>
        <polyline :points="geometry.polyline" fill="none" stroke="#3f6f57" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        <circle v-for="(mark, index) in geometry.marks" :key="`dot-${index}`" :cx="mark.lineX" :cy="mark.y" r="3.5" fill="#d77245" />
      </template>
      <text
        v-for="(mark, index) in geometry.marks"
        :key="`label-${index}`"
        :x="mark.labelX"
        :y="HEIGHT - 12"
        text-anchor="middle"
        fill="#16201d"
        fill-opacity="0.7"
        font-size="10"
      >
        {{ mark.label }}
      </text>
    </svg>

    <ul class="mt-3 space-y-2">
      <li v-for="(point, index) in points" :key="index" class="flex gap-2">
        <input
          :value="point.label"
          class="h-9 flex-1 rounded-md border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss"
          @change="updatePoint(index, { label: $event.target.value.trim() })"
        />
        <input
          :value="point.value"
          type="number"
          step="any"
          class="h-9 w-24 rounded-md border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss"
          @change="updatePoint(index, { value: Number($event.target.value) })"
        />
        <button type="button" class="text-xs text-ink/50 hover:text-ember" @click="removePoint(index)">删除</button>
      </li>
    </ul>

    <form class="mt-3 flex gap-2" @submit.prevent="addPoint">
      <input v-model="draft.label" class="h-10 flex-1 rounded-md border border-black/15 bg-white px-3 text-sm outline-none focus:border-moss" placeholder="标签" />
      <input v-model.number="draft.value" type="number" step="any" class="h-10 w-24 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss" />
      <button type="submit" class="h-10 rounded-md bg-ink px-3 text-sm font-semibold text-white hover:bg-moss">+ 添加数据点</button>
    </form>
  </article>
</template>
