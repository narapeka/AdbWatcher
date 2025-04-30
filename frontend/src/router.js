import { createRouter, createWebHistory } from 'vue-router'

// Views
import Dashboard from './views/Dashboard.vue'
import Config from './views/Config.vue'

// Routes
const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/config',
    name: 'Config',
    component: Config
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 