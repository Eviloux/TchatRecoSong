import { createRouter, createWebHistory } from 'vue-router';
import HomeView from './views/HomeView.vue';
import AdminView from './views/AdminView.vue';
import LoginView from './views/LoginView.vue';
import { ensureValidStoredAdminSession, loadStoredAdminSession } from './utils/adminSession';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'submit', component: HomeView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true } },
  ],
});

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth) {
    const { token } = loadStoredAdminSession();
    if (!token) {
      return { name: 'login', query: { redirect: to.fullPath } };
    }

    const validation = await ensureValidStoredAdminSession({ force: true });
    if (validation.status === 'valid') {
      return true;
    }

    if (validation.status === 'error') {
      console.warn('Impossible de valider la session admin avant navigation vers /admin');
    }

    return { name: 'login', query: { redirect: to.fullPath } };
  }

  if (to.name === 'login') {
    const { token } = loadStoredAdminSession();
    if (!token) {
      return true;
    }

    const validation = await ensureValidStoredAdminSession({ force: true });
    if (validation.status === 'valid') {
      return { name: 'admin' };
    }

    if (validation.status === 'error') {
      console.warn('Impossible de valider la session admin avant navigation vers /login');
    }
  }

  return true;
});

export default router;
