import puppeteer from 'puppeteer-core';
const AXE = await Bun.file('/home/jaro/KERNEL/app/.tools/axe/package/axe.min.js').text();
const BASE = 'http://127.0.0.1:18433';
const PAGES = process.argv[2].split(',');
const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18499', defaultViewport: null });
let bad = 0;
for (const vp of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
	const ctx = await browser.createBrowserContext();
	const page = await ctx.newPage();
	await page.setViewport(vp);
	await page.evaluateOnNewDocument(() => localStorage.setItem('consent', JSON.stringify({ v: 1, analytics: false, at: new Date().toISOString() })));
	for (const u of PAGES) {
		const errs: string[] = [];
		const onC = (m: import('puppeteer-core').ConsoleMessage) => ['error', 'warn', 'warning'].includes(m.type()) && errs.push(m.text().slice(0, 150));
		page.on('console', onC);
		await page.goto(BASE + u, { waitUntil: 'networkidle0' });
		await page.evaluate(async () => {
			for (let y = 0; y < document.body.scrollHeight; y += innerHeight * 0.8) {
				scrollTo(0, y);
				await new Promise((r) => setTimeout(r, 100));
			}
			scrollTo(0, 0);
		});
		await Bun.sleep(2500);
		await page.evaluate(AXE);
		const v = await page.evaluate(async () => (await (window as unknown as { axe: { run: (d: Document, o: object) => Promise<{ violations: { id: string; nodes: { target: string[] }[] }[] }> } }).axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] })).violations.map((x) => `${x.id}: ${x.nodes[0].target.join(' ')}`));
		const h = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
		page.off('console', onC);
		if (v.length || errs.length || h > 0) {
			bad++;
			console.log(vp.width, u, JSON.stringify({ v, errs, h }));
		}
	}
	await ctx.close();
}
console.log(`pages with issues: ${bad} of ${PAGES.length * 2}`);
await browser.disconnect();
