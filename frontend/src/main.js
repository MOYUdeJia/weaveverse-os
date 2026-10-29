import ContextMenu from '@imengyu/vue3-context-menu'
import { createApp } from 'vue'

import App from './App.vue'
import FocusPet from './components/FocusPet.vue'
import '@imengyu/vue3-context-menu/lib/vue3-context-menu.css'
import './style.css'

const surface = new URLSearchParams(window.location.search).get('surface')
if (surface === 'pet') {
  document.documentElement.dataset.surface = 'pet'
  createApp(FocusPet).mount('#app')
} else {
  createApp(App).use(ContextMenu).mount('#app')
}
