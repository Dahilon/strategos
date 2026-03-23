import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import PlannerView from '../views/PlannerView.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/planner/:worldId/:scenarioId', name: 'Planner', component: PlannerView, props: true },
]

export default createRouter({
  history: createWebHistory(),
  routes
})
