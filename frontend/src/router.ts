import { createRouter, createWebHistory } from 'vue-router';
import HomeView from './views/HomeView.vue';
import AdminView from './views/AdminView.vue';
import TwitchCallbackView from './views/TwitchCallbackView.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/submit' },
    { path: '/submit', name: 'submit', component: HomeView },
    { path: '/admin', name: 'admin', component: AdminView },

    { path: '/oauth/twitch', name: 'twitchCallback', component: AdminView },

  ],
});

export default router;
