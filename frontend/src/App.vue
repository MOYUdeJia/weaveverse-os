<script setup>
import { computed, onMounted, ref } from 'vue'

import { createNav, deleteNav, getHealth, getNav, updateNav } from './api/client'
import NavEditDialog from './components/NavEditDialog.vue'
import SidebarNav from './components/SidebarNav.vue'
import SplashScreen from './components/SplashScreen.vue'
import WorkspacePanel from './components/WorkspacePanel.vue'

const splashVisible = ref(true)
const navItems = ref([])
const activeId = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')
const noticeMessage = ref('')
const dialogMode = ref('create')
const editingItem = ref(null)
const isDialogOpen = ref(false)

const activeItem = computed(() => {
  return navItems.value.find((item) => item.id === activeId.value) ?? null
})

function setNavItems(items) {
  navItems.value = items
  if (!items.some((item) => item.id === activeId.value)) {
    activeId.value = items[0]?.id ?? null
  }
}

async function loadShellData() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    await getHealth()
    const items = await getNav()
    setNavItems(items)
  } catch (error) {
    console.error('Weaveverse startup request failed:', error)
    errorMessage.value = '后端暂时没有回应，请确认 Weaveverse 服务已经启动。'
  } finally {
    isLoading.value = false
  }
}

function openCreateDialog() {
  dialogMode.value = 'create'
  editingItem.value = null
  isDialogOpen.value = true
}

function openEditDialog(item) {
  dialogMode.value = 'edit'
  editingItem.value = item
  isDialogOpen.value = true
}

async function saveNavItem(data) {
  try {
    noticeMessage.value = ''
    if (dialogMode.value === 'create') {
      const created = await createNav(data)
      navItems.value = [...navItems.value, created]
      activeId.value = created.id
      noticeMessage.value = '导航项已添加。'
    } else if (editingItem.value) {
      const updated = await updateNav(editingItem.value.id, data)
      navItems.value = navItems.value.map((item) => (item.id === updated.id ? updated : item))
      activeId.value = updated.id
      noticeMessage.value = '导航项已更新。'
    }
    isDialogOpen.value = false
  } catch (error) {
    console.error('Failed to save nav item:', error)
    alert(error.message || '保存失败，请稍后再试。')
  }
}

async function removeNavItem(item) {
  const confirmed = window.confirm(`确定删除「${item.title}」吗？`)
  if (!confirmed) {
    return
  }

  try {
    noticeMessage.value = ''
    await deleteNav(item.id)
    const nextItems = navItems.value.filter((navItem) => navItem.id !== item.id)
    setNavItems(nextItems)
    noticeMessage.value = '导航项已删除。'
  } catch (error) {
    console.error('Failed to delete nav item:', error)
    alert(error.message || '删除失败，请稍后再试。')
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
        @create="openCreateDialog"
        @edit="openEditDialog"
        @delete="removeNavItem"
      />
      <WorkspacePanel
        :item="activeItem"
        :loading="isLoading"
        :error-message="errorMessage"
        :empty="!isLoading && !errorMessage && navItems.length === 0"
        :notice-message="noticeMessage"
      />
    </section>

    <NavEditDialog
      :open="isDialogOpen"
      :mode="dialogMode"
      :item="editingItem"
      @close="isDialogOpen = false"
      @save="saveNavItem"
    />
  </main>
</template>
