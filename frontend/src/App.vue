<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { assetFileUrl, backgroundUrl, createGroup, createNav, deleteGroup, deleteNav, getAppearance, getGroups, getHealth, getNav, lockGroup, lockNav, packFileUrl, patchNav, pinNav, reorderGroups, reorderNav, updateAppearance, updateGroup, updateNav, vaultEntryCount } from './api/client'
import ConfirmDialog from './components/ConfirmDialog.vue'
import GroupBar from './components/GroupBar.vue'
import GroupEditDialog from './components/GroupEditDialog.vue'
import NavEditDialog from './components/NavEditDialog.vue'
import AppearanceDialog from './components/AppearanceDialog.vue'
import GuideDialog from './components/GuideDialog.vue'
import MusicDock from './components/MusicDock.vue'
import SidebarNav from './components/SidebarNav.vue'
import SearchDialog from './components/SearchDialog.vue'
import QuickNoteDialog from './components/QuickNoteDialog.vue'
import SplashScreen from './components/SplashScreen.vue'
import ChatPanel from './components/ChatPanel.vue'
import WorkspacePanel from './components/WorkspacePanel.vue'
import { showToast, toastText } from './toast'

const splashVisible = ref(true)
const splashArmed = ref(false)
const shellReady = ref(false)
const guideOffered = ref(false)
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
const searchOpen = ref(false)
const searchQuery = ref('')
const searchTab = ref('all')
const noteOpen = ref(false)
const noteRevision = ref(0)
const appearanceOpen = ref(false)
const orbMoving = ref(false)
const chatOpen = ref(false)
const guideOpen = ref(false)
const appearance = ref({
  theme: 'warm',
  bar: 'push',
  low_power: false,
  bg_opacity: 0.85,
  hide_guide: false,
  splash_mode: 'default',
  splash_file: '',
  splash_owner: '',
  splash_caption: '正在编织你的宇宙',
  splash_duration: 2,
  splash_loop: true,
  active_pack: '',
  pack_background_kind: '',
  pack_background: '',
  pack_caption: '',
  decorations: [],
  startup_sound: '',
  packs: [],
  custom_themes: [],
  global_image: '',
  global_video: '',
  player: 'corner',
  player_hidden: false,
  groups: {},
})
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
    applyAppearance(await getAppearance())
    try {
      if (localStorage.getItem('wv.guide.seen') === '1' && !appearance.value.hide_guide) {
        applyAppearance(await updateAppearance({ hide_guide: true }))
        localStorage.removeItem('wv.guide.seen')
      }
    } catch {
      // 旧版 localStorage 迁移失败时仍按 appearance.json 决定。
    }
    splashArmed.value = true
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
    splashArmed.value = true
  } finally {
    isLoading.value = false
    shellReady.value = true
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

async function removeNavItem(item) {
  let title = '删除导航项'
  let message = `确定删除「${item.title}」吗？`
  if (item.page_type === 'password_vault') {
    let count = 0
    try {
      count = (await vaultEntryCount()).count || 0
    } catch {
      count = 0
    }
    title = '删除密码管理器'
    message = `将删除所有 ${count} 条密码，不可恢复`
  }
  askConfirm(title, message, async () => {
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

async function receiveNav(navId, groupId) {
  const item = navItems.value.find((navItem) => navItem.id === navId)
  if (!item) {
    return
  }
  await moveNavItem(item, groupId)
}

async function hideOrb() {
  try {
    applyAppearance(await updateAppearance({ player_hidden: true }))
    showToast('悬浮球已隐藏，可在设置→外观中重新显示。', 3600)
  } catch (error) {
    showToast(error.message || '没有隐藏')
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

onMounted(() => {
  loadShellData()
  window.addEventListener('keydown', onGlobalKey)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKey)
})

function onGlobalKey(event) {
  const key = event.key.toLowerCase()
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && key === 'n') {
    event.preventDefault()
    searchOpen.value = false
    noteOpen.value = true
    return
  }
  if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey && key === 'k') {
    event.preventDefault()
    noteOpen.value = false
    openSearch()
    return
  }
  if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey && key === 'j') {
    event.preventDefault()
    chatOpen.value = !chatOpen.value
  }
  if (event.key === 'Escape' && chatOpen.value) {
    chatOpen.value = false
  }
}

function openSearch(query = '', tab = 'all') {
  searchQuery.value = query
  searchTab.value = tab
  searchOpen.value = true
}

function solidColor(value, fallback) {
  const text = String(value || '')
  if (/^#[0-9a-fA-F]{6}/.test(text)) {
    return text.slice(0, 7)
  }
  return fallback
}

function chromeFor(opacity) {
  const t = Math.min(1, Math.max(0, Number(opacity) || 0))
  if (t >= 0.85) {
    return 82 + (18 * (t - 0.85)) / 0.15
  }
  return 100 - (18 * t) / 0.85
}

function paintOpacity(opacity) {
  const root = document.documentElement
  const value = opacity == null ? 0.85 : opacity
  root.style.setProperty('--wv-bg-opacity', String(value))
  root.style.setProperty('--wv-chrome', String(Math.round(chromeFor(value))))
}

function applyThemeVars(settings) {
  const root = document.documentElement
  const themeId = settings.theme || 'warm'
  const custom = (settings.custom_themes || []).find((item) => item.id === themeId)
  const keys = ['dawn', 'group', 'nav', 'work', 'orb', 'progress', 'group-solid', 'nav-solid', 'work-solid']
  if (custom?.vars) {
    root.dataset.theme = 'custom'
    keys.slice(0, 6).forEach((key) => {
      if (custom.vars[key]) {
        root.style.setProperty(`--wv-${key}`, custom.vars[key])
      }
    })
    root.style.setProperty('--wv-group-solid', solidColor(custom.vars.group, '#efeae1'))
    root.style.setProperty('--wv-nav-solid', solidColor(custom.vars.nav, '#f8f5ee'))
    root.style.setProperty('--wv-work-solid', solidColor(custom.vars.work, '#fcfaf5'))
  } else {
    root.dataset.theme = themeId
    keys.forEach((key) => root.style.removeProperty(`--wv-${key}`))
  }
  paintOpacity(settings.bg_opacity)
}

function applyAppearance(next) {
  appearance.value = {
    ...appearance.value,
    ...next,
    groups: next.groups || {},
    custom_themes: next.custom_themes || appearance.value.custom_themes || [],
  }
  applyThemeVars(appearance.value)
}

function previewOpacity(value) {
  paintOpacity(value)
}

function startOrbMove() {
  appearanceOpen.value = false
  orbMoving.value = true
}

async function finishOrbMove(payload) {
  appearance.value = { ...appearance.value, ...payload }
  orbMoving.value = false
  applyAppearance(await updateAppearance(payload))
}

function cancelOrbMove() {
  orbMoving.value = false
}

const groupMedia = computed(() => {
  if (activeGroupId.value == null) {
    return ''
  }
  return appearance.value.groups?.[String(activeGroupId.value)] || ''
})

const slotVideo = computed(() => {
  if (appearance.value.low_power || appearance.value.slot_background_media !== 'video' || !appearance.value.slots?.background) {
    return ''
  }
  return assetFileUrl('backgrounds', appearance.value.slots.background)
})

const slotStill = computed(() => {
  if (appearance.value.slot_background_media !== 'image' || !appearance.value.slots?.background) {
    return ''
  }
  return assetFileUrl('backgrounds', appearance.value.slots.background)
})

const packVideo = computed(() => {
  if (appearance.value.low_power || appearance.value.pack_background_kind !== 'video' || !appearance.value.pack_background) {
    return ''
  }
  if (!appearance.value.active_pack) {
    return ''
  }
  return packFileUrl(appearance.value.active_pack, appearance.value.pack_background)
})

const videoSrc = computed(() => {
  if (slotVideo.value) {
    return slotVideo.value
  }
  if (appearance.value.library_ready && !appearance.value.slots?.background) {
    return packVideo.value
  }
  return packVideo.value || (appearance.value.global_video && !appearance.value.low_power ? backgroundUrl(appearance.value.global_video) : '')
})

const packStill = computed(() => {
  if (appearance.value.pack_background_kind !== 'image' || !appearance.value.pack_background || !appearance.value.active_pack) {
    return ''
  }
  return packFileUrl(appearance.value.active_pack, appearance.value.pack_background)
})

const stillMedia = computed(() => {
  if (videoSrc.value) {
    return ''
  }
  if (slotStill.value) {
    return slotStill.value
  }
  if (appearance.value.library_ready && !appearance.value.slots?.background) {
    return groupMedia.value || packStill.value
  }
  return groupMedia.value || packStill.value || appearance.value.global_image || ''
})

async function closeGuide(hideNext) {
  guideOpen.value = false
  const hide = Boolean(hideNext)
  if (hide === Boolean(appearance.value.hide_guide)) {
    return
  }
  try {
    applyAppearance(await updateAppearance({ hide_guide: hide }))
  } catch (error) {
    console.error('Failed to save guide preference:', error)
  }
}

watch([splashVisible, shellReady, () => appearance.value.hide_guide], () => {
  if (splashVisible.value || !shellReady.value || appearance.value.hide_guide || guideOffered.value) {
    return
  }
  guideOffered.value = true
  guideOpen.value = true
})

async function openSearchNav({ groupId, navId }) {
  if (groupId == null || navId == null) {
    return
  }
  await selectGroup(groupId, navId, false)
}

async function openSearchGroup(groupId) {
  await selectGroup(groupId, null, true)
}

async function onNoteSaved(saved) {
  noticeMessage.value = '已记到收件箱'
  noteRevision.value += 1
  if (saved?.group_id == null || saved.group_id !== activeGroupId.value) {
    return
  }
  try {
    const items = await getNav(activeGroupId.value)
    if (showingOverview.value) {
      navItems.value = items
      return
    }
    applyNavItems(items, activeId.value)
  } catch (error) {
    console.error('Failed to refresh inbox nav:', error)
  }
}
</script>

<template>
  <main
    class="relative min-h-screen overflow-hidden text-ink"
    :class="videoSrc || stillMedia ? 'wv-has-media' : 'bg-dawn'"
  >
    <div v-if="splashVisible && !splashArmed" class="fixed inset-0 z-[100] bg-[#121816]" />
    <SplashScreen v-else-if="splashVisible" :appearance="appearance" @finished="splashVisible = false" />

    <section class="relative z-10 isolate flex min-h-screen">
      <div v-if="videoSrc || stillMedia" class="wv-media-layer pointer-events-none fixed inset-0 -z-10">
        <video
          v-if="videoSrc"
          :src="videoSrc"
          class="h-full w-full object-cover"
          autoplay
          muted
          loop
          playsinline
        />
        <img v-else-if="stillMedia" :src="stillMedia.startsWith('/api/') ? stillMedia : backgroundUrl(stillMedia)" alt="" class="h-full w-full object-cover" />
      </div>
      <GroupBar
        :groups="groups"
        :active-id="activeGroupId"
        :bar="appearance.bar || 'push'"
        @select="selectGroup($event, null, true)"
        @create="openCreateGroup"
        @edit="openEditGroup"
        @remove="removeGroup"
        @lock="toggleGroupLock"
        @reorder="persistGroupOrder"
        @receive="receiveNav"
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
        @search="openSearch()"
        @note="noteOpen = true"
        @appearance="appearanceOpen = true"
        @ai="chatOpen = !chatOpen"
      />
      <WorkspacePanel
        :item="activeItem"
        :loading="isLoading"
        :error-message="errorMessage"
        :empty="!isLoading && !errorMessage && !showingOverview && navItems.length === 0"
        :notice-message="noticeMessage"
        :overview-group="showingOverview ? activeGroup : null"
        :overview-items="navItems"
        :note-revision="noteRevision"
        :inbox-pause="noteOpen"
        @open-nav="openNav"
        @rename-group="renameGroup"
        @describe-group="describeGroup"
        @search-tag="openSearch($event, 'focus')"
      />
    </section>

    <NavEditDialog
      :open="isDialogOpen"
      :mode="dialogMode"
      :item="editingItem"
      :nav-items="navItems"
      :icon-pack="appearance.slots?.icons || ''"
      @close="isDialogOpen = false"
      @save="saveNavItem"
    />
    <GroupEditDialog
      :open="groupDialogOpen"
      :group="editingGroup"
      :icon-pack="appearance.slots?.icons || ''"
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
    <SearchDialog :open="searchOpen" :initial-query="searchQuery" :initial-tab="searchTab" @close="searchOpen = false" @open-nav="openSearchNav" />
    <QuickNoteDialog :open="noteOpen" @close="noteOpen = false" @saved="onNoteSaved" />
    <AppearanceDialog
      :open="appearanceOpen"
      :appearance="appearance"
      :group-id="activeGroupId"
      :group-name="activeGroup?.name || ''"
      @close="appearanceOpen = false"
      @change="applyAppearance"
      @opacity="previewOpacity"
      @open-guide="guideOpen = true"
      @move-orb="startOrbMove"
    />
    <ChatPanel :open="chatOpen" @close="chatOpen = false" @open-nav="openSearchNav" />
    <MusicDock
      v-if="!appearance.player_hidden"
      :place="appearance.player || 'corner'"
      :origin-x="appearance.player_x"
      :origin-y="appearance.player_y"
      :spread="appearance.player_spread || 'auto'"
      :progress-style="appearance.progress_style || 'solid'"
      :progress-color="appearance.progress_color || '#3f6f57'"
      :moving="orbMoving"
      @move-done="finishOrbMove"
      @move-cancel="cancelOrbMove"
      @hide="hideOrb"
    />
    <div v-if="appearance.active_pack && appearance.decorations?.length" class="pointer-events-none fixed inset-0 z-30">
      <img
        v-for="(item, index) in appearance.decorations"
        :key="item"
        :src="packFileUrl(appearance.active_pack, item)"
        alt=""
        class="wv-deco"
        :class="index === 0 ? 'wv-deco-0' : 'wv-deco-1'"
      />
    </div>
    <p v-if="toastText" class="wv-toast">{{ toastText }}</p>
    <GuideDialog v-if="guideOpen" :hide-next="appearance.hide_guide" @close="closeGuide" />
  </main>
</template>
