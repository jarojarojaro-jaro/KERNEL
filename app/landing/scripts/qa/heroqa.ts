/**
 * Hero QA: N fresh loads per viewport (fresh browser context each time = cold cache), with CPU
 * throttling and slowed network for some runs. At T ms after navigation it records the screenshot
 * and a completeness probe:
 *   - no hydration warnings / page errors,
 *   - headline and race panel visible (computed opacity ≥ 0.95 after animations, in viewport),
 *   - both lanes show a t/s value and the gauges have their needles.
 * Writes PNGs + a contact sheet (HTML rendered to PNG) into OUT.
 */
import puppeteer from 'puppeteer-core';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = process.env.BASE ?? 'http://127.0.0.1:18433';
const OUT = process.env.OUT ?? '/home/jaro/KERNEL/app/screens/v2/hero-qa';
const N = Number(process.env.N ?? 10);
const T = Number(process.env.T ?? 1500);
const URL_ = process.env.URL_ ?? '/pl/';
mkdirSync(OUT, { recursive: true });

const VPS = [
	{ name: '1920', width: 1920, height: 1080, deviceScaleFactor: 1 },
	{ name: '1536@1.25', width: 1536, height: 864, deviceScaleFactor: 1.25 },
	{ name: '1440', width: 1440, height: 900, deviceScaleFactor: 1 },
	{ name: '390', width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true }
];
// Load conditions cycle: normal, CPU 4×, CPU 6×, slow network (fonts late), JS disabled.
const CONDS = [
	{ name: 'normal' },
	{ name: 'cpu4', cpu: 4 },
	{ name: 'cpu6', cpu: 6 },
	{ name: 'slownet', net: { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 } },
	{ name: 'nojs', nojs: true }
];

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18499', defaultViewport: null });
const rows: { vp: string; i: number; cond: string; ok: boolean; why: string[]; img: string }[] = [];

for (const vp of VPS) {
	for (let i = 0; i < N; i++) {
		const cond = CONDS[i % CONDS.length];
		const ctx = await browser.createBrowserContext();
		const page = await ctx.newPage();
		const msgs: string[] = [];
		page.on('console', (m) => {
			if (m.type() === 'warning' || m.type() === 'error') msgs.push(m.text().slice(0, 200));
		});
		page.on('pageerror', (e) => msgs.push('pageerror ' + e.message));
		await page.setViewport(vp);
		const cdp = await page.createCDPSession();
		if (cond.cpu) await cdp.send('Emulation.setCPUThrottlingRate', { rate: cond.cpu });
		if (cond.net) {
			await cdp.send('Network.enable');
			await cdp.send('Network.emulateNetworkConditions', cond.net);
		}
		if (cond.nojs) await page.setJavaScriptEnabled(false);
		// consent stored so the banner does not cover the hero (separate check covers the banner)
		await page.evaluateOnNewDocument(() => {
			try {
				localStorage.setItem('consent', JSON.stringify({ v: 1, analytics: false, at: new Date().toISOString() }));
			} catch {}
		});
		const t0 = Date.now();
		await page.goto(BASE + URL_, { waitUntil: 'domcontentloaded', timeout: 60000 });
		const wait = T - (Date.now() - t0);
		if (wait > 0) await Bun.sleep(wait);
		const probe = await page.evaluate(() => {
			const why: string[] = [];
			const vis = (el: Element | null, label: string) => {
				if (!el) return why.push(`${label}: missing`);
				let o = 1;
				for (let n: Element | null = el; n; n = n.parentElement) o *= Number(getComputedStyle(n).opacity);
				const r = el.getBoundingClientRect();
				if (o < 0.95) why.push(`${label}: opacity ${o.toFixed(2)}`);
				if (r.width < 2 || r.height < 2) why.push(`${label}: zero size`);
				if (r.top > innerHeight * 1.6) why.push(`${label}: far below (${Math.round(r.top)})`);
			};
			const h1 = document.querySelector('#hero-title, .hero h1');
			vis(h1, 'headline');
			if (h1 && !/szybciej|faster/i.test(h1.textContent ?? '')) why.push('headline text incomplete');
			// every glyph of the headline fully drawn
			const glyphs = h1 ? [...h1.querySelectorAll<HTMLElement>('.ch')] : [];
			const faded = glyphs.filter((g) => Number(getComputedStyle(g).opacity) < 0.95).length;
			if (faded) why.push(`headline glyphs faded: ${faded}`);
			const race = document.querySelector('#hero-race, .hero .race');
			vis(race, 'race');
			const svgs = race ? race.querySelectorAll('svg').length : 0;
			if (svgs < 2) why.push(`race gauges: ${svgs} svg`);
			const nums = race ? (race.textContent ?? '').match(/\d+[,.]\d/g) ?? [] : [];
			if (nums.length < 2) why.push(`race numbers: ${nums.length}`);
			return why;
		});
		const img = `${OUT}/${vp.name.replace('@', '-dpr')}-${String(i).padStart(2, '0')}-${cond.name}.png`;
		await page.screenshot({ path: img });
		const why = [...probe, ...msgs.filter((m) => /hydration|pageerror|Error/i.test(m))];
		rows.push({ vp: vp.name, i, cond: cond.name, ok: why.length === 0, why, img });
		console.log(vp.name, i, cond.name, why.length ? 'FAIL ' + why.join('; ') : 'ok');
		await ctx.close();
	}
}

// contact sheet
const pass = rows.filter((r) => r.ok).length;
const html = `<html><body style="margin:0;background:#111;color:#ddd;font:12px monospace">
<h1 style="margin:12px">Hero QA ${URL_} at ${T} ms after navigation — ${pass}/${rows.length} pass</h1>
${VPS.map((vp) => `<div style="display:flex;flex-wrap:wrap;gap:6px;padding:6px">${rows
	.filter((r) => r.vp === vp.name)
	.map((r) => `<figure style="margin:0;width:${vp.name === '390' ? 150 : 300}px"><img src="file://${r.img}" style="width:100%;border:3px solid ${r.ok ? '#2a6' : '#d33'}"><figcaption>${r.vp} #${r.i} ${r.cond} ${r.ok ? 'OK' : 'FAIL: ' + r.why.join('; ')}</figcaption></figure>`)
	.join('')}</div>`).join('')}
</body></html>`;
writeFileSync(`${OUT}/sheet.html`, html);
const ctx = await browser.createBrowserContext();
const p = await ctx.newPage();
await p.setViewport({ width: 1600, height: 900 });
await p.goto(`file://${OUT}/sheet.html`, { waitUntil: 'load' });
await p.screenshot({ path: `${OUT}/contact-sheet.png`, fullPage: true });
await ctx.close();
writeFileSync(`${OUT}/result.json`, JSON.stringify({ url: URL_, t: T, pass, total: rows.length, rows }, null, 1));
console.log(`PASS ${pass}/${rows.length}`);
await browser.disconnect();
