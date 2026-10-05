<script setup>
import { computed, onMounted, ref } from 'vue'

import { getHealth, getNav } from './api/client'
import SidebarNav from './components/SidebarNav.vue'
import SplashScreen from './components/SplashScreen.vue'
import WorkspacePanel from './components/WorkspacePanel.vue'

const splashVisible = ref(true)
const navItems = ref([])
const activeId = ref('')
const isLoading = ref(true)
const errorMessage = ref('')

const activeItem = computed(() => {
  return navItems.value.find((item) => item.id === activeId.value) ?? null
})

async function loadShellData() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    await getHealth()
    const items = await getNav()
    navItems.value = items
    activeId.value = items[0]?.id ?? ''
  } catch (error) {
    console.error('Weaveverse startup request failed:', error)
    errorMessage.value = '后端暂时没有回应，请确认 Weaveverse 服务已经启动。'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadShellData)
</script>

<template>
  <main class="relative min-h-screen overflow-hidden bg-dawn text-ink">
    <SplashScreen v-if="splashVisible" @finished="splashVisible = false" />

    <section class="flex min-h-screen">
      <SidebarNav
        :items="navItems"
        :active-id="activeId"
        :loading="isLoading"
        :error-message="errorMessage"
        @select="activeId = $event"
      />
      <WorkspacePanel :item="activeItem" :loading="isLoading" :error-message="errorMessage" />
    </section>
  </main>
</template>
