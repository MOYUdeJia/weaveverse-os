<script setup>
import { computed, ref, watch } from 'vue'

import { addFocusSession, getFocusStats } from '../api/client'
import { showToast } from '../toast'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const grain = ref('week')
const start = ref('')
const end = ref('')
const data = ref(null)
const failed = ref('')
const backfill = ref({ label: '', minutes: 25, category: '学习' })

const pie = computed(() => {
  const rows = data.value?.categories || []
  const total = rows.reduce((sum, row) => sum + row.count, 0) || 1
  const colors = ['#d4251c', '#3f6f57', '#16201d', '#8faf9c']
  if (rows.length === 1) {
    return [{ ...rows[0], path: 'M 50 10 A 40 40 0 1 1 49.99 10 Z', color: colors[0] }]
  }
  let angle = 0
  return rows.map((row, index) => {
    const sweep = (row.count / total) * Math.PI * 2
    const startAngle = angle
    angle += sweep
    const large = sweep > Math.PI ? 1 : 0
    const x1 = 50 + 40 * Math.cos(startAngle)
    const y1 = 50 + 40 * Math.sin(startAngle)
    const x2 = 50 + 40 * Math.cos(angle)
    const y2 = 50 + 40 * Math.sin(angle)
    const path = `M 50 50 L ${x1} ${y1} A 40 40 0 ${large} 1 ${x2} ${y2} Z`
    return { ...row, path, color: colors[index % colors.length] }
  })
})

const doneShare = computed(() => {
  const done = data.value?.completion?.done || 0
  const left = data.value?.completion?.abandoned || 0
  const total = done + left || 1
  return Math.round((done / total) * 100)
})

function rangeFor(kind) {
  const today = new Date()
  const endDay = today.toISOString().slice(0, 10)
  const startDate = new Date(today)
  if (kind === 'day') startDate.setDate(today.getDate())
  else if (kind === 'week') startDate.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1))
  else startDate.setDate(1)
  return { start: startDate.toISOString().slice(0, 10), end: endDay }
}

async function load() {
  failed.value = ''
  const query = grain.value === 'custom' ? { start: start.value, end: end.value } : rangeFor(grain.value)
  start.value = query.start
  end.value = query.end
  try {
    data.value = await getFocusStats(query.start, query.end)
  } catch (error) {
    failed.value = error.message || '统计没有读出来'
  }
}

async function saveBackfill() {
  try {
    await addFocusSession(backfill.value)
    backfill.value = { label: '', minutes: 25, category: '学习' }
    await load()
  } catch (error) {
    showToast(error.message || '补记没有写上')
  }
}

function tone(day) {
  if (!day || day.future) return 'is-future'
  if (day.count >= 4) return 'is-deep'
  if (day.count >= 2) return 'is-mid'
  if (day.count > 0) return 'is-low'
  return ''
}

function exportCsv() {
  window.open(`/api/focus/stats.csv?start=${start.value}&end=${end.value}`, '_blank')
}

watch(
  () => props.open,
  (open) => {
    if (open) load()
  },
)
</script>

