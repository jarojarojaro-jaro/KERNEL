import { readFileSync } from 'node:fs';
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const json = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url), 'utf8'));

/**
 * Cards explorer pages (src/lib/cards/explorer.ts uses the same rule): every card in the generated
 * sheet (cards.json) plus every GPU with a lab status in gpus.json ('measured', 'in-progress',
 * 'planned' = the measurement queue). Gallery, compare view and one page per card, in both languages.
 */
const cardIds = [
	...new Set([
		...json('./src/lib/data/cards.json').cards.map((c) => c.id),
		...json('./src/lib/data/gpus.json')
			.gpus.filter((g) => g.lab)
			.map((g) => g.id)
	])
];
const cardPages = [
	['pl', 'karty', 'porownaj'],
	['en', 'cards', 'compare']
].flatMap(([l, seg, cmp]) => [`/${l}/${seg}/`, `/${l}/${seg}/${cmp}/`, ...cardIds.map((id) => `/${l}/${seg}/${id}/`)]);

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
			// Onboarding steps are reached through form submits (goto), so the crawler needs them listed;
			// the cards explorer is listed in full so no card page depends on being linked.
			entries: ['*', ...['pl', 'en'].flatMap((l) => ['paths', 'result', 'download', 'terminal'].map((s) => `/${l}/start/${s}/`)), ...cardPages]
		},
		// Inline the (small) global CSS so first paint needs no extra round trip.
		inlineStyleThreshold: 40000
	}
};

export default config;
