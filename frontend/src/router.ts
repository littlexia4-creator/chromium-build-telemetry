import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/builds/:id', name: 'detail', component: () => import('./views/BuildDetail.vue'), props: true },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
