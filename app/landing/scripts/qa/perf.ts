/**
 * Performance budget check (PERF.md): page-load metrics and click→interactive navigation timings,
 * measured on the static build in CPU-only headless Chrome (chrome-swgl, no GPU: numbers are
 * pessimistic next to a real desktop browser).
 *
 *   bun scripts/qa/perf.ts                 # ./build, every page, CPU 4× load + nav at 1× and 4×
 *   ROOT=/tmp/old-build bun scripts/qa/perf.ts
 *   PAGES=/pl/,/pl/karty/ RUNS=5 JSON=out.json bun scripts/qa/perf.ts
 *
 * Load (fresh browser context each run, CPU 4×, 1366×768): LCP, CLS (largest 5 s session window),
 * TBT (sum of long-task time over 50 ms from FCP to 5 s after load), JS kB transferred (gzip).
 * Navigation (warm page, mouse hovers 120 ms before the click, as a person does):
 *   input   = longest Event Timing entry of the click (pointerdown → next paint), the INP proxy;
 *   content = pointerdown → the new page's <h1> is in the DOM;
 *   ready   = pointerdown → new content, the page under the pointer is hit-testable (no
 *             view-transition overlay swallowing clicks) and a posted task runs within 50 ms.
 * Medians of RUNS (default 3). RM=1 emulates prefers-reduced-motion (no view transition): the
 * difference to a normal run is what the transition costs.
 */
import { resolve, join, extname } from 'node:path';
import puppeteer, { type Browser, type Page } from 'puppeteer-core';

const ROOT = resolve(process.env.ROOT ?? resolve(import.meta.dir, '../../build'));
const RUNS = Number(process.env.RUNS ?? 3);
const PAGES = (process.env.PAGES ?? '/pl/,/pl/karty/,/pl/karty/nvidia/,/pl/karty/rtx-3090/,/pl/karty/porownaj/?a=rtx-3090&b=rx-7900-xtx,/pl/methodology/,/pl/start/').split(',');
const NAVS = process.env.NAVS === '0' ? [] : [
	{ name: 'tile→vendor', from: '/pl/karty/', link: 'a[href="/pl/karty/nvidia/"].mk-tile' },
	{ name: 'card→card', from: '/pl/karty/rtx-3090/', link: 'main a[href="/pl/karty/rtx-4060-ti-16/"]' }
];

const gz = new Map<string, Uint8Array>();
const TYPES: Record<string, string> = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.avif': 'image/avif', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg' };
const server = Bun.serve({
	hostname: '127.0.0.1',
	port: 0,
	async fetch(req) {
		const url = new URL(req.url);
		let path = join(ROOT, decodeURIComponent(url.pathname));
		if (!path.startsWith(ROOT)) return new Response('Forbidden', { status: 403 });
		if (url.pathname.endsWith('/')) path = join(path, 'index.html');
		const f = Bun.file(path);
		if (!(await f.exists())) return new Response('Not found', { status: 404 });
		const ext = extname(path);
		const headers: Record<string, string> = { 'content-type': TYPES[ext] ?? 'application/octet-stream', 'cache-control': url.pathname.startsWith('/_app/immutable/') || url.pathname.startsWith('/fonts/') ? 'public, max-age=31536000, immutable' : 'no-cache' };
		if (['.html', '.js', '.css', '.json', '.svg'].includes(ext)) {
			let body = gz.get(path);
			if (!body) gz.set(path, (body = Bun.gzipSync(new Uint8Array(await f.arrayBuffer()))));
			return new Response(body, { headers: { ...headers, 'content-encoding': 'gzip' } });
		}
		return new Response(f, { headers });
	}
});
const BASE = `http://127.0.0.1:${server.port}`;

const browser: Browser = await puppeteer.launch({
	executablePath: resolve(import.meta.dir, '../../../.tools/chrome-swgl'),
	headless: true,
	args: ['--no-sandbox', '--hide-scrollbars', `--user-data-dir=/tmp/qa-perf-${process.pid}`]
});

const med = (xs: number[]) => {
	const s = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
	return s.length ? s[Math.floor((s.length - 1) / 2)] : NaN;
};

async function fresh(cpu: number): Promise<[Page, () => Promise<void>]> {
	const ctx = await browser.createBrowserContext();
	const page = await ctx.newPage();
	await page.setViewport({ width: 1366, height: 768, deviceScaleFactor: 1 });
	const cdp = await page.createCDPSession();
	await cdp.send('Emulation.setCPUThrottlingRate', { rate: cpu });
	if (process.env.RM === '1') await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
	await page.evaluateOnNewDocument(() => {
		const w = window as unknown as Record<string, unknown>;
		const lt: { s: number; d: number }[] = (w.__lt = []) as never;
		const sh: { t: number; v: number }[] = (w.__cls = []) as never;
		w.__lcp = 0;
		new PerformanceObserver((l) => l.getEntries().forEach((e) => lt.push({ s: e.startTime, d: e.duration }))).observe({ type: 'longtask', buffered: true });
		new PerformanceObserver((l) => l.getEntries().forEach((e) => (w.__lcp = e.startTime))).observe({ type: 'largest-contentful-paint', buffered: true });
		new PerformanceObserver((l) =>
			l.getEntries().forEach((e) => {
				const x = e as unknown as { hadRecentInput: boolean; value: number };
				if (!x.hadRecentInput) sh.push({ t: e.startTime, v: x.value });
			})
		).observe({ type: 'layout-shift', buffered: true });
		const ev: { name: string; s: number; d: number }[] = (w.__ev = []) as never;
		new PerformanceObserver((l) => l.getEntries().forEach((e) => ev.push({ name: e.name, s: e.startTime, d: e.duration }))).observe({ type: 'event', buffered: true, durationThreshold: 16 } as PerformanceObserverInit);
	});
	return [page, () => ctx.close()];
}

