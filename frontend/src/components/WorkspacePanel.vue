<script setup>
defineProps({
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
})
</script>

<template>
  <section class="relative flex min-w-0 flex-1 flex-col bg-[#fcfaf5]">
    <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-moss via-ember to-aurora" />

    <div class="flex flex-1 items-center justify-center px-10 py-12">
      <div class="w-full max-w-3xl">
        <p class="text-sm font-semibold uppercase tracking-[0.28em] text-aurora">Workspace</p>

        <h2 v-if="loading" class="mt-4 text-4xl font-semibold text-ink">正在唤醒工作区...</h2>

        <h2 v-else-if="errorMessage" class="mt-4 text-4xl font-semibold text-ink">工作区等待后端连接</h2>

        <template v-else-if="item">
          <div class="mt-5 flex items-center gap-4">
            <span class="grid h-16 w-16 place-items-center rounded-md bg-dawn text-4xl shadow-sm">
              {{ item.icon }}
            </span>
            <h2 class="text-4xl font-semibold text-ink">这里是 {{ item.title }} 的工作区</h2>
          </div>
          <p class="mt-6 max-w-2xl text-base leading-8 text-ink/65">
            M0 只负责把桌面外壳、开屏仪式、导航数据和工作区切换搭好。后续每一个维度都可以在这里长出自己的页面系统。
          </p>
        </template>

        <h2 v-else class="mt-4 text-4xl font-semibold text-ink">请选择一个工作区</h2>
      </div>
    </div>
  </section>
</template>
