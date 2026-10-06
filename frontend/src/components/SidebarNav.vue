<script setup>
defineProps({
  items: {
    type: Array,
    required: true,
  },
  activeId: {
    type: Number,
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
})

defineEmits(['select', 'create', 'edit', 'delete'])
</script>

<template>
  <aside class="flex w-72 shrink-0 flex-col border-r border-black/10 bg-[#f8f5ee]/88 px-5 py-6">
    <div class="mb-8">
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-moss">Weaveverse</p>
      <h1 class="mt-2 text-2xl font-semibold text-ink">个人宇宙</h1>
    </div>

    <div v-if="loading" class="rounded-md border border-black/10 bg-white/65 px-4 py-3 text-sm text-ink/70">
      正在加载导航...
    </div>

    <div v-else-if="errorMessage" class="rounded-md border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ink">
      {{ errorMessage }}
    </div>

    <nav v-else class="space-y-2">
      <div
        v-for="item in items"
        :key="item.id"
        class="group flex h-12 w-full items-center gap-2 rounded-md px-3 text-sm font-medium transition"
        :class="
          item.id === activeId
            ? 'bg-moss text-white shadow-sm'
            : 'text-ink/72 hover:bg-white/70 hover:text-ink'
        "
      >
        <button type="button" class="flex min-w-0 flex-1 items-center gap-3 text-left" @click="$emit('select', item.id)">
          <span class="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-white/20 text-lg">{{ item.icon }}</span>
          <span class="truncate">{{ item.title }}</span>
        </button>
        <div class="flex shrink-0 gap-1 opacity-0 transition group-hover:opacity-100">
          <button
            type="button"
            class="grid h-8 w-8 place-items-center rounded-md hover:bg-white/25"
            title="编辑"
            @click.stop="$emit('edit', item)"
          >
            ✏️
          </button>
          <button
            type="button"
            class="grid h-8 w-8 place-items-center rounded-md hover:bg-white/25"
            title="删除"
            @click.stop="$emit('delete', item)"
          >
            🗑️
          </button>
        </div>
      </div>
    </nav>

    <div class="mt-auto border-t border-black/10 pt-5">
      <button
        type="button"
        class="mb-5 flex h-11 w-full items-center justify-center gap-2 rounded-md bg-ink text-sm font-semibold text-white transition hover:bg-moss"
        @click="$emit('create')"
      >
        <span class="text-lg">+</span>
        <span>添加</span>
      </button>
      <div class="text-xs leading-5 text-ink/55">
        M1 local data<br />
        SQLite + Alembic
      </div>
    </div>
  </aside>
</template>
