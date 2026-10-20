# Performance budget

Measured on the static build with `bun run qa:perf` (`scripts/qa/perf.ts`): CPU-only headless Chrome
(chrome-swgl, software compositing, no GPU), 1366×768, localhost, medians of 3 runs. A real desktop
browser with a GPU is faster; the budget is set for this pessimistic setup so it holds on weak laptops.

| Metric | Budget | How it is measured |
|---|---|---|
| LCP | < 1000 ms | fresh context, CPU 4× |
| CLS | < 0.02 | largest 5 s session window |
| TBT | < 200 ms (home < 400 ms) | long tasks over 50 ms from FCP to 5 s after load, CPU 4× |
| JS transferred | < 150 kB gzip per page | every `.js` resource until 5 s after load |
| Navigation: content | < 200 ms at CPU 1× | click → the new page's `<h1>` is in the DOM |
| Navigation: ready | < 500 ms at CPU 1× | click → new page hit-testable under the pointer and the main thread free (a posted task runs within 50 ms) |
| Navigation: input | ≈ the page's no-op click floor | Event Timing duration of the click (click → next paint). A click that does nothing on `/pl/karty/` already measures ≈ 64 ms here: that is the software compositor, not the page |

Paths measured: home, `/karty/`, a maker page, a card page, the compare page, `/methodology/`, `/start/`,
plus tile → maker page and card → card navigation at CPU 1× and 4×.

## Run

```sh
bun run build                       # under flock /tmp/landing-build.lock, nice -n 10
bun run qa:perf                     # ./build, everything (~4 min)
ROOT=/tmp/old-build bun run qa:perf # another build, e.g. a copy taken before a change
PAGES=/pl/,/pl/karty/ LOAD=1 NAVS=0 RUNS=5 JSON=out.json bun run qa:perf
RM=1 LOAD=0 bun run qa:perf         # reduced motion: no view transition; the difference is its cost
```

For a cause, take a trace in the same Chrome (`page.tracing.start` with `devtools.timeline`,
`disabled-by-default-devtools.timeline`) and group main-thread events inside long tasks; the CDP
`LayerTree` domain lists compositing layers and their reasons.

## Rules that keep it there

- **View transitions never hold the page.** The cards explorer does not capture `:root`
  (`view-transition-name: none`) and `::view-transition` has `pointer-events: none`: the new page is
  on screen and clickable at once, only the named pieces fly (≤ 0.4 s). A captured root swallows every
  click until the animation ends (it did: the new page was clickable only ~1 s after the click).
- **No permanent layers for decoration.** `will-change` / `translate3d` only on a few big moving
  things, never per item (the odometer drums were 2 layers each: 163 layers on a card page, now 34).
  One-shot effects (the hero bloom) leave the DOM when their animation ends.
- **Small DOM per repeated widget.** An odometer reel is one text node, not 11 spans.
- **Loops pause off screen** (`visible` action, `onFrame` ticker) and on a hidden tab.
- **Format numbers through `num()`** (`$lib/i18n`): it reuses one `Intl.NumberFormat` per
  (language, digits); `toLocaleString` with options builds a new formatter on every call.
- Preload: `data-sveltekit-preload-data="hover"` on `<body>` (code and data load on hover/touchstart).
- Fonts: three subset woff2 files, preloaded, `font-display: swap`.
- Images: `ProductPhoto` sets `width`/`height`, `decoding="async"`, `loading="lazy"` and `sizes`;
  only the first-screen photo is `eager` + `fetchpriority="high"`.
