<script setup>
import Pickr from '@simonwep/pickr'
import autosize from 'autosize'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import '@simonwep/pickr/dist/themes/classic.min.css'

import { getQuickTags, saveQuickTags } from '../api/client'
import { useQueuedSave } from '../blocks/queuedSave.js'
import { completeTags } from '../tags.js'

const STANDARDS = [
  { id: 'black', value: '#161616', label: '黑' },
  { id: 'white', value: '#f4f1ea', label: '白' },
  { id: 'red', value: '#d64545', label: '红' },
  { id: 'orange', value: '#e07a2f', label: '橙' },
  { id: 'yellow', value: '#e2b340', label: '黄' },
  { id: 'green', value: '#3f6f57', label: '绿' },
  { id: 'cyan', value: '#3ca1b0', label: '青' },
  { id: 'blue', value: '#3d6fd8', label: '蓝' },
  { id: 'purple', value: '#7a4e7a', label: '紫' },
  { id: 'gray', value: '#8a908c', label: '灰' },
]

const PRESETS = [
  { id: 'ink', value: '', label: '默认' },
  { id: 'moss', value: '#3f6f57', label: '苔' },
  { id: 'ember', value: '#d77245', label: '烬' },
  { id: 'aurora', value: '#5c79a8', label: '极光' },
  { id: 'plum', value: '#7a4e7a', label: '梅' },
]

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
  inbox: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['save'])

const mode = ref('numbered')
const lines = ref([{ text: '', color: '' }])
const paletteIndex = ref(-1)
const tagFilter = ref('')
const quickTags = ref([])
const draftTag = ref('')
const addingTag = ref(false)
const pickerHost = ref(null)
const areas = ref([])
const list = ref(null)
let pickr = null
let pickerToken = 0

function readContent() {
  const source = lines.value.length ? lines.value : [{ text: '', color: '' }]
  return {
    mode: mode.value === 'bullets' ? 'bullets' : 'numbered',
    lines: source.map((line) => ({ text: line.text, color: line.color || '' })),
  }
}

const { queue, flush } = useQueuedSave(emit, readContent)

function applyBlock(block) {
  const content = block.content || {}
  mode.value = content.mode === 'bullets' ? 'bullets' : 'numbered'
  const source = Array.isArray(content.lines) && content.lines.length ? content.lines : [{ text: '', color: '' }]
  lines.value = source.map((line) => ({ text: line.text || '', color: line.color || '' }))
  paletteIndex.value = -1
  refreshAreas()
}

watch(
  () => props.block.id,
  (_id, previous) => {
    if (previous != null) {
      flush()
    }
    applyBlock(props.block)
  },
  { immediate: true },
)