type Load = { lcp: number; cls: number; tbt: number; js: number };
async function load(path: string): Promise<Load> {
	const [page, close] = await fresh(4);
	await page.goto(BASE + path, { waitUntil: 'load', timeout: 90000 });
	await Bun.sleep(5000);
	const r = await page.evaluate(() => {
		const w = window as unknown as { __lt: { s: number; d: number }[]; __cls: { t: number; v: number }[]; __lcp: number };
		const fcp = performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0;
		const tbt = w.__lt.filter((t) => t.s + t.d > fcp).reduce((a, t) => a + Math.max(0, t.d - 50), 0);
		let cls = 0, cur = 0, ws = -1e9, last = -1e9;
		for (const s of w.__cls) {
			if (s.t - last > 1000 || s.t - ws > 5000) (cur = 0), (ws = s.t);
			cur += s.v;
			last = s.t;
			cls = Math.max(cls, cur);
		}
		const js = (performance.getEntriesByType('resource') as PerformanceResourceTiming[]).filter((e) => /\.js(\?|$)/.test(e.name)).reduce((a, e) => a + e.transferSize, 0);
		return { lcp: w.__lcp, cls, tbt, js: js / 1024 };
	});
	await close();
	return r;
}

type Nav = { input: number; content: number; ready: number; longMax: number; longSum: number };
async function nav(n: (typeof NAVS)[number], cpu: number): Promise<Nav> {
	const [page, close] = await fresh(cpu);
	await page.goto(BASE + n.from, { waitUntil: 'load', timeout: 90000 });
	await Bun.sleep(2500);
	const a = await page.waitForSelector(n.link, { timeout: 10000 });
	await a!.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
	await Bun.sleep(1200);
	await page.evaluate(() => {
		const w = window as unknown as Record<string, unknown>;
		const h1 = () => document.querySelector('main h1')?.textContent ?? '';
		const old = h1();
		addEventListener(
			'pointerdown',
			() => {
				const t0 = performance.now();
				const r: Record<string, number> = (w.__nav = { t0 }) as never;
				const poll = () => {
					const now = performance.now();
					if (now - t0 > 8000) return;
					if (!r.content && h1() !== old) r.content = now - t0;
					if (r.content && !r.ready) {
						const el = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
						if (el && el !== document.documentElement) {
							const s = performance.now();
							setTimeout(() => {
								if (!r.ready && performance.now() - s < 50) r.ready = s - t0;
							}, 0);
						}
					}
					if (!r.ready) setTimeout(poll, 8);
				};
				poll();
			},
			{ capture: true, once: true }
		);
	});
	const box = (await a!.boundingBox())!;
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 4 });
	await Bun.sleep(120);
	await page.mouse.down();
	await page.mouse.up();
	await Bun.sleep(4000);
	const r = await page.evaluate(() => {
		const w = window as unknown as { __nav: Record<string, number>; __lt: { s: number; d: number }[]; __ev: { name: string; s: number; d: number }[] };
		const t0 = w.__nav.t0;
		const lt = w.__lt.filter((t) => t.s >= t0 - 5 && t.s < t0 + 3000);
		const ev = w.__ev.filter((e) => e.s >= t0 - 5 && e.s < t0 + 1000 && /pointer|click|mouse/.test(e.name));
		return { input: Math.max(0, ...ev.map((e) => e.d)), content: w.__nav.content ?? NaN, ready: w.__nav.ready ?? NaN, longMax: Math.max(0, ...lt.map((t) => t.d)), longSum: lt.reduce((x, t) => x + t.d, 0) };
	});
	await close();
	return r;
}

const out: Record<string, unknown> = { root: ROOT, runs: RUNS };
const loads: Record<string, Load> = {};
for (const p of process.env.LOAD === '0' ? [] : PAGES) {
	const rs: Load[] = [];
	for (let i = 0; i < RUNS; i++) rs.push(await load(p));
	loads[p] = { lcp: med(rs.map((r) => r.lcp)), cls: med(rs.map((r) => r.cls)), tbt: med(rs.map((r) => r.tbt)), js: med(rs.map((r) => r.js)) };
	console.log(`load ${p.padEnd(44)} LCP ${loads[p].lcp.toFixed(0).padStart(5)} ms  CLS ${loads[p].cls.toFixed(3)}  TBT(4×) ${loads[p].tbt.toFixed(0).padStart(5)} ms  JS ${loads[p].js.toFixed(1)} kB`);
}
out.loads = loads;
const navs: Record<string, Nav> = {};
for (const n of NAVS)
	for (const cpu of [1, 4]) {
		const rs: Nav[] = [];
		for (let i = 0; i < RUNS; i++) rs.push(await nav(n, cpu));
		const k = `${n.name} @${cpu}×`;
		navs[k] = { input: med(rs.map((r) => r.input)), content: med(rs.map((r) => r.content)), ready: med(rs.map((r) => r.ready)), longMax: med(rs.map((r) => r.longMax)), longSum: med(rs.map((r) => r.longSum)) };
		const v = navs[k];
		console.log(`nav  ${k.padEnd(20)} input ${v.input.toFixed(0).padStart(4)} ms  content ${v.content.toFixed(0).padStart(5)} ms  ready ${v.ready.toFixed(0).padStart(5)} ms  longtask max ${v.longMax.toFixed(0)} / sum ${v.longSum.toFixed(0)} ms`);
	}
out.navs = navs;
if (process.env.JSON) await Bun.write(process.env.JSON, JSON.stringify(out, null, 2));
await browser.close();
server.stop(true);
