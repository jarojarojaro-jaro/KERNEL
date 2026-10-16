import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({ pages: 'build', assets: 'build', fallback: undefined, strict: true }),
		alias: { $design: '../design' },
		prerender: {
			// Absolute origin for hreflang/canonical. Set SITE_ORIGIN when a domain exists (no domain yet: PLAN §7).
			origin: process.env.SITE_ORIGIN ?? 'http://127.0.0.1:18433',
			handleHttpError: 'fail',
			handleMissingId: 'fail',
			// Onboarding steps are reached through form submits (goto), so the crawler needs them listed.
			entries: ['*', ...['pl', 'en'].flatMap((l) => ['paths', 'result', 'download', 'terminal'].map((s) => `/${l}/start/${s}/`))]
		},
		// Inline the (small) global CSS so first paint needs no extra round trip.
		inlineStyleThreshold: 40000
	}
};

export default config;
