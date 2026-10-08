<script setup>
import { Ellipse, Canvas, Line, Path, PencilBrush, Point, Rect, Textbox } from 'fabric'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const TOOLS = [
  { id: 'select', label: '选择' },
  { id: 'pan', label: '拖动画布' },
  { id: 'pen', label: '画笔' },
  { id: 'rect', label: '矩形' },
  { id: 'ellipse', label: '圆' },
  { id: 'line', label: '直线' },
  { id: 'arrow', label: '箭头' },
  { id: 'text', label: '文本' },
]

const SWATCHES = ['#16201d', '#3f6f57', '#d77245', '#5c79a8', '#7a4e7a', '#c4a15a']
const DRAW_TOOLS = new Set(['rect', 'ellipse', 'line', 'arrow'])

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save'])

const host = ref(null)
const canvasEl = ref(null)
const tool = ref('pen')
const color = ref('#16201d')
const canUndo = ref(false)
const canRedo = ref(false)

let canvas = null
let observer = null
let timer = null
let blockId = null
let dirty = false
let pausing = false
let history = []
let cursor = -1
let mounted = false

function exportJson() {
  const data = canvas.toJSON()
  data.viewportTransform = [...canvas.viewportTransform]
  return data
}

function refreshHistoryButtons() {
  canUndo.value = cursor > 0
  canRedo.value = cursor >= 0 && cursor < history.length - 1
}

function scheduleSave() {
  dirty = true
  clearTimeout(timer)
  timer = setTimeout(flushSave, 500)
}

function flushSave() {
  if (!dirty || !canvas || blockId == null) {
    return
  }
  clearTimeout(timer)
  timer = null
  dirty = false
  emit('save', { blockId, content: exportJson() })
}

function snapshot() {
  if (pausing || !canvas) {
    return
  }
  const json = JSON.stringify(exportJson())
  if (history[cursor] === json) {
    return
  }
  history = history.slice(0, cursor + 1)
  history.push(json)
  if (history.length > 40) {
    history.shift()
  }
  cursor = history.length - 1
  refreshHistoryButtons()
  scheduleSave()
}

function scenePoint(event) {
  if (typeof canvas.getScenePoint === 'function') {
    return canvas.getScenePoint(event)
  }
  return canvas.getPointer(event)
}

function viewportPoint(event) {
  if (typeof canvas.getViewportPoint === 'function') {
    return canvas.getViewportPoint(event)
  }
  const bounds = canvas.upperCanvasEl.getBoundingClientRect()
  return new Point(event.clientX - bounds.left, event.clientY - bounds.top)
}

function arrowPath(x1, y1, x2, y2) {
  const angle = Math.atan2(y2 - y1, x2 - x1)
  const head = 16
  const wing = Math.PI / 6
  const x3 = x2 - head * Math.cos(angle - wing)
  const y3 = y2 - head * Math.sin(angle - wing)
  const x4 = x2 - head * Math.cos(angle + wing)
  const y4 = y2 - head * Math.sin(angle + wing)
  return `M ${x1} ${y1} L ${x2} ${y2} M ${x3} ${y3} L ${x2} ${y2} L ${x4} ${y4}`
}

function makeShape(kind, start, end) {
  const stroke = color.value
  if (kind === 'rect') {
    return new Rect({
      left: Math.min(start.x, end.x),
      top: Math.min(start.y, end.y),
      width: Math.abs(end.x - start.x),
      height: Math.abs(end.y - start.y),
      fill: 'transparent',
      stroke,
      strokeWidth: 2,
    })
  }
  if (kind === 'ellipse') {
    return new Ellipse({
      left: Math.min(start.x, end.x),
      top: Math.min(start.y, end.y),
      rx: Math.abs(end.x - start.x) / 2,
      ry: Math.abs(end.y - start.y) / 2,
      originX: 'left',
      originY: 'top',
      fill: 'transparent',
      stroke,
      strokeWidth: 2,
    })
  }
  if (kind === 'line') {
    return new Line([start.x, start.y, end.x, end.y], { stroke, strokeWidth: 2 })
  }
  return new Path(arrowPath(start.x, start.y, end.x, end.y), {
    stroke,
    strokeWidth: 2,
    fill: '',
  })
}

