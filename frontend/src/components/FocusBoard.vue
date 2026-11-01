<script setup>
// Sidebar entry for the focus console. The tomato list lives in the dialog.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import draggable from 'vuedraggable'

import {
  createFocusPreset,
  deleteFocusPresets,
  getFocusPresets,
  reorderFocusPresets,
  updateFocusPreset,
} from '../api/client'
import { focusClock, focusCommand, formatClock } from '../focusClock'
import { claimNoise, stopNoise } from '../focusNoise'
import { showToast } from '../toast'

const emit = defineEmits(['start'])

const open = ref(false)
const items = ref([])
const picking = ref(false)
const chosen = ref([])
const editor = ref(null)
const draft = ref(blank())

const categories = ['学习', '工作', '生活']
const givingUp = ref(false)
const clock = computed(() => formatClock(focusClock.left))
const active = computed(() => focusClock.status === 'running' || focusClock.status === 'paused')

function blank() {
  return { name: '', focus_minutes: 25, rest_minutes: 5, cycles: 1, category: '学习' }
}

async function load() {
  try {
    const data = await getFocusPresets()
    items.value = data.items || []
  } catch (error) {
    showToast(error.message || '番茄钟没有读出来')
  }
}

function show() {
  open.value = true
  load()
}

function close() {
  open.value = false
  editor.value = null
  picking.value = false
}

function openNew() {
  draft.value = blank()
  editor.value = 'new'
}

function openEdit(item) {
  draft.value = { ...item }
  editor.value = item.id
}

async function save() {
  const body = {
    name: draft.value.name || '番茄',
    focus_minutes: Number(draft.value.focus_minutes),
    rest_minutes: Number(draft.value.rest_minutes),
    cycles: Number(draft.value.cycles),
    category: draft.value.category,
  }
  try {
    if (editor.value === 'new') await createFocusPreset(body)
    else await updateFocusPreset(editor.value, body)
    editor.value = null
    await load()
  } catch (error) {
    showToast(error.message || '没有保存')
  }
}

async function onSort() {
  try {
    const data = await reorderFocusPresets(items.value.map((item) => item.id))
    items.value = data.items || items.value
  } catch (error) {
    showToast(error.message || '顺序没有改成')
  }
}

async function removeChosen() {
  if (!chosen.value.length) return
  try {
    await deleteFocusPresets(chosen.value)
    chosen.value = []
    picking.value = false
    await load()
  } catch (error) {
    showToast(error.message || '没有删掉')
  }
}

function toggle(id) {
  chosen.value = chosen.value.includes(id) ? chosen.value.filter((item) => item !== id) : [...chosen.value, id]
}

function launch(item) {
  close()
  emit('start', item)
}

async function toggleRun() {
  givingUp.value = false
  const pausing = focusClock.status === 'running'
  if (pausing) stopNoise()
  else claimNoise()
  try {
    await focusCommand(pausing ? 'pause' : 'resume')
  } catch (error) {
    showToast(error.message || '这一轮没有改成')
  }
}

async function giveUp() {
  if (!givingUp.value) {
    givingUp.value = true
    return
  }
  givingUp.value = false
  stopNoise()
  try {
    await focusCommand('abandon', { record: true, interrupt: '自己停下' })
  } catch (error) {
    showToast(error.message || '没有放弃这一轮')
  }
}

