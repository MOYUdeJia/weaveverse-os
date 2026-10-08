<script setup>
import { computed, onMounted, ref } from 'vue'

import {
  createGroup,
  createNav,
  deleteGroup,
  deleteNav,
  getGroups,
  getHealth,
  getNav,
  lockGroup,
  lockNav,
  patchNav,
  pinNav,
  reorderGroups,
  reorderNav,
  updateGroup,
  updateNav,
} from './api/client'
import ConfirmDialog from './components/ConfirmDialog.vue'
import GroupBar from './components/GroupBar.vue'
import GroupEditDialog from './components/GroupEditDialog.vue'
import NavEditDialog from './components/NavEditDialog.vue'
import SidebarNav from './components/SidebarNav.vue'
import SplashScreen from './components/SplashScreen.vue'
import WorkspacePanel from './components/WorkspacePanel.vue'

const splashVisible = ref(true)
const groups = ref([])
const activeGroupId = ref(null)
const navItems = ref([])
const activeId = ref(null)
const showingOverview = ref(false)
const isLoading = ref(true)
const navLoading = ref(false)
const errorMessage = ref('')
const noticeMessage = ref('')
const dialogMode = ref('create')
const editingItem = ref(null)
const isDialogOpen = ref(false)
const groupDialogOpen = ref(false)
const editingGroup = ref(null)
const confirmOpen = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmBusy = ref(false)
let confirmAction = null
let navRequest = 0

const activeItem = computed(() => {
  return navItems.value.find((item) => item.id === activeId.value) ?? null
})

const activeGroup = computed(() => {
  return groups.value.find((group) => group.id === activeGroupId.value) ?? null
})

function replaceGroup(updated) {
  groups.value = groups.value.map((group) => (group.id === updated.id ? { ...group, ...updated } : group))
}

function applyNavItems(items, preferredId = null) {
  navItems.value = items
  if (showingOverview.value && preferredId == null) {
    return
  }
  if (preferredId != null && items.some((item) => item.id === preferredId)) {
    activeId.value = preferredId
    return
  }
  if (!items.some((item) => item.id === activeId.value)) {
    activeId.value = items[0]?.id ?? null
  }
}

async function selectGroup(groupId, preferredId = null, overview = false) {
  const requestId = ++navRequest
  activeGroupId.value = groupId
  navLoading.value = true
  errorMessage.value = ''
  try {
    const items = await getNav(groupId)
    if (requestId !== navRequest) {
      return
    }
    if (overview) {
      showingOverview.value = true
      navItems.value = items
      activeId.value = null
      return
    }
    showingOverview.value = false
    applyNavItems(items, preferredId)
  } catch (error) {
    if (requestId !== navRequest) {
      return
    }
    console.error('Failed to load group nav:', error)
    errorMessage.value = '这个分组的导航暂时没有加载出来。'
    navItems.value = []
    activeId.value = null
  } finally {
    if (requestId === navRequest) {
      navLoading.value = false
    }
  }
}

async function reloadGroups() {
  groups.value = await getGroups()
}

async function loadShellData() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    await getHealth()
    groups.value = await getGroups()
    const firstId = groups.value[0]?.id ?? null
    if (firstId == null) {
      navItems.value = []
      activeId.value = null
      return
    }
    await selectGroup(firstId, null, true)
  } catch (error) {
    console.error('Weaveverse startup request failed:', error)
    errorMessage.value = '后端暂时没有回应，请确认 Weaveverse 服务已经启动。'
  } finally {
    isLoading.value = false
  }
}

