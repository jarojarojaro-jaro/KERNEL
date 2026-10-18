/** Screenshots of every home section and each subpage (PL, 1440 + 390) into OUT, from the build. */
import puppeteer from 'puppeteer-core';
import { mkdirSync } from 'node:fs';

const BASE = process.env.BASE ?? 'http://127.0.0.1:18433';
const OUT = process.env.OUT ?? '/home/jaro/KERNEL/app/screens/v2/r6';
mkdirSync(OUT, { recursive: true });
const VPS = [
	{ name: '1440', width: 1440, height: 900, deviceScaleFactor: 1 },
	{ name: '390', width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true }
];
const SECTIONS = ['scene-scan', 'scene-fit', 'scene-boost', 'engine', 'results', 'quality', 'cards', 'privacy'];
const PAGES: [string, string, number][] = [
	['/pl/wyniki/', 'wyniki', 3],
	['/pl/karty/', 'karty-gallery', 2],
	['/pl/karty/rtx-3090/', 'karty-3090', 5],
	['/pl/karty/rx-7900-xtx/', 'karty-7900xtx', 3],
	['/pl/karty/rtx-3060-12/', 'karty-3060', 2],
	['/pl/karty/rtx-4090/', 'karty-4090-queue', 1],
	['/pl/karty/porownaj/', 'karty-compare', 2],
	['/pl/start/', 'start-konto', 1],
	['/pl/start/paths/', 'start-droga', 1],
	['/pl/start/result/?gpu=rtx-3090', 'start-wynik', 2],
	['/pl/methodology/', 'methodology', 2],
	['/pl/legal/privacy/', 'legal', 1]
];
const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18499', defaultViewport: null });
for (const vp of VPS) {
	const ctx = await browser.createBrowserContext();
	const page = await ctx.newPage();
	await page.setViewport(vp);
	await page.evaluateOnNewDocument(() => {
		try {
			localStorage.setItem('consent', JSON.stringify({ v: 1, analytics: false, at: new Date().toISOString() }));
		} catch {}
	});
	const shot = (n: string) => page.screenshot({ path: `${OUT}/${n}-${vp.name}.png` });
	await page.goto(BASE + '/pl/', { waitUntil: 'load' });
	for (const t of [1, 3, 6]) {
		await Bun.sleep(t === 1 ? 1000 : t === 3 ? 2000 : 3000);
		await shot(`home-hero-t${t}`);
	}
	for (const id of SECTIONS) {
		await page.evaluate((id) => {
			const el = document.getElementById(id);
			if (el) scrollTo({ top: el.getBoundingClientRect().top + scrollY - 10, behavior: 'instant' });
		}, id);
		await Bun.sleep(700);
		await shot(`home-${id}-mid`);
		await Bun.sleep(2600);
		await shot(`home-${id}`);
	}
	for (const sel of ['.final', '#faq']) {
		await page.evaluate((sel) => {
			const el = document.querySelector(sel);
			if (el) scrollTo({ top: el.getBoundingClientRect().top + scrollY - 10, behavior: 'instant' });
		}, sel);
		await Bun.sleep(2600);
		await shot(`home-${sel.replace(/[.#]/, '')}`);
	}
	for (const [u, n, k] of PAGES) {
		await page.goto(BASE + u, { waitUntil: 'load' });
		for (let i = 0; i < k; i++) {
			if (i) await page.evaluate((y) => scrollTo({ top: y, behavior: 'instant' }), i * (vp.name === '390' ? 780 : 860));
			await Bun.sleep(i ? 2200 : 2600);
			await shot(`${n}-${i}`);
		}
	}
	await ctx.close();
	console.log('done', vp.name);
}
await browser.disconnect();
