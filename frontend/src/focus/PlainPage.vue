<script setup>
import Pickr from '@simonwep/pickr'
import autosize from 'autosize'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import '@simonwep/pickr/dist/themes/classic.min.css'

import { useQueuedSave } from '../blocks/queuedSave.js'

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
})

const emit = defineEmits(['save'])

const mode = ref('numbered')
const lines = ref([{ text: '', color: '' }])
const paletteIndex = ref(-1)
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

function touch() {
  queue(props.block.id)
}

function setMode(next) {
  mode.value = next
  touch()
  flush()
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
      <p class="text-xs text-ink/40">写满自动换行 · 回车新开一条</p>
    </div>

    <div ref="list" class="flex flex-col">
      <div v-for="(line, index) in lines" :key="index" class="relative flex items-start gap-2 border-b border-black/[0.04] py-1">
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
          class="min-w-0 flex-1 resize-none overflow-hidden bg-transparent py-0.5 text-[15px] leading-7 outline-none"
          :style="{ color: line.color || '#16201d' }"
          :placeholder="index === 0 ? '写一条' : ''"
          @input="grow"
          @keydown="onKeydown($event, index)"
        />
        <div
          v-if="paletteIndex === index"
          class="plain-palette absolute left-0 top-8 z-20 rounded-md border border-black/10 bg-white p-2 shadow-lg"
          @pointerdown.stop
        >
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