function applyTool() {
  if (!canvas) {
    return
  }
  canvas.isDrawingMode = tool.value === 'pen'
  canvas.selection = tool.value === 'select'
  canvas.skipTargetFind = tool.value !== 'select'
  if (canvas.freeDrawingBrush) {
    canvas.freeDrawingBrush.color = color.value
    canvas.freeDrawingBrush.width = 3
  }
  const cursors = { pan: 'grab', pen: 'crosshair', text: 'text', select: 'default' }
  canvas.defaultCursor = cursors[tool.value] || 'crosshair'
}

function chooseTool(next) {
  tool.value = next
  applyTool()
}

function chooseColor(next) {
  color.value = next
  applyTool()
  const active = canvas?.getActiveObject()
  if (!active) {
    return
  }
  if (active.type === 'textbox' || active.type === 'i-text' || active.type === 'text') {
    active.set('fill', next)
  } else {
    active.set('stroke', next)
  }
  canvas.requestRenderAll()
  snapshot()
}

async function restore(index) {
  if (!canvas || index < 0 || index >= history.length) {
    return
  }
  pausing = true
  const data = JSON.parse(history[index])
  await canvas.loadFromJSON(data)
  if (Array.isArray(data.viewportTransform) && data.viewportTransform.length === 6) {
    canvas.setViewportTransform(data.viewportTransform)
  }
  pausing = false
  cursor = index
  canvas.requestRenderAll()
  refreshHistoryButtons()
  scheduleSave()
}

function undo() {
  if (cursor > 0) {
    restore(cursor - 1)
  }
}

function redo() {
  if (cursor < history.length - 1) {
    restore(cursor + 1)
  }
}

function resize() {
  if (!canvas || !host.value) {
    return
  }
  const box = host.value.getBoundingClientRect()
  if (box.width < 1 || box.height < 1) {
    return
  }
  canvas.setDimensions({ width: box.width, height: box.height })
}

async function setup(block) {
  blockId = block.id
  if (canvas) {
    canvas.dispose()
    canvas = null
  }
  const box = host.value.getBoundingClientRect()
  canvas = new Canvas(canvasEl.value, {
    width: Math.max(box.width, 320),
    height: Math.max(box.height, 240),
    backgroundColor: '#f6f3ec',
    preserveObjectStacking: true,
  })
  canvas.freeDrawingBrush = new PencilBrush(canvas)
  applyTool()

  let draft = null
  let start = null
  let panning = false
  let panLast = null

  function clearDraft() {
    if (!draft) {
      return
    }
    pausing = true
    canvas.remove(draft)
    pausing = false
    draft = null
  }

  canvas.on('object:added', snapshot)
  canvas.on('object:modified', snapshot)
  canvas.on('object:removed', snapshot)
  canvas.on('path:created', snapshot)
  canvas.on('text:changed', snapshot)

  canvas.on('mouse:wheel', (opt) => {
    let zoom = canvas.getZoom() * 0.999 ** opt.e.deltaY
    zoom = Math.max(0.15, Math.min(6, zoom))
    canvas.zoomToPoint(viewportPoint(opt.e), zoom)
    opt.e.preventDefault()
    opt.e.stopPropagation()
    scheduleSave()
  })

  canvas.on('mouse:down', (opt) => {
    if (tool.value === 'pan' || opt.e.button === 1) {
      panning = true
      panLast = { x: opt.e.clientX, y: opt.e.clientY }
      return
    }
    if (tool.value === 'text') {
      const point = scenePoint(opt.e)
      const text = new Textbox('文本', {
        left: point.x,
        top: point.y,
        width: 180,
        fontSize: 22,
        fill: color.value,
        fontFamily: 'sans-serif',
      })
      canvas.add(text)
      canvas.setActiveObject(text)
      text.enterEditing()
      tool.value = 'select'
      applyTool()
      return
    }
    if (!DRAW_TOOLS.has(tool.value)) {
      return
    }
    start = scenePoint(opt.e)
  })

  canvas.on('mouse:move', (opt) => {
    if (panning && panLast) {
      const transform = canvas.viewportTransform
      transform[4] += opt.e.clientX - panLast.x
      transform[5] += opt.e.clientY - panLast.y
      panLast = { x: opt.e.clientX, y: opt.e.clientY }
      canvas.setViewportTransform(transform)
      return
    }
    if (!start || !DRAW_TOOLS.has(tool.value)) {
      return
    }
    const point = scenePoint(opt.e)
    clearDraft()
    pausing = true
    draft = makeShape(tool.value, start, point)
    canvas.add(draft)
    pausing = false
    canvas.requestRenderAll()
  })

  canvas.on('mouse:up', () => {
    if (panning) {
      panning = false
      panLast = null
      snapshot()
      return
    }
    if (!start) {
      return
    }
    start = null
    if (!draft) {
      return
    }
    draft = null
    snapshot()
  })

  pausing = true
  try {
    const content = block.content && Array.isArray(block.content.objects) ? block.content : { objects: [] }
    await canvas.loadFromJSON(content)
    if (Array.isArray(content.viewportTransform) && content.viewportTransform.length === 6) {
      canvas.setViewportTransform(content.viewportTransform)
    }
  } catch (error) {
    console.error('Failed to load canvas:', error)
  }
  pausing = false
  canvas.requestRenderAll()
  history = [JSON.stringify(exportJson())]
  cursor = 0
  dirty = false
  refreshHistoryButtons()
  resize()
}

