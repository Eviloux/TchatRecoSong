import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { initTheme } from './utils/theme';
import './assets/styles/app.scss';

initTheme();

const app = createApp(App);
app.use(router);
app.mount('#app');
