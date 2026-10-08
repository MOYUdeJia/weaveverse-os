import ChartBlock from './ChartBlock.vue'
import CodeBlock from './CodeBlock.vue'
import GalleryBlock from './GalleryBlock.vue'
import LinkBlock from './LinkBlock.vue'
import MarkdownBlock from './MarkdownBlock.vue'
import ProgressBlock from './ProgressBlock.vue'
import ScheduleBlock from './ScheduleBlock.vue'
import TodoBlock from './TodoBlock.vue'

export const blockComponents = {
  markdown: MarkdownBlock,
  todo: TodoBlock,
  link: LinkBlock,
  gallery: GalleryBlock,
  schedule: ScheduleBlock,
  progress: ProgressBlock,
  chart: ChartBlock,
  code: CodeBlock,
}

export const blockOptions = [
  { type: 'markdown', label: 'Markdown' },
  { type: 'todo', label: '待办' },
  { type: 'link', label: '链接' },
  { type: 'gallery', label: '画廊' },
  { type: 'schedule', label: '计划表' },
  { type: 'progress', label: '进度' },
  { type: 'chart', label: '图表' },
  { type: 'code', label: '代码' },
]

export const defaultBlockContent = {
  markdown: { text: '' },
  todo: { items: [] },
  link: { links: [] },
  gallery: { images: [] },
  schedule: { entries: [] },
  progress: { items: [] },
  chart: { chart_type: 'line', unit: '', data: [] },
  code: { language: 'plain', text: '', highlight: false },
}
