<script setup>
defineProps({
  items: {
    type: Array,
    required: true,
  },
  activeId: {
    type: String,
    default: '',
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

defineEmits(['select'])
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
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="flex h-12 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-medium transition"
        :class="
          item.id === activeId
            ? 'bg-moss text-white shadow-sm'
            : 'text-ink/72 hover:bg-white/70 hover:text-ink'
        "
        @click="$emit('select', item.id)"
      >
        <span class="grid h-8 w-8 place-items-center rounded-md bg-white/20 text-lg">{{ item.icon }}</span>
        <span>{{ item.title }}</span>
      </button>
    </nav>

    <div class="mt-auto border-t border-black/10 pt-5 text-xs leading-5 text-ink/55">
      M0 local shell<br />
      FastAPI + Vue + pywebview
    </div>
  </aside>
</template>
