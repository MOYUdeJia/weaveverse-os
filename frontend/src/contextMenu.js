import ContextMenu from '@imengyu/vue3-context-menu'

// 在鼠标位置打开右键菜单。
// Open the shared context menu at the pointer.
export function showMenu(event, items) {
  event.preventDefault()
  event.stopPropagation()
  ContextMenu.showContextMenu({
    x: event.clientX,
    y: event.clientY,
    zIndex: 80,
    items,
  })
}
