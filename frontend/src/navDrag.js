// 侧栏拖到分组栏时用的临时载荷。放下后由分组栏标记 dropped，避免再触发排序。
export const navDrag = {
  id: null,
  dropped: false,
}

export function beginNavDrag(id) {
  navDrag.id = id
  navDrag.dropped = false
}

export function endNavDrag() {
  navDrag.id = null
}