<template>
  <div v-if="open" class="mask" @click.self="emit('close')">
    <section class="sheet" role="dialog" aria-labelledby="focus-stats-title">
      <header>
        <h2 id="focus-stats-title">专注统计</h2>
        <button type="button" @click="emit('close')">关闭</button>
      </header>
      <div class="grains">
        <button type="button" :class="{ 'is-on': grain === 'day' }" @click="grain = 'day'; load()">日</button>
        <button type="button" :class="{ 'is-on': grain === 'week' }" @click="grain = 'week'; load()">周</button>
        <button type="button" :class="{ 'is-on': grain === 'month' }" @click="grain = 'month'; load()">月</button>
        <button type="button" :class="{ 'is-on': grain === 'custom' }" @click="grain = 'custom'">自选</button>
      </div>
      <form v-if="grain === 'custom'" class="custom" @submit.prevent="load">
        <input v-model="start" type="date" />
        <input v-model="end" type="date" />
        <button type="submit">查看</button>
      </form>
      <p v-if="failed">{{ failed }}</p>
      <template v-else-if="data">
        <dl class="numbers">
          <div><dt>累计专注次数</dt><dd>{{ data.count }}</dd></div>
          <div><dt>累计专注时长</dt><dd>{{ data.minutes }}</dd></div>
          <div><dt>日均时长</dt><dd>{{ data.daily_average }}</dd></div>
          <div><dt>总番茄数</dt><dd>{{ data.count }}</dd></div>
        </dl>
        <p class="peak">{{ data.peak ? `这段时间更多做完在${data.peak}` : '这段时间还没有完成的番茄' }}</p>

        <h3>这一周</h3>
        <div class="week" aria-label="一周专注纵览">
          <div v-for="(day, dayIndex) in data.week" :key="dayIndex" class="week-col">
            <i v-for="(slot, slotIndex) in day" :key="slotIndex" :class="slot ? 'is-on' : ''" :style="{ opacity: slot ? Math.min(1, 0.35 + slot * 0.2) : 1 }" />
          </div>
        </div>

        <h3>日历</h3>
        <div class="heat">
          <i v-for="day in data.days" :key="day.date" :class="tone(day)" :title="`${day.date} ${day.count} 个`" />
        </div>

        <h3>时长</h3>
        <div class="trend">
          <i v-for="day in data.days.slice(-14)" :key="day.date" :style="{ height: `${Math.min(72, day.minutes)}px` }" :title="`${day.date} ${day.minutes} 分钟`" />
        </div>

        <h3>分类</h3>
        <svg v-if="pie.length" class="pie" viewBox="0 0 100 100" role="img" aria-label="分类占比">
          <path v-for="slice in pie" :key="slice.name" :d="slice.path" :fill="slice.color" />
        </svg>
        <p v-for="slice in data.categories" :key="slice.name">{{ slice.name }} {{ slice.count }}</p>
        <p v-if="!data.categories.length">还没有分类</p>

        <h3>计划完成</h3>
        <div class="completion" aria-label="已完成与放弃">
          <i class="is-done" :style="{ width: `${doneShare}%` }" />
          <i class="is-left" />
        </div>
        <p>完成 {{ data.completion.done }} · 放弃 {{ data.completion.abandoned }}</p>

        <h3>打断</h3>
        <p v-for="row in data.interrupts" :key="row.name">{{ row.name }} {{ row.count }}</p>
        <p v-if="!data.interrupts.length">没有记下打断</p>

        <h3>记录</h3>
        <ul>
          <li v-for="row in data.history" :key="row.id">{{ row.at }} {{ row.label }} {{ row.minutes }} 分钟 {{ row.outcome === 'abandoned' ? '放弃' : '' }}</li>
        </ul>
        <form class="backfill" @submit.prevent="saveBackfill">
          <input v-model="backfill.label" placeholder="补记一件事" maxlength="40" />
          <input v-model.number="backfill.minutes" type="number" min="1" max="180" />
          <select v-model="backfill.category">
            <option>学习</option>
            <option>工作</option>
            <option>生活</option>
          </select>
          <button type="submit">补记</button>
        </form>
        <button type="button" class="export" @click="exportCsv">导出 CSV</button>
      </template>
    </section>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: transparent;
}

.sheet {
  position: absolute;
  bottom: 16px;
  left: 16px;
  width: min(420px, calc(100vw - 32px));
  max-height: calc(100vh - 32px);
  overflow: auto;
  padding: 20px;
  background: rgba(244, 239, 231, 0.96);
  color: #16201d;
}

header,
.grains,
.custom,
.backfill {
  display: flex;
  gap: 8px;
  align-items: center;
}

header h2 {
  margin: 0 auto 0 0;
  font-size: 28px;
  line-height: 1;
}

h3 {
  margin: 22px 0 8px;
  font-size: 16px;
}

button,
input,
select {
  border: 0;
  background: #fff;
  color: inherit;
  font: inherit;
  font-size: 14px;
}

button {
  padding: 6px 8px;
}

button.is-on {
  background: #16201d;
  color: #f4efe7;
}

.numbers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 16px 0;
}

.numbers div {
  background: #fff;
  padding: 10px;
}

dt {
  font-size: 13px;
}

dd {
  margin: 4px 0 0;
  font-size: 32px;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.week-col {
  display: grid;
  gap: 3px;
}

.week-col i,
.heat i {
  display: block;
  background: #e4ddd2;
}

.week-col i {
  height: 8px;
}

.week-col i.is-on {
  background: #d4251c;
}

.heat {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}

.heat i {
  width: 12px;
  height: 12px;
}

.heat i.is-low { background: #8faf9c; }
.heat i.is-mid { background: #3f6f57; }
.heat i.is-deep { background: #1d3d2e; }

.trend {
  display: flex;
  gap: 4px;
  align-items: end;
  height: 72px;
}

.trend i {
  flex: 1;
  background: #d4251c;
}

.pie {
  width: 120px;
  height: 120px;
}

.completion {
  display: flex;
  height: 16px;
  background: #e4ddd2;
}

.completion .is-done { background: #3f6f57; }
.completion .is-left { flex: 1; background: #d4251c; }

ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  padding: 4px 0;
  font-size: 14px;
}

.export {
  margin-top: 12px;
}

button:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 2px solid #3f6f57;
  outline-offset: 2px;
}
</style>
