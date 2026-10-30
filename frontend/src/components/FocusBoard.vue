<script setup>
import { onMounted, ref } from 'vue'
import draggable from 'vuedraggable'

import {
  createFocusPreset,
  deleteFocusPresets,
  getFocusPresets,
  reorderFocusPresets,
  updateFocusPreset,
} from '../api/client'
import { showToast } from '../toast'

const emit = defineEmits(['start'])

const items = ref([])
const picking = ref(false)
const chosen = ref([])
const editor = ref(null)
const draft = ref(blank())

const categories = ['学习', '工作', '生活']

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

onMounted(load)
</script>

<template>
  <section class="board">
    <div class="head">
      <h2>番茄钟</h2>
      <button type="button" @click="openNew">添加</button>
      <button type="button" @click="picking = !picking">{{ picking ? '取消' : '选择' }}</button>
    </div>
    <button v-if="picking" type="button" class="wipe" :disabled="!chosen.length" @click="removeChosen">删除所选</button>
    <draggable v-model="items" item-key="id" handle=".handle" tag="div" @end="onSort">
      <template #item="{ element }">
        <div class="row">
          <input v-if="picking" type="checkbox" :checked="chosen.includes(element.id)" @change="toggle(element.id)" />
          <button type="button" class="handle" title="拖动">⋮⋮</button>
          <button type="button" class="main" @click="emit('start', element)">
            <span>{{ element.name }}</span>
            <span>{{ element.focus_minutes }}:00</span>
          </button>
          <button type="button" @click="openEdit(element)">编辑</button>
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
</template>

<style scoped>
.board {
  margin: 12px 0 8px;
  color: #16201d;
}

.head,
.actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.head h2,
.editor h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}

.head h2 {
  margin-right: auto;
}

.board button,
.wipe {
  border: 0;
  background: transparent;
  color: #16201d;
  font: inherit;
  font-size: 13px;
}

.head button,
.wipe,
.actions button,
.editor {
  background: #fff;
}

.head button,
.wipe,
.actions button {
  padding: 4px 8px;
}

.wipe {
  margin-top: 8px;
}

.row {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-top: 6px;
}

.main {
  display: flex;
  flex: 1;
  justify-content: space-between;
  min-width: 0;
  padding: 6px 0;
  font-variant-numeric: tabular-nums;
  text-align: left;
}

.main span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.handle {
  cursor: grab;
  padding: 0 2px;
}

.editor {
  display: grid;
  gap: 8px;
  margin-top: 8px;
  padding: 10px;
}

.editor label {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.editor input,
.editor select {
  width: 72px;
  border: 0;
  background: #f4efe7;
  color: inherit;
  font: inherit;
}

.editor input:focus-visible,
.editor select:focus-visible,
.board button:focus-visible {
  outline: 2px solid #3f6f57;
  outline-offset: 2px;
}
</style>
