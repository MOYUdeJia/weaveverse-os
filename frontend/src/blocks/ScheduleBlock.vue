<script setup>
// 计划表区块：按日期分组展示条目，勾选和编辑后立刻保存。
import { computed, ref, watch } from 'vue'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'delete'])

const entries = ref([])
const openNotes = ref({})
const draft = ref({ date: today(), title: '', note: '' })

watch(
  () => props.block,
  () => {
    entries.value = (props.block.content?.entries || []).map((entry) => ({
      date: entry.date || '',
      title: entry.title || '',
      done: Boolean(entry.done),
      note: entry.note || '',
    }))
  },
  { immediate: true, deep: true },
)

const groups = computed(() => {
  const grouped = new Map()
  entries.value.forEach((entry, index) => {
    const date = entry.date || '未定日期'
    if (!grouped.has(date)) {
      grouped.set(date, [])
    }
    grouped.get(date).push({ ...entry, index })
  })
  return [...grouped.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([date, items]) => ({ date, items }))
})

function today() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

function persist(nextEntries) {
  entries.value = nextEntries
  emit('save', {
    entries: nextEntries.map(({ date, title, done, note }) => ({ date, title, done, note })),
  })
}

function updateEntry(index, patch) {
  persist(entries.value.map((entry, entryIndex) => (entryIndex === index ? { ...entry, ...patch } : entry)))
}

function addEntry() {
  const title = draft.value.title.trim()
  if (!draft.value.date || !title) {
    return
  }
  persist([
    ...entries.value,
    { date: draft.value.date, title, done: false, note: draft.value.note.trim() },
  ])
  draft.value = { date: draft.value.date, title: '', note: '' }
}

function removeEntry(index) {
  const nextOpen = {}
  entries.value.forEach((_, entryIndex) => {
    if (entryIndex === index || !openNotes.value[entryIndex]) {
      return
    }
    nextOpen[entryIndex > index ? entryIndex - 1 : entryIndex] = true
  })
  openNotes.value = nextOpen
  persist(entries.value.filter((_, entryIndex) => entryIndex !== index))
}

function toggleNote(index) {
  openNotes.value = { ...openNotes.value, [index]: !openNotes.value[index] }
}

function confirmDelete() {
  if (window.confirm('确定删除这个计划表区块吗？')) {
    emit('delete')
  }
}
</script>

<template>
  <article class="rounded-md border border-black/10 bg-white/80 p-4 shadow-sm">
    <div class="mb-3 flex items-center justify-between gap-3">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-moss">计划表</p>
      <button type="button" class="grid h-8 w-8 place-items-center rounded-md hover:bg-black/5" title="删除" @click="confirmDelete">
        🗑️
      </button>
    </div>

    <p v-if="entries.length === 0" class="text-sm text-ink/50">还没有计划</p>

    <div v-else class="space-y-4">
      <section v-for="group in groups" :key="group.date">
        <p class="text-xs font-semibold tracking-wide text-aurora">{{ group.date }}</p>
        <ul class="mt-2 space-y-2">
          <li v-for="entry in group.items" :key="entry.index" class="rounded-md bg-dawn/60 px-2 py-2">
            <div class="flex items-center gap-2">
              <input type="checkbox" :checked="entry.done" @change="updateEntry(entry.index, { done: !entry.done })" />
              <input
                type="date"
                :value="entry.date"
                class="h-9 rounded-md border border-transparent bg-transparent px-1 text-sm outline-none focus:border-moss"
                @change="updateEntry(entry.index, { date: $event.target.value })"
              />
              <input
                :value="entry.title"
                class="h-9 min-w-0 flex-1 rounded-md border border-transparent bg-transparent px-2 text-sm outline-none focus:border-moss"
                :class="entry.done ? 'text-ink/40 line-through' : 'text-ink'"
                @change="updateEntry(entry.index, { title: $event.target.value.trim() })"
              />
              <button type="button" class="text-xs text-ink/50 hover:text-moss" @click="toggleNote(entry.index)">
                {{ openNotes[entry.index] ? '收起' : '备注' }}
              </button>
              <button type="button" class="text-xs text-ink/50 hover:text-ember" @click="removeEntry(entry.index)">删除</button>
            </div>
            <textarea
              v-if="openNotes[entry.index]"
              :value="entry.note"
              rows="2"
              class="mt-2 w-full rounded-md border border-black/10 bg-white px-2 py-1 text-sm outline-none focus:border-moss"
              placeholder="备注"
              @change="updateEntry(entry.index, { note: $event.target.value })"
            />
          </li>
        </ul>
      </section>
    </div>

    <form class="mt-4 grid gap-2 sm:grid-cols-[auto_1fr_auto]" @submit.prevent="addEntry">
      <input v-model="draft.date" type="date" required class="h-10 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss" />
      <input v-model="draft.title" class="h-10 rounded-md border border-black/15 bg-white px-3 text-sm outline-none focus:border-moss" placeholder="计划标题" />
      <button type="submit" class="h-10 rounded-md bg-ink px-3 text-sm font-semibold text-white hover:bg-moss">+ 添加计划</button>
      <input v-model="draft.note" class="h-10 rounded-md border border-black/15 bg-white px-3 text-sm outline-none focus:border-moss sm:col-span-3" placeholder="备注（可选）" />
    </form>
  </article>
</template>