onMounted(async () => {
  mounted = true
  observer = new ResizeObserver(resize)
  if (host.value) {
    observer.observe(host.value)
  }
  await setup(props.block)
})

watch(
  () => props.block.id,
  async (id, previous) => {
    if (!mounted || previous == null || id === previous) {
      return
    }
    flushSave()
    await setup(props.block)
  },
)

onBeforeUnmount(() => {
  flushSave()
  observer?.disconnect()
  canvas?.dispose()
  canvas = null
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div ref="host" class="relative min-h-0 flex-1 overflow-hidden bg-[#f6f3ec]">
      <canvas ref="canvasEl" />
    </div>
    <div class="flex shrink-0 flex-wrap items-center gap-1 border-t border-black/10 bg-[#fcfaf5] px-3 py-2">
      <button
        v-for="item in TOOLS"
        :key="item.id"
        type="button"
        class="h-8 rounded-md px-2.5 text-xs font-medium"
        :class="tool === item.id ? 'bg-moss text-white' : 'bg-white text-ink hover:bg-black/5'"
        @click="chooseTool(item.id)"
      >
        {{ item.label }}
      </button>
      <span class="mx-1 h-5 w-px bg-black/10" />
      <button
        v-for="swatch in SWATCHES"
        :key="swatch"
        type="button"
        class="h-5 w-5 rounded-full border border-black/15"
        :class="color === swatch ? 'ring-2 ring-moss ring-offset-1' : ''"
        :style="{ background: swatch }"
        :title="swatch"
        @click="chooseColor(swatch)"
      />
      <input
        :value="color"
        type="color"
        class="h-7 w-8 cursor-pointer border-0 bg-transparent p-0"
        title="自定义颜色"
        @input="chooseColor($event.target.value)"
      />
      <span class="mx-1 h-5 w-px bg-black/10" />
      <button type="button" class="h-8 rounded-md bg-white px-2.5 text-xs disabled:opacity-40" :disabled="!canUndo" @click="undo">
        撤销
      </button>
      <button type="button" class="h-8 rounded-md bg-white px-2.5 text-xs disabled:opacity-40" :disabled="!canRedo" @click="redo">
        重做
      </button>
      <span class="ml-auto text-xs text-ink/40">滚轮缩放 · 自动保存</span>
    </div>
  </div>
</template>
