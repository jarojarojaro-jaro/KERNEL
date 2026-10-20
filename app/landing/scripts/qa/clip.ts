/**
 * Clipped-text gate: no word or letter on the site may be cut off. Crawls every prerendered page in
 * ./build (served by this script) at 320/390/768/1024/1440/1920 with prefers-reduced-motion (pages at
 * rest) and fails on:
 *   overflow  the page scrolls sideways (scrollWidth > clientWidth)
 *   clip      a glyph is partly hidden by a clipping ancestor (overflow hidden/clip, a non-scrolling
 *             auto/scroll box, clip-path), or a word/line is cut there with some letters shown and
 *             some hidden (also text-overflow: ellipsis, reported as `ellipsis`)
 *   bgclip    background-clip: text, and a glyph's ink (italic overhang, ę ą ł descenders, Ż Ś
 *             accents, negative tracking) leaves the box that paints its colour: that part is invisible
 * Glyph ink comes from canvas measureText with the element's font, per character, placed on the
 * character's layout rect. Text that is wholly outside its clip (odometer digits at rest, lines that
 * scrolled out of a terminal pane) is hidden by design and not reported; scrollable boxes (carousels)
 * do not clip in the axis they scroll. `data-clip-ok` on a rolling/scrolling viewport (odometer reel,
 * terminal pane) skips the text inside it; nothing else may use it. SVG text is not checked.
 *
 * Usage: `bun run qa:clip` (launches CPU-only chrome-swgl), or `CDP=http://127.0.0.1:18499 bun run qa:clip`
 * to use a running Chrome. `PAGES=/pl/,/en/cards/` limits the pages, `VP=390,1440` the widths.
 * Exit code 1 when anything is found.
 */
import { readdirSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import puppeteer, { type Browser } from 'puppeteer-core';

const ROOT = resolve(import.meta.dir, '../../build');
const WIDTHS = (process.env.VP ?? '320,390,768,1024,1440,1920').split(',').map(Number);
const TOL = 0.5;

function pagesIn(dir: string): string[] {
	const out: string[] = [];
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) {
			if (name !== '_app') out.push(...pagesIn(p));
		} else if (name === 'index.html') out.push('/' + relative(ROOT, dir).split('\\').join('/') + (dir === ROOT ? '' : '/'));
	}
	return out;
}
const PAGES = process.env.PAGES ? process.env.PAGES.split(',') : pagesIn(ROOT).map((p) => p.replace(/^\/\//, '/')).sort();

/* the build, served as a static host would (`<dir>/index.html`) */
const server = Bun.serve({
	hostname: '127.0.0.1',
	port: 0,
	async fetch(req) {
		const url = new URL(req.url);
		let path = join(ROOT, decodeURIComponent(url.pathname));
		if (!path.startsWith(ROOT)) return new Response('Forbidden', { status: 403 });
		if (url.pathname.endsWith('/')) path = join(path, 'index.html');
		const f = Bun.file(path);
		return (await f.exists()) ? new Response(f) : new Response('Not found', { status: 404 });
	}
});
const BASE = `http://127.0.0.1:${server.port}`;

const browser: Browser = process.env.CDP
	? await puppeteer.connect({ browserURL: process.env.CDP, defaultViewport: null })
	: await puppeteer.launch({
			executablePath: resolve(import.meta.dir, '../../../.tools/chrome-swgl'),
			headless: true,
			args: ['--no-sandbox', '--hide-scrollbars', `--user-data-dir=/tmp/qa-clip-${process.pid}`]
		});

type Hit = { kind: 'overflow' | 'clip' | 'ellipsis' | 'bgclip'; where: string; text: string; px: number };

/** Runs in the page: every clipped glyph, cut word and invisible bit of gradient text. */
function scan(TOL: number): Hit[] {
	const hits: Hit[] = [];
	const de = document.documentElement;
	if (de.scrollWidth > de.clientWidth) hits.push({ kind: 'overflow', where: 'html', text: '', px: de.scrollWidth - de.clientWidth });

	type Box = { l: number; t: number; r: number; b: number };
	const INF = 1e9;
	const desc = (el: Element) => {
		const parts: string[] = [];
		for (let e: Element | null = el; e && parts.length < 3 && e !== document.body; e = e.parentElement) {
			const cls = [...e.classList].filter((c) => !c.startsWith('svelte-')).slice(0, 2).join('.');
			parts.unshift(e.tagName.toLowerCase() + (cls ? '.' + cls : ''));
		}
		return parts.join(' > ');
	};

	/* the effective clip box of an element's content: the intersection of every clipping ancestor
	   on its containing-block chain (absolute/fixed boxes escape non-positioned ancestors). A box that
	   scrolls in an axis (carousel) frees that axis for itself and every ancestor beyond it: whatever
	   lies outside its viewport is reached by scrolling. Each edge remembers the element that set it. */
	type Edge = 'l' | 't' | 'r' | 'b';
	type Clip = { box: Box; own: Record<Edge, Element | null>; ellipsis: boolean } | null;
	const clipCache = new Map<Element, Clip | 'skip'>();
	function clipOf(start: Element): Clip | 'skip' {
		if (clipCache.has(start)) return clipCache.get(start)!;
		const box: Box = { l: -INF, t: -INF, r: INF, b: INF };
		const own: Record<Edge, Element | null> = { l: null, t: null, r: null, b: null };
		const tighten = (e: Element, edge: Edge, v: number) => {
			if (edge === 'l' || edge === 't' ? v > box[edge] : v < box[edge]) {
				box[edge] = v;
				own[edge] = e;
			}
		};
		let ellipsis = false;
		let freeX = false;
		let freeY = false;
		let escape: 'none' | 'absolute' | 'fixed' = 'none';
		let res: Clip | 'skip' = null;
		for (let e: Element | null = start; e; e = e.parentElement) {
			const cs = getComputedStyle(e);
			const r = e.getBoundingClientRect();
			// visually hidden (sr-only) text is meant to be clipped; so is text inside an opted-out
			// rolling window (odometer reel, terminal pane)
			if ((cs.clip && cs.clip !== 'auto') || (r.width <= 1 && r.height <= 1 && cs.overflow !== 'visible') || e.hasAttribute('data-clip-ok')) {
				res = 'skip';
				break;
			}
			const createsCb = cs.transform !== 'none' || cs.filter !== 'none' || cs.perspective !== 'none' || /paint|layout|strict|content/.test(cs.contain);
			const positioned = cs.position !== 'static';
			const applies = escape === 'none' || (escape === 'absolute' && (positioned || createsCb)) || (escape === 'fixed' && createsCb);
			if (e !== start && applies) escape = 'none';
			if (applies) {
				const root = e === de || e === document.body;
				const bl = parseFloat(cs.borderLeftWidth), bt = parseFloat(cs.borderTopWidth);
				const pad: Box = root ? { l: 0, t: -INF, r: de.clientWidth, b: INF } : { l: r.left + bl, t: r.top + bt, r: r.left + bl + e.clientWidth, b: r.top + bt + e.clientHeight };
				const ox = cs.overflowX, oy = cs.overflowY;
				if ((ox === 'auto' || ox === 'scroll') && e.scrollWidth > e.clientWidth + 1 && !root) freeX = true;
				if ((oy === 'auto' || oy === 'scroll') && e.scrollHeight > e.clientHeight + 1 && !root) freeY = true;
				let clipped = false;
				if (ox !== 'visible' && !freeX) {
					tighten(e, 'l', pad.l);
					tighten(e, 'r', pad.r);
					clipped = true;
				}
				if (oy !== 'visible' && !freeY && !root) {
					tighten(e, 't', pad.t);
					tighten(e, 'b', pad.b);
					clipped = true;
				}
				if (cs.clipPath !== 'none' && !root) {
					if (!freeX) {
						tighten(e, 'l', r.left);
						tighten(e, 'r', r.right);
					}
					if (!freeY) {
						tighten(e, 't', r.top);
						tighten(e, 'b', r.bottom);
					}
					clipped = true;
				}
				if (clipped && cs.textOverflow === 'ellipsis') ellipsis = true;
			}
			if (cs.position === 'fixed') escape = 'fixed';
			else if (cs.position === 'absolute' && escape === 'none') escape = 'absolute';
		}
		if (res !== 'skip') res = own.l || own.t || own.r || own.b ? { box, own, ellipsis } : null;
		clipCache.set(start, res);
		return res;
	}

	/* glyph ink from the element's font, placed on the character's layout rect */
	const ctx = document.createElement('canvas').getContext('2d')!;
	const STRETCH: [number, CanvasFontStretch][] = [[50, 'ultra-condensed'], [62.5, 'extra-condensed'], [75, 'condensed'], [87.5, 'semi-condensed'], [100, 'normal'], [112.5, 'semi-expanded'], [125, 'expanded'], [150, 'extra-expanded'], [200, 'ultra-expanded']];
	const inkCache = new Map<string, { l: number; r: number; a: number; d: number; fa: number; fd: number }>();
	function inkOf(cs: CSSStyleDeclaration, ch: string) {
		const st = parseFloat(cs.fontStretch) || 100;
		const stretch = STRETCH.reduce((a, b) => (Math.abs(b[0] - st) < Math.abs(a[0] - st) ? b : a))[1];
		const font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
		const key = font + stretch + ch;
		let m = inkCache.get(key);
		if (!m) {
			ctx.font = font;
			ctx.fontStretch = stretch;
			ctx.letterSpacing = '0px';
			const t = ctx.measureText(ch);
			m = { l: t.actualBoundingBoxLeft, r: t.actualBoundingBoxRight, a: t.actualBoundingBoxAscent, d: t.actualBoundingBoxDescent, fa: t.fontBoundingBoxAscent, fd: t.fontBoundingBoxDescent };
			inkCache.set(key, m);
		}
		return m;
	}
	type Glyph = { ch: string; ink: Box; line: number; word: number };
	function glyphs(node: Text, cs: CSSStyleDeclaration): Glyph[] {
		const out: Glyph[] = [];
		const s = node.data;
		const range = document.createRange();
		const upper = cs.textTransform === 'uppercase';
		let word = 0;
		for (let i = 0; i < s.length; i++) {
			const code = s.charCodeAt(i);
			const n = code >= 0xd800 && code <= 0xdbff ? 2 : 1;
			const raw = s.slice(i, i + n);
			if (/\s/.test(raw)) {
				word++;
				i += n - 1;
				continue;
			}
			range.setStart(node, i);
			range.setEnd(node, i + n);
			i += n - 1;
			const rr = range.getClientRects()[0];
			if (!rr || rr.height === 0) continue;
			const ch = upper ? raw.toUpperCase() : raw;
			const m = inkOf(cs, ch);
			const k = rr.height / (m.fa + m.fd || rr.height); // transforms and zoom
			const base = rr.top + m.fa * k;
			out.push({ ch: raw, ink: { l: rr.left - m.l * k, r: rr.left + m.r * k, t: base - m.a * k, b: base + m.d * k }, line: Math.round(rr.top), word });
		}
		return out;
	}
	const outside = (g: Box, c: Box) => Math.max(c.l - g.l, g.r - c.r, c.t - g.t, g.b - c.b, 0);
	const fullyOut = (g: Box, c: Box) => g.r <= c.l + TOL || g.l >= c.r - TOL || g.b <= c.t + TOL || g.t >= c.b - TOL;
	const visible = (el: Element) => el.checkVisibility({ opacityProperty: true, visibilityProperty: true });

	const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
	const seen = new Set<Element>();
	for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) {
		const el = n.parentElement;
		if (!el || !n.data.trim() || el.closest('svg, script, style, noscript, template') || !visible(el)) continue;
		const clip = clipOf(el);
		if (clip === 'skip' || !clip) continue;
		const cs = getComputedStyle(el);
		const range = document.createRange();
		range.selectNodeContents(n);
		const rects = [...range.getClientRects()];
		const em = parseFloat(cs.fontSize);
		// cheap pass: every line box well inside the clip (room for ink overhang) → fine
		if (rects.every((r) => r.left - 0.4 * em >= clip.box.l && r.right + 0.4 * em <= clip.box.r && r.top - 0.3 * em >= clip.box.t && r.bottom + 0.3 * em <= clip.box.b)) continue;
		if (rects.every((r) => fullyOut({ l: r.left, t: r.top, r: r.right, b: r.bottom }, clip.box))) continue;
		const gs = glyphs(n, cs);
		let worst = 0;
		const over: Record<Edge, number> = { l: 0, t: 0, r: 0, b: 0 };
		const state = new Map<string, Set<string>>();
		for (const g of gs) {
			const st = fullyOut(g.ink, clip.box) ? 'out' : outside(g.ink, clip.box) > TOL ? 'cut' : 'in';
			if (st === 'cut') worst = Math.max(worst, outside(g.ink, clip.box));
			if (st !== 'in') {
				over.l = Math.max(over.l, clip.box.l - g.ink.l);
				over.r = Math.max(over.r, g.ink.r - clip.box.r);
				over.t = Math.max(over.t, clip.box.t - g.ink.t);
				over.b = Math.max(over.b, g.ink.b - clip.box.b);
			}
			for (const key of [`w${g.word}`, `l${g.line}`]) {
				const set = state.get(key) ?? new Set();
				set.add(st);
				state.set(key, set);
			}
		}
		const mixed = [...state.values()].some((s) => s.has('in') && (s.has('out') || s.has('cut')));
		if ((worst > TOL || mixed) && !seen.has(el)) {
			seen.add(el);
			// name the element whose edge the text crosses the most
			const edge = (['l', 't', 'r', 'b'] as Edge[]).reduce((a, b) => (over[b] > over[a] ? b : a));
			const by = clip.own[edge] ?? clip.own.l ?? clip.own.t ?? clip.own.r ?? clip.own.b!;
			hits.push({ kind: clip.ellipsis ? 'ellipsis' : 'clip', where: `${desc(el)}  (clipped by ${desc(by)})`, text: n.data.trim().slice(0, 40), px: Math.round(worst * 10) / 10 });
		}
	}

	// gradient text: the colour is painted only inside the element's box (each fragment for inlines)
	for (const el of document.body.querySelectorAll('*')) {
		const cs = getComputedStyle(el);
		const bc = cs.backgroundClip + ' ' + cs.getPropertyValue('-webkit-background-clip');
		if (!/text/.test(bc) || el.closest('svg') || !visible(el)) continue;
		const frags = [...el.getClientRects()].map((r) => ({ l: r.left, t: r.top, r: r.right, b: r.bottom }));
		if (!frags.length) continue;
		const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
		let worst = 0;
		let sample = '';
		for (let n = tw.nextNode() as Text | null; n; n = tw.nextNode() as Text | null) {
			if (!n.data.trim() || !n.parentElement || !visible(n.parentElement)) continue;
			for (const g of glyphs(n, getComputedStyle(n.parentElement))) {
				const o = Math.min(...frags.map((f) => outside(g.ink, f)));
				if (o > worst) {
					worst = o;
					sample = g.ch;
				}
			}
		}
		if (worst > TOL) hits.push({ kind: 'bgclip', where: desc(el), text: `${(el.textContent ?? '').trim().slice(0, 40)}  [worst: ${sample}]`, px: Math.round(worst * 10) / 10 });
	}
	return hits;
}

const all = new Map<string, { hit: Hit; page: string; widths: number[] }>();
const ctxB = await browser.createBrowserContext();
const page = await ctxB.newPage();
await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
await page.evaluateOnNewDocument(() => localStorage.setItem('consent', JSON.stringify({ v: 1, analytics: false, at: new Date().toISOString() })));
for (const w of WIDTHS) {
	await page.setViewport({ width: w, height: 900, deviceScaleFactor: 1, isMobile: w < 600, hasTouch: w < 600 });
	for (const p of PAGES) {
		try {
			await page.goto(BASE + p, { waitUntil: 'load', timeout: 60000 });
			await page.evaluate(() => document.fonts.ready);
			await Bun.sleep(400);
			const hits = (await page.evaluate(scan, TOL)) as Hit[];
			for (const h of hits) {
				const key = `${p}|${h.kind}|${h.where}|${h.text}`;
				const e = all.get(key) ?? { hit: h, page: p, widths: [] };
				if (!e.widths.includes(w)) e.widths.push(w);
				e.hit.px = Math.max(e.hit.px, h.px);
				all.set(key, e);
			}
		} catch (err) {
			console.log(`${w} ${p} ERROR ${(err as Error).message}`);
		}
	}
}
await ctxB.close();
if (process.env.CDP) await browser.disconnect();
else await browser.close();
server.stop(true);

type Found = { hit: Hit; page: string; widths: number[] };
const byPage = new Map<string, Found[]>();
for (const e of all.values()) byPage.set(e.page, [...(byPage.get(e.page) ?? []), e]);
for (const [p, es] of [...byPage].sort()) {
	console.log(`\n${p}`);
	for (const e of es) console.log(`  ${e.hit.kind.padEnd(8)} ${String(e.hit.px).padStart(5)}px  @${e.widths.join(',')}  ${e.hit.where}  "${e.hit.text}"`);
}
console.log(`\n${all.size} problem(s) on ${byPage.size} of ${PAGES.length} pages × ${WIDTHS.length} widths`);
process.exit(all.size ? 1 : 0);
