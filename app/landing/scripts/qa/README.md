# QA scripts (puppeteer-core over CDP, CPU-only Chrome)

Start Chrome: `~/KERNEL/app/.tools/chrome-swgl --headless=new --no-sandbox --user-data-dir=/tmp/swgl-cdp --remote-debugging-port=18499 --remote-debugging-address=127.0.0.1 about:blank`.
Install once in a scratch dir: `bun add puppeteer-core@24`, then copy these files there.

| Script | What it checks |
|---|---|
| `hyd.ts <urls>` | hydration / console warnings per page (`BASE`, `ONE=1` for a single viewport; against the dev server it also reports invalid HTML placement) |
| `heroqa.ts` | 10 fresh loads × 4 viewports under normal / CPU 4× / CPU 6× / slow network / no JS; hero complete 1.5 s after navigation; contact sheet in `screens/v2/hero-qa/` |
| `axe.ts <urls>` | axe-core WCAG 2.x A/AA + best-practice, console errors, horizontal scroll, at 1280 and 390 |
| `shots.ts` | every home section and subpage, PL, 1440 + 390, into `OUT` |
