import { onBeforeUnmount } from 'vue'

// 输入停一会儿再保存。切页或卸载时把还没发出的内容补上。
// Save after a short pause, and flush a pending edit when the page changes.
export function useQueuedSave(emit, readContent, delay = 450) {
  let timer = null
  let blockId = null

  function queue(id) {
    blockId = id
    clearTimeout(timer)
    timer = setTimeout(flush, delay)
  }

  function flush() {
    if (timer === null) {
      return
    }
    clearTimeout(timer)
    timer = null
    const id = blockId
    blockId = null
    if (id == null) {
      return
    }
    emit('save', { blockId: id, content: readContent() })
  }

  function cancel() {
    clearTimeout(timer)
    timer = null
    blockId = null
  }

  onBeforeUnmount(flush)

  return { queue, flush, cancel }
}
