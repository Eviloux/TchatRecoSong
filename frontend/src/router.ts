import { createRouter, createWebHistory } from 'vue-router';
import HomeView from './views/HomeView.vue';
import AdminView from './views/AdminView.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/submit' },
    { path: '/submit', name: 'submit', component: HomeView },
    { path: '/admin', name: 'admin', component: AdminView },
<<<<<<< HEAD
=======
    { path: '/twitch-callback', name: 'twitch-callback', component: TwitchCallbackView },
>>>>>>> origin/codex/restore-code-from-merge-pr-#42-2x13fr
  ],
});

export default router;
