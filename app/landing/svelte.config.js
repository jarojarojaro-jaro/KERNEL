import { readFileSync, rmSync } from 'node:fs';
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const json = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url), 'utf8'));

/**
 * Cards explorer pages (src/lib/cards/explorer.ts uses the same rule): every card in the generated
 * sheet (cards.json) plus every GPU with a lab status in gpus.json ('measured', 'in-progress',
 * 'planned' = the measurement queue). Maker index, one page per maker, compare view and one page
 * per card, in both languages.
 */
const cardIds = [
	...new Set([
		...json('./src/lib/data/cards.json').cards.map((c) => c.id),
		...json('./src/lib/data/gpus.json')
			.gpus.filter((g) => g.lab)
			.map((g) => g.id)
	])
];
const vendors = ['nvidia', 'amd', 'intel', 'apple'];
const cardPages = [
	['pl', 'karty', 'porownaj'],
	['en', 'cards', 'compare']
].flatMap(([l, seg, cmp]) => [`/${l}/${seg}/`, `/${l}/${seg}/${cmp}/`, ...vendors.map((v) => `/${l}/${seg}/${v}/`), ...cardIds.map((id) => `/${l}/${seg}/${id}/`)]);

/** Public build (PUBLIC_SITE_PUBLIC=1): the methodology loops ship with no page, so drop them from build/. */
const publicAdapter = (inner) =>
	process.env.PUBLIC_SITE_PUBLIC === '1'
		? {
				...inner,
				async adapt(builder) {
					await inner.adapt(builder);
					rmSync(new URL('./build/media/methodology', import.meta.url), { recursive: true, force: true });
				}
			}
		: inner;

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: publicAdapter(adapter({ pages: 'build', assets: 'build', fallback: undefined, strict: true })),
		alias: { $design: '../design' },
		prerender: {
			// Absolute URLs (canonical/hreflang/og:url) come from PUBLIC_SITE_ORIGIN via src/lib/site/public.ts, not page.url.origin.
			...(process.env.PUBLIC_SITE_ORIGIN ? { origin: process.env.PUBLIC_SITE_ORIGIN.replace(/\/+$/, '') } : {}),
			handleHttpError: 'fail',
			handleMissingId: 'fail',
			// Public build (PUBLIC_SITE_PUBLIC=1, vite.config.ts): the methodology route is unlinked and not built.
			handleUnseenRoutes: ({ routes }) => {
				const unseen = routes.filter((r) => !(process.env.PUBLIC_SITE_PUBLIC === '1' && r.endsWith('/methodology')));
				if (unseen.length) throw new Error(`Routes not prerendered: ${unseen.join(', ')}`);
			},
			// Onboarding steps are reached through form submits (goto), so the crawler needs them listed;
			// the cards explorer is listed in full so no card page depends on being linked.
			entries: ['*', ...['pl', 'en'].flatMap((l) => ['paths', 'result', 'download', 'terminal'].map((s) => `/${l}/start/${s}/`)), ...cardPages]
		},
		// New deploy detection: client navigations after a deploy do a full page load (no stale chunks).
		version: { pollInterval: 300000 },
		// Inline the (small) global CSS so first paint needs no extra round trip.
		inlineStyleThreshold: 40000
	}
};

export default config;
