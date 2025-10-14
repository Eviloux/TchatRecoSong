import { createRouter, createWebHistory } from 'vue-router';
import HomeView from './views/HomeView.vue';
import AdminView from './views/AdminView.vue';
import { ensureValidStoredAdminSession, loadStoredAdminSession } from './utils/adminSession';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/submit' },
    { path: '/submit', name: 'submit', component: HomeView },
    { path: '/admin', name: 'admin', component: AdminView },
  ],
});

router.beforeEach(async (to) => {
  if (to.name !== 'admin') {
    return true;
  }

  const { token } = loadStoredAdminSession();
  if (!token) {
    return true;
  }

  const validation = await ensureValidStoredAdminSession();

  if (validation.status === 'invalid') {
    return true;
  }

  if (validation.status === 'error') {
    console.warn('Impossible de valider la session admin avant navigation vers /admin');
  }

  return true;
});

export default router;
