<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'

import { createBlock, deleteBlock, getNavItem, updateBlock } from '../api/client'
import { blockComponents, blockOptions, defaultBlockContent } from '../blocks/registry.js'
import BookmarksPage from '../focus/BookmarksPage.vue'
import PlainPage from '../focus/PlainPage.vue'
import { focusPageByType } from '../specialAdds/registry.js'
import BookshelfPanel from './BookshelfPanel.vue'
import GroupOverview from './GroupOverview.vue'
import NavIcon from './NavIcon.vue'

const focusViews = {
  doc: defineAsyncComponent(() => import('../focus/DocPage.vue')),
  plain: PlainPage,
  inbox: PlainPage,
  bookmarks: BookmarksPage,
  canvas: defineAsyncComponent(() => import('../focus/CanvasPage.vue')),
}

const props = defineProps({
  item: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  errorMessage: {
    type: String,
    default: '',
  },
  empty: {
    type: Boolean,
    default: false,
  },
  noticeMessage: {
    type: String,
    default: '',
  },
  overviewGroup: {
    type: Object,
    default: null,
  },
  overviewItems: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['open-nav', 'rename-group', 'describe-group', 'search-tag'])

const page = ref(null)
const pageLoading = ref(false)
const pageError = ref('')
const pickerOpen = ref(false)

const blocks = computed(() => page.value?.blocks ?? [])
const focusSpec = computed(() => focusPageByType(page.value?.page_type || props.item?.page_type))
const focusView = computed(() => focusViews[focusSpec.value?.pageType] || null)
const focusBlock = computed(() => {
  if (!focusSpec.value) {
    return null
  }
  return blocks.value[0] || null
})

watch(
  () => props.item?.id,
  async (id) => {
    page.value = null
    pageError.value = ''
    if (!id) {
      return
    }
    pageLoading.value = true
    try {
      page.value = await getNavItem(id)
    } catch (error) {
      console.error('Failed to load page:', error)
      pageError.value = error.message || '无法加载页面内容'
    } finally {
      pageLoading.value = false
    }
  },
  { immediate: true },
)

// 按区块类型从注册表取出组件。
// Resolve a Vue component from the block type registry.
function componentFor(block) {
  return blockComponents[block.block_type] || null
}

async function saveBlock(block, content) {
  return saveBlockById(block.id, content)
}

async function saveBlockById(blockId, content) {
  try {
    const updated = await updateBlock(blockId, { content })
    if (!page.value) {
      return
    }
    page.value = {
      ...page.value,
      blocks: page.value.blocks.map((item) => (item.id === updated.id ? updated : item)),
    }
  } catch (error) {
    console.error('Failed to save block:', error)
    alert(error.message || '保存区块失败')
  }
}

async function removeBlock(block) {
  try {
    await deleteBlock(block.id)
    page.value = {
      ...page.value,
      blocks: page.value.blocks.filter((item) => item.id !== block.id),
    }
  } catch (error) {
    console.error('Failed to delete block:', error)
    alert(error.message || '删除区块失败')
  }
}

async function addBlock(blockType) {
  pickerOpen.value = false
  if (!page.value) {
    return
  }
  try {
    const created = await createBlock(page.value.id, {
      block_type: blockType,
      content: defaultBlockContent[blockType] || {},
    })
    page.value = {
      ...page.value,
      blocks: [...page.value.blocks, created],
    }
  } catch (error) {
    console.error('Failed to add block:', error)
    alert(error.message || '添加区块失败')
  }
}
</script>

<template>
  <section class="wv-work relative flex h-screen min-h-0 min-w-0 flex-1 flex-col">
    <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-moss via-ember to-aurora" />

    <div v-if="overviewGroup && !loading && !errorMessage" class="min-h-0 flex-1 overflow-y-auto px-10 py-12">
      <GroupOverview
        :group="overviewGroup"
        :items="overviewItems"
        @open="emit('open-nav', $event)"
        @rename="(name, done) => emit('rename-group', name, done)"
        @describe="(text, done) => emit('describe-group', text, done)"
      />
    </div>

    <BookshelfPanel
      v-else-if="item && item.page_type === 'bookshelf' && !loading && !errorMessage && !empty"
      :title="item.title"
      :icon="item.icon"
      :notice-message="noticeMessage"
    />

    <div
      v-else-if="item && focusView && !loading && !errorMessage && !empty"
      class="flex min-h-0 flex-1 flex-col"
    >
      <header class="flex shrink-0 items-center gap-3 border-b border-black/10 px-6 py-3">
        <NavIcon :icon="item.icon" box="h-9 w-9 bg-dawn text-base" />
        <div class="min-w-0">
          <h2 class="truncate text-lg font-semibold text-ink">{{ item.title }}</h2>
          <div v-if="item.tags?.length" class="mt-1 flex flex-wrap gap-1">
            <button
              v-for="tag in item.tags"
              :key="tag"
              type="button"
              class="wv-tag text-xs"
              @click="emit('search-tag', `#${tag}`)"
            >
              #{{ tag }}
            </button>
          </div>
          <p v-if="noticeMessage" class="truncate text-xs text-moss">{{ noticeMessage }}</p>
        </div>
      </header>
      <div class="min-h-0 flex-1" :class="focusSpec?.pageType === 'canvas' ? 'overflow-hidden' : 'overflow-y-auto'">
        <p v-if="pageLoading" class="px-6 py-8 text-sm text-ink/60">正在加载...</p>
        <p v-else-if="pageError" class="px-6 py-8 text-sm text-ember">{{ pageError }}</p>
        <p v-else-if="!focusBlock" class="px-6 py-8 text-sm text-ink/60">这块专用页缺少内容。</p>
        <component
          :is="focusView"
          v-else
          class="h-full"
          :block="focusBlock"
          :inbox="item.page_type === 'inbox'"
          @save="saveBlockById($event.blockId, $event.content)"
        />
      </div>
    </div>

    <div v-else class="min-h-0 flex-1 overflow-y-auto px-8 py-8">
      <div class="mx-auto w-full max-w-3xl">
        <p class="text-sm font-semibold uppercase tracking-[0.28em] text-aurora">Workspace</p>
        <div v-if="noticeMessage" class="mt-4 rounded-md border border-moss/25 bg-moss/10 px-4 py-3 text-sm text-moss">
          {{ noticeMessage }}
        </div>

        <h2 v-if="loading" class="mt-4 text-4xl font-semibold text-ink">正在唤醒工作区...</h2>
        <h2 v-else-if="errorMessage" class="mt-4 text-4xl font-semibold text-ink">工作区等待后端连接</h2>

        <template v-else-if="empty">
          <h2 class="mt-4 text-4xl font-semibold text-ink">暂无导航项，点击 + 添加</h2>
          <p class="mt-6 max-w-2xl text-base leading-8 text-ink/65">选择一个页面类型后，工作区会按区块渲染内容。</p>
        </template>

        <template v-else-if="item">
          <div class="mt-5 flex items-center gap-4">
            <NavIcon :icon="item.icon" box="h-16 w-16 bg-dawn text-2xl shadow-sm" />
            <div>
              <h2 class="text-4xl font-semibold text-ink">{{ item.title }}</h2>
              <p class="mt-1 text-sm text-ink/50">{{ page?.page_type || item.page_type || 'markdown' }}</p>
            </div>
          </div>

          <p v-if="pageLoading" class="mt-8 text-sm text-ink/60">正在加载区块...</p>
          <p v-else-if="pageError" class="mt-8 text-sm text-ember">{{ pageError }}</p>

          <div v-else class="mt-6 space-y-2">
            <template v-for="block in blocks" :key="block.id">
              <component
                :is="componentFor(block)"
                v-if="componentFor(block)"
                :block="block"
                @save="saveBlock(block, $event)"
                @delete="removeBlock(block)"
              />
              <article v-else class="rounded-md border border-black/10 bg-white/80 p-4 text-sm text-ink/60">
                未知区块类型：{{ block.block_type }}
              </article>
            </template>

            <button
              v-if="!focusSpec"
              type="button"
              class="h-9 w-full rounded-md border border-dashed border-moss/40 text-sm font-medium text-moss hover:bg-moss/10"
              @click="pickerOpen = true"
            >
              + 添加区块
            </button>
          </div>
        </template>

        <h2 v-else class="mt-4 text-4xl font-semibold text-ink">请选择一个工作区</h2>
      </div>
    </div>

    <div v-if="pickerOpen" class="fixed inset-0 z-30 grid place-items-center bg-black/40 px-4" @click.self="pickerOpen = false">
      <div class="w-full max-w-sm rounded-md bg-[#fcfaf5] p-5 shadow-2xl">
        <h3 class="text-lg font-semibold text-ink">选择区块类型</h3>
        <div class="mt-4 grid grid-cols-2 gap-2">
          <button
            v-for="option in blockOptions"
            :key="option.type"
            type="button"
            class="h-11 rounded-md bg-white text-sm font-medium text-ink shadow-sm hover:bg-moss hover:text-white"
            @click="addBlock(option.type)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
