import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

/** Backend the dev server proxies to (`bun run dev` serves the API on ENIGMA_PORT, default 11525). */
const api = `http://127.0.0.1:${process.env.ENIGMA_PORT ?? '11525'}`;

export default defineConfig({
	plugins: [svelte()],
	root: '.',
	base: '/',
	build: {
		outDir: 'dist/ui',
		emptyOutDir: true,
		target: 'es2022',
		assetsInlineLimit: 0,
		reportCompressedSize: false
	},
	server: {
		host: '127.0.0.1',
		port: 11501,
		strictPort: true,
		proxy: {
			'/api': { target: api, changeOrigin: true },
			'/v1': { target: api, changeOrigin: true }
		}
	}
});
