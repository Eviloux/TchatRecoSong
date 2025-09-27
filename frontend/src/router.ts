import { createRouter, createWebHistory } from 'vue-router';
import HomeView from './views/HomeView.vue';
import SubmissionView from './views/SubmissionView.vue';
import AdminView from './views/AdminView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/submit/:token', name: 'submit', component: SubmissionView, props: true },
    { path: '/admin', name: 'admin', component: AdminView },
  ],
});

export default router;
