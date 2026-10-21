import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, type Plugin } from 'vite';

/** Public (online) build: no methodology pages, no internal source paths (src/lib/site/public.ts). */
const SITE_PUBLIC = process.env.PUBLIC_SITE_PUBLIC === '1';

/** Public build: the methodology route compiles to an empty page; nothing links to it, so it is never prerendered. */
const dropMethodology = (): Plugin => ({
	name: 'site-public-drop-methodology',
	enforce: 'pre',
	load(id) {
		if (/[\\/]routes[\\/]\[lang=lang\][\\/]\(site\)[\\/]methodology[\\/]\+page\.svelte$/.test(id)) return '';
	}
});

/** Names an internal file: a repo path, a research report, a log or a JSONL dump. */
const INTERNAL = /KERNEL\/|qwen-opt\/|[\w-]+\.(?:md|log|jsonl)\b/;

type Node = { type: string; start: number; end: number; value?: unknown; expressions?: unknown[]; quasis?: { value: { cooked: string } }[] };

/** Every string literal (and interpolation-free template literal) in the AST that names an internal file. */
function internalLiterals(node: unknown, out: Node[]): Node[] {
	if (!node || typeof node !== 'object') return out;
	if (Array.isArray(node)) {
		for (const n of node) internalLiterals(n, out);
		return out;
	}
	const n = node as Node;
	if (n.type === 'Literal' && typeof n.value === 'string') {
		if (INTERNAL.test(n.value)) out.push(n);
		return out;
	}
	if (n.type === 'TemplateLiteral' && n.quasis!.some((q) => INTERNAL.test(q.value.cooked))) {
		out.push(n);
		return out;
	}
	for (const k in n) if (k !== 'type' && k !== 'start' && k !== 'end') internalLiterals((n as Record<string, unknown>)[k], out);
	return out;
}

/**
 * Public build: every bundled string literal naming an internal file becomes '' (client and SSR
 * chunks, so the prerendered HTML loses them too).
 */
const stripSources = (): Plugin => ({
	name: 'site-public-strip-sources',
	renderChunk(code) {
		const hits = internalLiterals(this.parse(code), []);
		if (!hits.length) return null;
		let out = code;
		for (const h of hits.sort((a, b) => b.start - a.start)) out = out.slice(0, h.start) + '""' + out.slice(h.end);
		return { code: out, map: null };
	}
});
export default defineConfig({
	plugins: [...(SITE_PUBLIC ? [dropMethodology(), stripSources()] : []), sveltekit()],
	define: { __SITE_PUBLIC__: JSON.stringify(SITE_PUBLIC) },
	// Large JSON must stay a plain object literal (not JSON.parse("…")) so stripSources sees each string.
	json: SITE_PUBLIC ? { stringify: false } : undefined,
	server: { port: 18433, strictPort: true, fs: { allow: ['..'] } },
	preview: { port: 18433, strictPort: true }
});