function lineVisible(line) {
  const raw = tagFilter.value.trim().replace(/^#/, '')
  if (!raw) {
    return true
  }
  if (props.inbox) {
    return (line.tags || []).some((tag) => String(tag).includes(raw))
  }
  const needle = tagFilter.value.trim().startsWith('#') ? tagFilter.value.trim().toLowerCase() : `#${raw.toLowerCase()}`
  return line.text.toLowerCase().includes(needle)
}

const viewLines = computed(() => {
  const rows = lines.value.map((line, index) => ({ line, index })).filter(({ line }) => lineVisible(line))
  if (!props.inbox) {
    return rows
  }
  return rows.sort((a, b) => String(b.line.at || '').localeCompare(String(a.line.at || '')))
})

function touch() {
  queue(props.block.id)
}

function setMode(next) {
  mode.value = next
  touch()
  flush()
}

function chooseSwatch(index, color, close) {
  setColor(index, color, close)
  if (color) {
    pickr?.setColor(color, true)
  }
}

function setColor(index, color, close) {
  lines.value[index].color = color
  if (close) {
    paletteIndex.value = -1
  }
  touch()
  flush()
}

function toHex(color) {
  const raw = String(color.toHEXA())
  return raw.length >= 7 ? raw.slice(0, 7) : raw
}

function destroyPicker() {
  if (!pickr) {
    return
  }
  pickr.destroyAndRemove()
  pickr = null
}

function bindPickerHost(element) {
  pickerHost.value = element
}

watch(paletteIndex, async (index) => {
  const token = ++pickerToken
  destroyPicker()
  if (index < 0) {
    return
  }
  await nextTick()
  if (token !== pickerToken || !pickerHost.value) {
    return
  }
  const current = lines.value[index]?.color || '#16201d'
  pickr = Pickr.create({
    el: pickerHost.value,
    theme: 'classic',
    inline: true,
    showAlways: true,
    default: current,
    defaultRepresentation: 'HEX',
    lockOpacity: true,
    comparison: false,
    appClass: 'plain-pickr',
    components: {
      palette: true,
      preview: true,
      opacity: false,
      hue: true,
      interaction: {
        hex: true,
        input: true,
        save: false,
        cancel: false,
        clear: false,
      },
    },
  })
  const applySeed = () => {
    pickr?.setColor(current, true)
  }
  pickr.on('init', applySeed)
  pickr.on('change', (color) => {
    const hex = toHex(color)
    const shown = (lines.value[index]?.color || '#16201d').toLowerCase()
    if (!hex || hex.toLowerCase() === shown) {
      return
    }
    lines.value[index].color = hex
    touch()
  })
})

function refreshAreas() {
  nextTick(() => {
    areas.value.forEach((area) => {
      if (area) {
        autosize(area)
        autosize.update(area)
      }
    })
  })
}

function focusLine(index) {
  nextTick(() => {
    const area = areas.value[index]
    if (!area) {
      return
    }
    area.focus()
    autosize.update(area)
  })
}

function grow(event) {
  touch()
  autosize(event.target)
  autosize.update(event.target)
}

function onKeydown(event, index) {
  if (event.key === 'Enter') {
    event.preventDefault()
    const color = lines.value[index].color || ''
    lines.value.splice(index + 1, 0, { text: '', color })
    touch()
    refreshAreas()
    focusLine(index + 1)
    return
  }
  if (event.key === 'Backspace' && lines.value[index].text === '' && lines.value.length > 1) {
    event.preventDefault()
    lines.value.splice(index, 1)
    touch()
    focusLine(Math.max(0, index - 1))
  }
}

function onPointerDown(event) {
  if (paletteIndex.value < 0) {
    return
  }
  const target = event.target
  if (target?.closest?.('.plain-palette') || target?.closest?.('.plain-swatch') || target?.closest?.('.pcr-app')) {
    return
  }
  paletteIndex.value = -1
}

let observer = null

onMounted(() => {
  document.addEventListener('pointerdown', onPointerDown)
  refreshAreas()
  if (props.inbox) {
    getQuickTags().then((payload) => {
      quickTags.value = payload.tags || []
    }).catch(() => {
      quickTags.value = []
    })
  }
  if (list.value) {
    observer = new ResizeObserver(() => refreshAreas())
    observer.observe(list.value)
  }
})

onBeforeUnmount(() => {
  destroyPicker()
  document.removeEventListener('pointerdown', onPointerDown)
  observer?.disconnect()
  areas.value.forEach((area) => {
    if (area) {
      autosize.destroy(area)
    }
  })
})

function removeInboxLine(index) {
  if (lines.value.length <= 1) {
    lines.value = [{ text: '', color: '', at: '', tags: [] }]
  } else {
    lines.value.splice(index, 1)
  }
  touch()
  flush()
}

async function persistQuickTags(next) {
  quickTags.value = next
  try {
    const saved = await saveQuickTags(next)
    quickTags.value = saved.tags || next
  } catch (error) {
    console.error(error)
  }
}

function addQuickTag() {
  const text = draftTag.value.trim().replace(/^#/, '')
  draftTag.value = ''
  addingTag.value = false
  if (!text || quickTags.value.includes(text) || quickTags.value.length >= 6) {
    return
  }
  persistQuickTags([...quickTags.value, text])
}

function dropQuickTag(tag) {
  persistQuickTags(quickTags.value.filter((item) => item !== tag))
}
</script>

<template>
  <div class="mx-auto flex min-h-full w-full max-w-3xl flex-col px-6 py-5">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div class="flex rounded-md bg-black/5 p-0.5">
        <button
          type="button"
          class="h-7 rounded px-3 text-xs font-medium"
          :class="mode === 'numbered' ? 'bg-white text-ink shadow-sm' : 'text-ink/55'"
          @click="setMode('numbered')"
        >
          行号模式
        </button>
        <button
          type="button"
          class="h-7 rounded px-3 text-xs font-medium"
          :class="mode === 'bullets' ? 'bg-white text-ink shadow-sm' : 'text-ink/55'"
          @click="setMode('bullets')"
        >
          · 分条模式
        </button>
      </div>
      <div v-if="inbox" class="mb-3 flex flex-wrap items-center gap-1">
        <button
          v-for="tag in quickTags"
          :key="tag"
          type="button"
          class="group/tag h-7 rounded px-2 text-xs"
          :class="tagFilter === tag ? 'bg-aurora text-white' : 'bg-white text-ink/70'"
          @click="tagFilter = tagFilter === tag ? '' : tag"
        >
          {{ tag }}
          <span class="ml-1 opacity-0 group-hover/tag:opacity-100" @click.stop="dropQuickTag(tag)">×</span>
        </button>
        <form v-if="addingTag" class="flex" @submit.prevent="addQuickTag">
          <input v-model="draftTag" class="h-7 w-20 rounded border border-black/10 px-2 text-xs outline-none" maxlength="24" />
        </form>
        <button v-else-if="quickTags.length < 6" type="button" class="h-7 rounded bg-white px-2 text-xs" @click="addingTag = true">+</button>
      </div>
      <input
        v-else
        v-model="tagFilter"
        type="text"
        class="h-8 w-36 rounded border border-black/10 bg-white px-2 text-xs outline-none"
        placeholder="#标签"
      />
    </div>

    <div ref="list" class="flex flex-col">
      <div v-for="{ line, index } in viewLines" :key="index" class="group/line relative flex items-start gap-2 border-b border-black/[0.04] py-1">
        <button
          type="button"
          class="plain-swatch mt-2 h-4 w-4 shrink-0 rounded-full border border-black/20"
          :style="{ background: line.color || '#16201d' }"
          title="行颜色"
          @click="paletteIndex = paletteIndex === index ? -1 : index"
        />
        <span
          v-if="mode === 'bullets'"
          class="plain-mark"
          :style="{ background: line.color || '#16201d' }"
        />
        <span v-else class="mt-0.5 w-8 shrink-0 text-right font-mono text-sm leading-7 text-ink/40">
          {{ index + 1 }}
        </span>
        <textarea
          :ref="(element) => (areas[index] = element)"
          v-model="line.text"
          rows="1"
          class="min-w-0 flex-1 resize-none overflow-hidden bg-transparent py-0.5 pr-24 text-[15px] leading-7 outline-none"
          :style="{ color: line.color || '#16201d' }"
          :placeholder="index === 0 ? '写一条' : ''"
          @input="grow"
          @keydown="onKeydown($event, index)"
        />
        <div class="mt-1 flex max-w-[40%] flex-wrap justify-end gap-1">
          <button
            v-for="tag in completeTags(line.text)"
            :key="tag"
            type="button"
            class="wv-tag text-[11px]"
            @click="tagFilter = `#${tag} `"
          >
            #{{ tag }}
          </button>
        </div>
        <span v-if="line.at" class="pointer-events-none absolute bottom-0.5 right-1 text-[10px] text-ink/35 group-hover/line:text-ink/70">{{ line.at }}</span>
        <button
          v-if="inbox"
          type="button"
          class="absolute right-1 top-1 hidden text-xs text-ember group-hover/line:block"
          @click="removeInboxLine(index)"
        >
          删除
        </button>
        <div v-if="inbox && line.tags?.length" class="absolute bottom-0.5 left-8 flex gap-1">
          <span v-for="tag in line.tags" :key="tag" class="wv-tag text-[10px]">#{{ tag }}</span>
        </div>
        <div
          v-if="paletteIndex === index"
          class="plain-palette absolute left-0 top-8 z-20 rounded-md border border-black/10 bg-white p-2 shadow-lg"
          @pointerdown.stop
        >
          <div class="mb-2 flex flex-wrap gap-1">
            <button
              v-for="swatch in STANDARDS"
              :key="swatch.id"
              type="button"
              class="h-5 w-5 rounded-full border border-black/15"
              :style="{ background: swatch.value }"
              :title="swatch.label"
              @click="chooseSwatch(index, swatch.value, false)"
            />
          </div>
          <div class="mb-2 flex items-center gap-1">
            <button
              v-for="preset in PRESETS"
              :key="preset.id"
              type="button"
              class="h-6 w-6 rounded-full border border-black/10"
              :style="{ background: preset.value || '#16201d' }"
              :title="preset.label"
              @click="setColor(index, preset.value, true)"
            />
          </div>
          <div v-once :ref="bindPickerHost" class="plain-picker-host"></div>
        </div>
      </div>
    </div>
  </div>
</template>
