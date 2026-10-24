import { mount } from 'svelte';
import App from './App.svelte';
import './styles/tokens.css';
import './styles/components.css';
import './styles/app.css';

const target = document.getElementById('app');
if (!target) throw new Error('#app missing in index.html');
mount(App, { target });
