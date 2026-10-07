import GalleryBlock from './GalleryBlock.vue'
import LinkBlock from './LinkBlock.vue'
import MarkdownBlock from './MarkdownBlock.vue'
import TodoBlock from './TodoBlock.vue'

export const blockComponents = {
  markdown: MarkdownBlock,
  todo: TodoBlock,
  link: LinkBlock,
  gallery: GalleryBlock,
}

export const blockOptions = [
  { type: 'markdown', label: 'Markdown' },
  { type: 'todo', label: '待办' },
  { type: 'link', label: '链接' },
  { type: 'gallery', label: '画廊' },
]

export const defaultBlockContent = {
  markdown: { text: '' },
  todo: { items: [] },
  link: { links: [] },
  gallery: { images: [] },
}