function openNav(id) {
  showingOverview.value = false
  activeId.value = id
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

function openCreateGroup() {
  editingGroup.value = null
  groupDialogOpen.value = true
}

function openEditGroup(group) {
  editingGroup.value = group
  groupDialogOpen.value = true
}

function askConfirm(title, message, action) {
  confirmTitle.value = title
  confirmMessage.value = message
  confirmAction = action
  confirmOpen.value = true
}

async function runConfirm() {
  if (!confirmAction || confirmBusy.value) {
    return
  }
  confirmBusy.value = true
  try {
    await confirmAction()
    confirmOpen.value = false
    confirmAction = null
  } catch (error) {
    console.error('Confirm action failed:', error)
    alert(error.message || '操作失败，请稍后再试。')
  } finally {
    confirmBusy.value = false
  }
}

function cancelConfirm() {
  if (confirmBusy.value) {
    return
  }
  confirmOpen.value = false
  confirmAction = null
}

async function saveNavItem(data, done) {
  try {
    noticeMessage.value = ''
    if (dialogMode.value === 'create') {
      const payload = { ...data }
      if (payload.group_id == null && activeGroupId.value != null) {
        payload.group_id = activeGroupId.value
      }
      const created = await createNav(payload)
      await reloadGroups()
      if (created.group_id !== activeGroupId.value) {
        await selectGroup(created.group_id, created.id)
      } else {
        showingOverview.value = false
        navItems.value = [...navItems.value, created]
        activeId.value = created.id
      }
      noticeMessage.value = '导航项已添加。'
    } else if (editingItem.value) {
      const updated = await updateNav(editingItem.value.id, data)
      navItems.value = navItems.value.map((item) => (item.id === updated.id ? { ...item, ...updated } : item))
      showingOverview.value = false
      activeId.value = updated.id
      noticeMessage.value = '导航项已更新。'
    }
    done?.(true)
    isDialogOpen.value = false
  } catch (error) {
    done?.(false)
    console.error('Failed to save nav item:', error)
    alert(error.message || '保存失败，请稍后再试。')
  }
}

function removeNavItem(item) {
  askConfirm('删除导航项', `确定删除「${item.title}」吗？`, async () => {
    noticeMessage.value = ''
    await deleteNav(item.id)
    const nextItems = navItems.value.filter((navItem) => navItem.id !== item.id)
    showingOverview.value = false
    applyNavItems(nextItems)
    await reloadGroups()
    noticeMessage.value = '导航项已删除。'
  })
}

async function persistNavOrder(ids) {
  const previous = navItems.value
  navItems.value = ids.map((id) => previous.find((item) => item.id === id)).filter(Boolean)
  try {
    const items = await reorderNav(ids)
    const keepOverview = showingOverview.value
    applyNavItems(items, keepOverview ? null : activeId.value)
    showingOverview.value = keepOverview
  } catch (error) {
    console.error('Failed to reorder nav:', error)
    navItems.value = previous
    alert(error.message || '排序失败')
  }
}

async function toggleLock(item) {
  try {
    const updated = await lockNav(item.id)
    navItems.value = navItems.value.map((navItem) => (navItem.id === updated.id ? { ...navItem, ...updated } : navItem))
  } catch (error) {
    console.error('Failed to lock nav:', error)
    alert(error.message || '锁定失败')
  }
}

async function toggleGroupLock(group) {
  try {
    const updated = await lockGroup(group.id)
    replaceGroup(updated)
  } catch (error) {
    console.error('Failed to lock group:', error)
    alert(error.message || '锁定失败')
  }
}

async function togglePin(item) {
  try {
    await pinNav(item.id)
    const items = await getNav(activeGroupId.value)
    const keepOverview = showingOverview.value
    navItems.value = items
    if (!keepOverview) {
      applyNavItems(items, item.id)
    }
  } catch (error) {
    console.error('Failed to pin nav:', error)
    alert(error.message || '置顶失败')
  }
}

async function moveNavItem(item, groupId) {
  try {
    await patchNav(item.id, { group_id: groupId })
    navItems.value = navItems.value.filter((navItem) => navItem.id !== item.id)
    if (!showingOverview.value && activeId.value === item.id) {
      activeId.value = navItems.value[0]?.id ?? null
      showingOverview.value = activeId.value == null
    }
    await reloadGroups()
    noticeMessage.value = '导航项已移动。'
  } catch (error) {
    console.error('Failed to move nav:', error)
    alert(error.message || '移动失败')
  }
}

async function saveGroup(data, done) {
  try {
    if (!editingGroup.value) {
      const created = await createGroup({
        name: data.name,
        icon: data.icon,
        description: data.description,
      })
      await reloadGroups()
      await selectGroup(created.id, null, true)
      noticeMessage.value = '分组已创建。'
    } else {
      const payload = {
        icon: data.icon,
        description: data.description,
      }
      if (!editingGroup.value.is_system) {
        payload.name = data.name
      }
      const updated = await updateGroup(editingGroup.value.id, payload)
      replaceGroup(updated)
      noticeMessage.value = '分组已更新。'
    }
    done?.(true)
    groupDialogOpen.value = false
  } catch (error) {
    done?.(false)
    console.error('Failed to save group:', error)
    alert(error.message || '保存分组失败')
  }
}

function removeGroup(group) {
  if (group.is_system) {
    return
  }
  askConfirm('删除分组', `确定删除「${group.name}」吗？该分组有 ${group.item_count} 个导航项。`, async () => {
    await deleteGroup(group.id)
    groups.value = groups.value.filter((item) => item.id !== group.id)
    if (activeGroupId.value === group.id) {
      const next = groups.value[0]
      if (next) {
        await selectGroup(next.id, null, true)
      } else {
        navItems.value = []
        activeId.value = null
        showingOverview.value = false
      }
    }
    noticeMessage.value = '分组已删除。'
  })
}

async function persistGroupOrder(ids) {
  const previous = groups.value
  groups.value = ids.map((id) => previous.find((group) => group.id === id)).filter(Boolean)
  try {
    groups.value = await reorderGroups(ids)
  } catch (error) {
    console.error('Failed to reorder groups:', error)
    groups.value = previous
    alert(error.message || '分组排序失败')
  }
}

async function renameGroup(name, done) {
  try {
    const updated = await updateGroup(activeGroupId.value, { name })
    replaceGroup(updated)
    done?.(true)
  } catch (error) {
    done?.(false)
    console.error('Failed to rename group:', error)
    alert(error.message || '改名失败')
  }
}

async function describeGroup(description, done) {
  try {
    const updated = await updateGroup(activeGroupId.value, { description })
    replaceGroup(updated)
    done?.(true)
  } catch (error) {
    done?.(false)
    console.error('Failed to update description:', error)
    alert(error.message || '简介保存失败')
  }
}

onMounted(loadShellData)
</script>

<template>
  <main class="relative min-h-screen overflow-hidden bg-dawn text-ink">
    <SplashScreen v-if="splashVisible" @finished="splashVisible = false" />

    <section class="flex min-h-screen">
      <GroupBar
        :groups="groups"
        :active-id="activeGroupId"
        @select="selectGroup($event, null, true)"
        @create="openCreateGroup"
        @edit="openEditGroup"
        @remove="removeGroup"
        @lock="toggleGroupLock"
        @reorder="persistGroupOrder"
      />
      <SidebarNav
        :items="navItems"
        :groups="groups"
        :group-id="activeGroupId"
        :group-name="activeGroup?.name || ''"
        :active-id="showingOverview ? null : activeId"
        :loading="isLoading || navLoading"
        :error-message="errorMessage"
        @select="openNav"
        @create="openCreateDialog"
        @edit="openEditDialog"
        @delete="removeNavItem"
        @reorder="persistNavOrder"
        @pin="togglePin"
        @lock="toggleLock"
        @move="moveNavItem"
        @open-overview="selectGroup(activeGroupId, null, true)"
      />
      <WorkspacePanel
        :item="activeItem"
        :loading="isLoading"
        :error-message="errorMessage"
        :empty="!isLoading && !errorMessage && !showingOverview && navItems.length === 0"
        :notice-message="noticeMessage"
        :overview-group="showingOverview ? activeGroup : null"
        :overview-items="navItems"
        @open-nav="openNav"
        @rename-group="renameGroup"
        @describe-group="describeGroup"
      />
    </section>

    <NavEditDialog
      :open="isDialogOpen"
      :mode="dialogMode"
      :item="editingItem"
      :nav-items="navItems"
      @close="isDialogOpen = false"
      @save="saveNavItem"
    />
    <GroupEditDialog
      :open="groupDialogOpen"
      :group="editingGroup"
      @close="groupDialogOpen = false"
      @save="saveGroup"
    />
    <ConfirmDialog
      :open="confirmOpen"
      :title="confirmTitle"
      :message="confirmMessage"
      :busy="confirmBusy"
      @cancel="cancelConfirm"
      @confirm="runConfirm"
    />
  </main>
</template>