function onKey(event) {
  if (event.key === 'Escape' && open.value) close()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <button type="button" class="launch" @click="show">专注控制台</button>

  <Teleport to="body">
    <div v-if="open" class="mask" role="presentation" @click="close">
      <section class="sheet" role="dialog" aria-modal="true" aria-labelledby="focus-console-title" @click.stop>
        <header class="top">
          <div>
            <h2 id="focus-console-title">专注控制台</h2>
            <p>选一轮，从这一颗开始。</p>
          </div>
          <div class="top-actions">
            <button type="button" @click="openNew">添加</button>
            <button type="button" @click="picking = !picking">{{ picking ? '取消' : '选择' }}</button>
            <button type="button" class="ghost" @click="close">关闭</button>
          </div>
        </header>

        <section class="now" aria-label="当前这一轮">
          <template v-if="active">
            <p class="now-time">{{ clock }}</p>
            <div class="now-copy">
              <p class="name">{{ focusClock.name }}</p>
              <p class="meta">{{ focusClock.phase === 'rest' ? '休息' : '专注' }} · {{ focusClock.cycle }}/{{ focusClock.cycles }}</p>
            </div>
            <button type="button" class="now-btn" @click="toggleRun">{{ focusClock.status === 'running' ? '暂停' : '继续' }}</button>
            <button type="button" class="now-stop" @click="giveUp">{{ givingUp ? '确认放弃' : '放弃' }}</button>
          </template>
          <p v-else class="now-idle">这一轮还没开始。从下面选一个番茄钟。</p>
        </section>

        <button v-if="picking" type="button" class="wipe" :disabled="!chosen.length" @click="removeChosen">删除所选</button>

        <p v-if="!items.length" class="empty">还没有番茄钟。先添加一轮。</p>

        <draggable v-else v-model="items" item-key="id" handle=".handle" tag="div" class="list" @end="onSort">
          <template #item="{ element }">
            <div class="row">
              <input v-if="picking" type="checkbox" :checked="chosen.includes(element.id)" @change="toggle(element.id)" />
              <button type="button" class="handle" title="拖动排序">⋮⋮</button>
              <p class="minutes">{{ String(element.focus_minutes).padStart(2, '0') }}:00</p>
              <div class="copy">
                <p class="name">{{ element.name }}</p>
                <p class="meta">休息 {{ element.rest_minutes }} 分钟 · 循环 {{ element.cycles }} 次 · {{ element.category }}</p>
              </div>
              <button type="button" class="edit" @click="openEdit(element)">编辑</button>
              <button type="button" class="go" @click="launch(element)">▶ 启动</button>
            </div>
          </template>
        </draggable>

        <form v-if="editor" class="editor" @submit.prevent="save">
          <h3>{{ editor === 'new' ? '添加番茄钟' : '编辑番茄钟' }}</h3>
          <label>名称<input v-model="draft.name" maxlength="40" /></label>
          <label>专注<input v-model.number="draft.focus_minutes" type="number" min="5" max="180" /> 分钟</label>
          <label>休息<input v-model.number="draft.rest_minutes" type="number" min="1" max="60" /> 分钟</label>
          <label>循环<input v-model.number="draft.cycles" type="number" min="1" max="12" /> 次</label>
          <label>
            分类
            <select v-model="draft.category">
              <option v-for="item in categories" :key="item">{{ item }}</option>
            </select>
          </label>
          <div class="actions">
            <button type="submit">保存</button>
            <button type="button" @click="editor = null">取消</button>
          </div>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.launch {
  display: flex;
  width: 100%;
  height: 44px;
  align-items: center;
  justify-content: center;
  margin: 0 0 12px;
  border: 0;
  border-radius: 0.375rem;
  background: #16201d;
  color: #fff6ea;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
}

.launch:focus-visible,
.sheet button:focus-visible,
.sheet input:focus-visible,
.sheet select:focus-visible {
  outline: 2px solid #c43228;
  outline-offset: 2px;
}

.mask {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  background: rgba(22, 24, 20, 0.46);
}

.sheet {
  width: min(720px, 100%);
  max-height: min(80vh, 760px);
  overflow: auto;
  padding: 28px 28px 24px;
  border-radius: 20px;
  background: #f6f1e8;
  color: #1c1915;
  animation: console-in 320ms cubic-bezier(0.2, 0, 0, 1);
}

.top,
.top-actions,
.actions,
.row {
  display: flex;
  align-items: center;
}

.top {
  justify-content: space-between;
  gap: 16px;
}

.top h2,
.editor h3,
.name,
.meta,
.empty {
  margin: 0;
}

.top h2 {
  font-size: 32px;
  line-height: 1;
  letter-spacing: -0.03em;
}

.top p,
.meta,
.empty {
  margin-top: 8px;
  font-size: 16px;
  line-height: 1.45;
}

.now {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 22px;
  padding: 16px;
  border-radius: 14px;
  background: #efe8dc;
}

.now-time,
.now-idle,
.now-copy .name,
.now-copy .meta {
  margin: 0;
}

.now-time {
  font-size: 40px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
  line-height: 1;
}

.now-copy {
  min-width: 0;
  flex: 1;
}

.now-idle {
  font-size: 16px;
  line-height: 1.45;
}

.now-btn,
.now-stop {
  min-height: 44px;
  padding: 0 16px;
  border-radius: 0.375rem;
  font-size: 15px;
  font-weight: 700;
}

.now-btn {
  background: #16201d;
  color: #fff6ea;
}

.now-stop {
  background: #c43228;
  color: #fff6ea;
}

.top-actions,
.actions {
  gap: 8px;
}

.sheet button,
.sheet input,
.sheet select {
  border: 0;
  border-radius: 10px;
  background: #e7e0d4;
  color: inherit;
  font: inherit;
  font-size: 14px;
  transition:
    transform 130ms cubic-bezier(0.2, 0, 0, 1),
    background-color 160ms ease,
    color 160ms ease;
}

.sheet button:active {
  transform: scale(0.97);
}

.sheet .now-btn,
.sheet .now-stop {
  min-height: 44px;
  padding: 0 16px;
  border-radius: 0.375rem;
  font-size: 15px;
  font-weight: 700;
}

.sheet .now-btn {
  background: #16201d;
  color: #fff6ea;
}

.sheet .now-stop {
  background: #c43228;
  color: #fff6ea;
}

.top-actions button,
.actions button,
.wipe,
.edit {
  min-height: 36px;
  padding: 0 12px;
}

.ghost {
  background: transparent;
}

.wipe {
  margin-top: 16px;
}

.wipe:disabled {
  opacity: 0.4;
}

.list {
  margin-top: 22px;
}

.row {
  gap: 12px;
  min-height: 84px;
  margin-top: 8px;
  padding: 12px 12px 12px 8px;
  border-radius: 14px;
  background: #f0eadd;
  transition:
    transform 180ms cubic-bezier(0.2, 0, 0, 1),
    background-color 180ms ease;
}

.row:nth-child(odd) {
  background: #e9e1d3;
}

.row:hover {
  transform: translateX(3px);
  background: #e5dccd;
}

.copy {
  min-width: 0;
  flex: 1;
}

.minutes {
  margin: 0;
  min-width: 4.2ch;
  font-size: 32px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
  line-height: 1;
}

.name {
  overflow: hidden;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.03em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}

.handle,
.edit {
  background: transparent;
}

.go {
  min-width: 112px;
  min-height: 48px;
  padding: 0 16px;
  background: #c43228;
  color: #fff6ea;
  font-size: 16px;
  font-weight: 700;
}

.editor {
  display: grid;
  gap: 10px;
  margin-top: 18px;
  padding: 16px;
  border-radius: 14px;
  background: #efe8dc;
  animation: editor-in 220ms cubic-bezier(0.2, 0, 0, 1);
}

.editor h3 {
  font-size: 18px;
}

.editor label {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 15px;
}

.editor input,
.editor select {
  min-height: 36px;
  padding: 0 8px;
  background: #f6f1e8;
}

@keyframes console-in {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes editor-in {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 640px) {
  .top,
  .row {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .go {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sheet,
  .editor {
    animation: none;
  }

  .sheet button,
  .sheet input,
  .sheet select,
  .row {
    transition: none;
  }

  .row:hover {
    transform: none;
  }
}
</style>
