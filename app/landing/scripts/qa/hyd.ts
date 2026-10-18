import puppeteer from 'puppeteer-core';
const BASE = process.env.BASE ?? 'http://127.0.0.1:18433';
const urls = (process.argv[2] ?? '/pl/').split(',');
const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18499', defaultViewport: null });
const ctx = await browser.createBrowserContext();
const page = await ctx.newPage();
const msgs: string[] = [];
page.on('console', (m) => msgs.push(`${m.type()}: ${m.text().slice(0, 600)}`));
page.on('pageerror', (e) => msgs.push(`pageerror: ${e.message}`));
for (const [w, h, d] of (process.env.ONE ? [[1366, 768, 1]] : [[1536, 864, 1.25], [1366, 768, 1], [390, 844, 2]]) as [number, number, number][]) {
	await page.setViewport({ width: w, height: h, deviceScaleFactor: d });
	for (const u of urls) {
		msgs.length = 0;
		await page.goto(BASE + u, { waitUntil: 'load', timeout: 60000 });
		await page.evaluate(() => console.warn('PROBE'));
		await Bun.sleep(2500);
		console.log(w, u, JSON.stringify(msgs.filter((m) => !m.startsWith('debug'))));
	}
}
await ctx.close();
await browser.disconnect();
