<script setup>
const emit = defineEmits(['close'])
</script>

<template>
  <div class="fixed inset-0 z-[75] grid place-items-center bg-black/45 px-4" @click.self="emit('close')">
    <article class="max-h-[84vh] w-full max-w-lg overflow-y-auto rounded-md bg-[#fcfaf5] p-6 shadow-2xl">
      <h2 class="text-xl font-semibold text-ink">Weaveverse 怎么用</h2>
      <div class="mt-4 space-y-3 text-sm leading-7 text-ink/80">
        <p><strong>积木页</strong>用一块块内容搭起来，比如待办、画廊、Markdown。空白页和模板都从这里进。</p>
        <p><strong>专用页</strong>整页只有一种内容：长文、笔记、网址集、白板。专页可以加 <span class="wv-tag">#标签</span>，在搜索的「专页」里跨页找到。</p>
        <p><strong>系统页</strong>全局只有一个，比如书架。创建后会放进系统分组。系统分组永远排在分组栏第一位。</p>
        <p>分组从左侧栏新建。悬停展开；外观里可以改成覆盖在内容上面。</p>
        <p>快捷键：Ctrl+K 搜索页面名，Ctrl+Shift+N 速记，长文里 Ctrl+点击打开链接。</p>
      </div>
      <div class="mt-6 flex justify-end">
        <button type="button" class="h-9 rounded bg-ink px-4 text-sm text-white" @click="emit('close')">知道了</button>
      </div>
    </article>
  </div>
</template>
