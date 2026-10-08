// 专用页登记表。「+」菜单的「新建专用页」读这里，不进「新建积木页」。
// Focus-page registry. The add menu's focus entry reads this, not the flex-page list.
//
// placement: 'focus' 进专用页选择；省略则作为「+」菜单上的独立入口。
// placement 'focus' opens inside the focus picker. Omit it for a top-level add action.
export const specialAdds = {
  doc: {
    label: '长文',
    icon: '📄',
    pageType: 'doc',
    placement: 'focus',
    description: '一整页 Markdown，边写边看排版',
  },
  plain: {
    label: '笔记',
    icon: '📝',
    pageType: 'plain',
    placement: 'focus',
    description: '行号或分条，可以为每一行上色',
  },
  bookmarks: {
    label: '网址集',
    icon: '🔖',
    pageType: 'bookmarks',
    placement: 'focus',
    description: '分区收藏标题、网址和 #标签',
  },
  canvas: {
    label: '白板',
    icon: '🎨',
    pageType: 'canvas',
    placement: 'focus',
    description: '无限画布，画笔、图形和文本',
  },
}

export function focusAdds() {
  return Object.values(specialAdds).filter((item) => item.placement === 'focus')
}

export function focusPageByType(pageType) {
  return focusAdds().find((item) => item.pageType === pageType) || null
}
