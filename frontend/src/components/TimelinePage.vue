<script setup>
// One spine for quick notes, reader notes, new pages, and finished focus rounds.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { getTimeline } from '../api/client'
import { focusClock, formatClock } from '../focusClock'

const emit = defineEmits(['open'])

const events = ref([])
const loading = ref(true)
const errorMessage = ref('')

const days = computed(() => {
  const groups = [
    { id: 'today', label: '今天', tone: 'is-today', events: [] },
    { id: 'yesterday', label: '昨天', tone: 'is-yesterday', events: [] },
    { id: 'earlier', label: '更早', tone: 'is-earlier', events: [] },
  ]
  const byId = Object.fromEntries(groups.map((item) => [item.id, item]))
  for (const event of events.value) {
    byId[bucket(event.at)].events.push(event)
  }
  return groups.filter((item) => item.events.length)
})

function bucket(iso) {
  if (!iso) {
    return 'earlier'
  }
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) {
    return 'earlier'
  }
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  const day = new Date(moment)
  day.setHours(0, 0, 0, 0)
  const diff = (start.getTime() - day.getTime()) / 86400000
  if (diff < 1) {
    return 'today'
  }
  if (diff < 2) {
    return 'yesterday'
  }
  return 'earlier'
}

function clock(iso) {
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) {
    return ''
  }
  return `${String(moment.getHours()).padStart(2, '0')}:${String(moment.getMinutes()).padStart(2, '0')}`
}

function sameText(event) {
  return event.title && event.title === event.summary
}

async function load() {
  errorMessage.value = ''
  try {
    const data = await getTimeline()
    events.value = data.events || []
  } catch (error) {
    errorMessage.value = error.message || '时间线没有加载出来'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  window.addEventListener('wv-timeline-refresh', load)
})

onBeforeUnmount(() => {
  window.removeEventListener('wv-timeline-refresh', load)
})
</script>

<template>
  <div class="wv-timeline">
    <header class="wv-timeline-head wv-rise">
      <h2>这些事发生过</h2>
      <p>速记、阅读笔记、新建的页面，还有完成的专注，按时间排在同一条线上。</p>
      <p v-if="focusClock.status === 'running'" class="wv-timeline-live">正在专注，还剩 {{ formatClock(focusClock.left) }}</p>
    </header>

    <p v-if="loading" class="wv-timeline-note">正在把记录排到线上。</p>
    <p v-else-if="errorMessage" class="wv-timeline-note is-error">{{ errorMessage }}</p>
    <p v-else-if="!days.length && focusClock.status !== 'running'" class="wv-timeline-note">
      还没有记录。写一条速记，或从侧栏开始一轮专注。
    </p>

    <section v-for="day in days" :key="day.id" class="wv-day wv-rise" :class="day.tone">
      <h3>{{ day.label }}</h3>
      <ol>
        <li v-for="(event, index) in day.events" :key="event.id" class="wv-rise" :style="{ animationDelay: `${Math.min(index, 8) * 70}ms` }">
          <time :datetime="event.at">{{ clock(event.at) }}</time>
          <button type="button" @click="emit('open', event)">
            <span class="wv-dot" aria-hidden="true" />
            <span class="wv-kind" aria-hidden="true">{{ event.icon }}</span>
            <span class="wv-copy">
              <strong>{{ event.title || '一条记录' }}</strong>
              <span v-if="!sameText(event)">{{ event.summary }}</span>
            </span>
          </button>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.wv-timeline {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 28px 28px 80px;
  color: #16201d;
}

.wv-timeline-head h2 {
  margin: 0;
  max-width: 16ch;
  font-size: clamp(40px, 6vw, 72px);
  line-height: 0.95;
  letter-spacing: -0.04em;
}

.wv-timeline-head p {
  max-width: 38rem;
  margin: 16px 0 0;
  font-size: 18px;
  line-height: 1.5;
}

.wv-timeline-live {
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}

.wv-timeline-note {
  margin: 36px 0 0;
  font-size: 18px;
}

.wv-timeline-note.is-error {
  color: #9a4036;
}

.wv-day {
  margin-top: 36px;
  padding: 22px 18px 8px;
}

.wv-day.is-today {
  background: #fffcf7;
}

.wv-day.is-yesterday {
  background: #f3efe6;
}

.wv-day.is-earlier {
  background: #efeae1;
}

.wv-day h3 {
  margin: 0 0 8px;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.wv-day ol {
  position: relative;
  margin: 0;
  padding: 0;
  list-style: none;
}

.wv-day ol::before {
  content: "";
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 78px;
  width: 3px;
  background: #3f6f57;
}

.wv-day li {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 28px;
  align-items: start;
}

.wv-day time {
  padding-top: 14px;
  font-size: 15px;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.wv-day button {
  display: grid;
  grid-template-columns: 16px 28px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  width: 100%;
  min-height: 44px;
  padding: 12px 0 16px;
  background: transparent;
  text-align: left;
}

.wv-dot {
  width: 12px;
  height: 12px;
  margin-top: 6px;
  margin-left: 2px;
  background: #16201d;
}

.wv-kind {
  font-size: 18px;
  line-height: 1.3;
}

.wv-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.wv-copy strong,
.wv-copy span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.wv-copy strong {
  font-size: 17px;
  line-height: 1.35;
}

.wv-copy span {
  font-size: 15px;
  line-height: 1.45;
}

.wv-day button:hover .wv-copy strong,
.wv-day button:focus-visible .wv-copy strong {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.wv-day button:focus-visible {
  outline: 2px solid #3f6f57;
  outline-offset: 2px;
}

.wv-rise {
  animation: wv-rise 480ms ease both;
}

@keyframes wv-rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 768px) {
  .wv-timeline {
    padding: 64px 16px 96px;
  }

  .wv-day ol::before {
    left: 62px;
  }

  .wv-day li {
    grid-template-columns: 48px minmax(0, 1fr);
    gap: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .wv-rise {
    animation: none;
  }
}
</style>
