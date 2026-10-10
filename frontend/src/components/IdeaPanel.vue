<script setup>
import { computed, ref } from 'vue'

import { autotagIdea, createIdea, deleteIdea, listIdeas, summarizeIdea, updateIdea } from '../api/client'
import NavIcon from './NavIcon.vue'
import { showToast } from '../toast'

defineProps({
  title: { type: String, default: 'IDEA 栏' },
  icon: { type: String, default: '💡' },
})

const ideas = ref([])
const query = ref('')
const tagFilter = ref('')
const editor = ref(null)
const summary = ref('')

const tags = computed(() => {
  const found = []
  ideas.value.forEach((idea) => {
    ;(idea.tags || []).forEach((tag) => {
      if (!found.includes(tag)) {
        found.push(tag)
      }
    })
  })
  return found
})

const shown = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return ideas.value.filter((idea) => {
    if (tagFilter.value && !(idea.tags || []).includes(tagFilter.value)) {
      return false
    }
    if (!needle) {
      return true
    }
    return `${idea.title} ${idea.content}`.toLowerCase().includes(needle)
  })
})

async function load() {
  ideas.value = await listIdeas()
}

function tagList(raw) {
  return raw
    .split(/[\s,，]+/)
    .map((tag) => tag.replace(/^#/, '').trim())
    .filter(Boolean)
}

async function saveEditor() {
  if (!editor.value) {
    return
  }
  const payload = {
    title: editor.value.title.trim(),
    content: editor.value.content.trim(),
    tags: tagList(editor.value.tags),
  }
  if (!payload.title && !payload.content) {
    return
  }
  if (editor.value.id) {
    await updateIdea(editor.value.id, payload)
  } else {
    await createIdea(payload)
  }
  editor.value = null
  await load()
}

function edit(idea) {
  editor.value = { id: idea.id, title: idea.title, content: idea.content, tags: (idea.tags || []).join(' ') }
}

async function remove(idea) {
  if (!window.confirm('删除这个点子？')) {
    return
  }
  await deleteIdea(idea.id)
  await load()
}

async function summarize(idea) {
  try {
    const result = await summarizeIdea(idea.id)
    summary.value = result.summary || ''
    showToast('已总结')
  } catch (error) {
    showToast(error.message || '总结失败')
  }
}

async function autotag(idea) {
  try {
    await autotagIdea(idea.id)
    await load()
    showToast('已贴上标签')
  } catch (error) {
    showToast(error.message || '贴标签失败')
  }
}

load().catch((error) => showToast(error.message || '无法加载点子'))
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-y-auto px-8 py-8">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div class="flex items-center gap-4">
        <NavIcon :icon="icon" box="h-14 w-14 bg-dawn text-2xl shadow-sm" />
        <div>
          <p class="text-sm font-semibold uppercase tracking-[0.28em] text-aurora">Ideas</p>
          <h2 class="mt-1 text-4xl font-semibold text-ink">{{ title }}</h2>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <input v-model="query" class="wv-surface h-10 min-w-0 flex-1 rounded border border-black/10 px-3 text-sm outline-none" placeholder="搜索点子" />
        <button type="button" class="h-10 rounded bg-moss px-4 text-sm font-semibold text-white" @click="editor = { id: null, title: '', content: '', tags: '' }">新建点子</button>
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="bg-transparent text-xs" :class="tagFilter ? 'text-ink/50' : 'font-semibold text-moss'" @click="tagFilter = ''">全部</button>
        <button
          v-for="tag in tags"
          :key="tag"
          type="button"
          class="text-xs"
          :class="tagFilter === tag ? 'font-semibold text-moss' : 'text-ink/60'"
          @click="tagFilter = tagFilter === tag ? '' : tag"
        >
          #{{ tag }}
        </button>
      </div>
      <p v-if="summary" class="wv-surface rounded-md px-4 py-3 text-sm">{{ summary }}</p>
      <p v-if="!shown.length" class="text-sm text-ink/50">还没有点子</p>
      <article v-for="idea in shown" :key="idea.id" class="wv-surface rounded-md p-4 shadow-sm">
        <h3 v-if="idea.title" class="text-base font-semibold">{{ idea.title }}</h3>
        <p class="mt-1 whitespace-pre-wrap text-sm leading-6">{{ idea.content }}</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <button v-for="tag in idea.tags" :key="tag" type="button" class="text-xs text-moss" @click="tagFilter = tag">#{{ tag }}</button>
        </div>
        <div class="mt-3 flex flex-wrap items-center gap-3 text-xs text-ink/45">
          <span>{{ String(idea.updated_at || '').slice(0, 16).replace('T', ' ') }}</span>
          <button type="button" class="text-ink/70" @click="edit(idea)">编辑</button>
          <button type="button" class="text-ink/70" @click="summarize(idea)">总结</button>
          <button type="button" class="text-ink/70" @click="autotag(idea)">自动贴标签</button>
          <button type="button" class="text-ember" @click="remove(idea)">删除</button>
        </div>
      </article>
    </div>
    <div v-if="editor" class="fixed inset-0 z-50 grid place-items-center bg-black/40 px-4" @click.self="editor = null">
      <form class="wv-surface w-full max-w-lg rounded-md p-4 shadow-2xl" @submit.prevent="saveEditor">
        <p class="text-sm font-medium">{{ editor.id ? '编辑点子' : '新建点子' }}</p>
        <input v-model="editor.title" class="wv-chip mt-3 h-10 w-full rounded px-3 text-sm outline-none" maxlength="80" placeholder="标题，可空" />
        <textarea v-model="editor.content" rows="5" class="wv-chip mt-2 w-full rounded px-3 py-2 text-sm outline-none" placeholder="内容" />
        <input v-model="editor.tags" class="wv-chip mt-2 h-10 w-full rounded px-3 text-sm outline-none" placeholder="标签，用空格分开" />
        <div class="mt-3 flex justify-end gap-2">
          <button type="button" class="h-8 px-3 text-xs text-ink/55" @click="editor = null">取消</button>
          <button type="submit" class="h-8 rounded bg-moss px-3 text-xs text-white">保存</button>
        </div>
      </form>
    </div>
  </div>
</template>
