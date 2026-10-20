# v2 redesign: creative brief („Białe ciepło”)

Status: in progress, 2026-10-16. The v1 page (`screens/landing-pl-dark-desktop.png`) was dense, text-heavy and uniform. v2 is a launch page for a performance product, not a SaaS template.

## 1. Concept: speed is heat

The page is a dark test cell. Everything slow is **cold**: steel, graphite, quiet type. Everything our engine does **heats up**: the needle sweeps into the redline, the bar glows, the counter turns white-hot. Heat is the only colour that carries meaning, and it means one thing: tokens per second.

One idea per screen:

1. **Hero:** the race. Same card, same model, the same answer written twice at the measured speeds.
2. **Skan:** we read your card.
3. **Dobór:** the model that fits drops into VRAM.
4. **Przyspieszenie:** the layers stack up and the speed climbs.
5. **Wyniki:** pick your GPU and model, and watch it replay.
6. **Jak to możliwe:** 1956 kernels per token collapse to 795.
7. **Jakość:** the same model and the same quality, measured with KLD.
8. **Twoja karta:** the cards explorer.
9. **CTA:** redline.

## 2. Moodboard

Each reference is listed with what we take from it.

| Reference | What we take |
|---|---|
| [Apple MacBook Pro / M-chip pages](https://www.apple.com/macbook-pro/) | One huge number per screen; scroll-pinned scenes; chip "scan" reveals |
| [Linear](https://linear.app/) | Restraint, grain-on-black depth, precise hairlines |
| [Vercel Ship](https://vercel.com/ship) | Kinetic, big type, cursor-reactive light |
| [Raycast](https://www.raycast.com/) | Tactile controls, keyboard-first, glowing key caps |
| [Nothing](https://nothing.tech/) | Dot-matrix and mono details, industrial labels |
| [Teenage Engineering](https://teenage.engineering/) | Instrument-like UI, orange as a signal only, labels as design |
| [Porsche Taycan](https://www.porsche.com/international/models/taycan/) / F1 telemetry overlays | Tachometer, redline, lap delta, odometer digits |
| [Rimac Nevera](https://www.rimac-automobili.com/nevera/) | Dark-on-dark product renders, light sweeps over hardware |

## 3. Type

| Role | Font | Why |
|---|---|---|
| Display + text | **Mona Sans** (GitHub, OFL 1.1), variable `wght 200–900`, `wdth 75–125` | The width axis is the kinetic device: headlines stretch wide as they "accelerate". It has a grotesk with character and full Polish diacritics. |
| Numbers, labels | **Martian Mono** (Evil Martians, OFL 1.1), variable `wght 100–800`, `wdth 75–112.5` | Instrument feel, tabular figures, condensed width for dense HUD labels. |

Both fonts are self-hosted from `static/fonts/` (no Google Fonts requests: GDPR), and the hero weight is preloaded. Geist is removed.

Scale:

- display: `clamp(3.2rem, 9vw, 10rem)`, `wdth 112–125`, weight 800;
- section titles: `clamp(2.4rem, 5.5vw, 6rem)`;
- lead: 1.25–1.5rem;
- body: 1.0625rem;
- labels: Martian Mono 0.72rem, uppercase, tracking 0.08em.

## 4. Palette

Deep blacks with real depth come from layered radial gradients, film grain (SVG turbulence, 4% opacity) and 1px hairlines. There is no glass except the sticky header.

| Token | Value | Use |
|---|---|---|
| ink-0 | `#050506` | page |
| ink-1 | `#0B0B0D` | raised |
| ink-2 | `#141417` | panels |
| ink-3 | `#1E1E23` | controls |
| line | `#26262C` | hairlines |
| bone | `#EDEAE3` | text-hi (18.9:1) |
| ash | `#A9A6A0` | text (8.4:1) |
| smoke | `#86837E` | mute (5.4:1) |
| cold | `#6E7C8C` | "before" / upstream (4.7:1) |

The heat ramp is used ONLY to mean speed:

`#1E3448` (cold) → `#7A2E1F` → `#E2401C` (red) → `#FF7A1A` (orange) → `#FFC15A` (amber) → `#FFF3D6` (white-hot)

- CTAs are bone on ink (or ink on bone), never heat.
- Focus ring: bone 2px plus an ink 2px offset.
- No purple and no blue gradients. The one cold tone is a desaturated steel used for "before".

The home page is always dark, because the cinematic hero has no light variant. Other pages keep the light/dark toggle through `tokens.css`.

## 5. Motion principles

1. **Motion explains.** Every animation is a measurement being replayed (race at real t/s, counters, needles) or a step of the process (scan, drop, stack). Nothing floats for decoration.
2. **Physics:**
   - needles use a damped spring with a little overshoot;
   - counters roll like odometer drums;
   - blocks drop with gravity and a short settle.
3. **Composited only.** Animations use `transform` and `opacity`. Canvas/WebGL caps devicePixelRatio at 1.5 and renders the shader at half resolution. It pauses offscreen (IntersectionObserver) and when the tab is hidden (`visibilitychange`).
4. **Scroll-driven:**
   - CSS `animation-timeline: view()` / `scroll()` where supported;
   - otherwise a single rAF-throttled scroll listener sets `--p` (0..1) per scene;
   - no scroll hijacking: sticky scenes are ordinary tall sections.
5. **Reduced motion:** every scene renders its final state statically. The race shows final numbers and both finished answers; replay is opt-in.
6. **Durations:**
   - micro 120–180 ms;
   - reveals 600–900 ms with `cubic-bezier(.16,1,.3,1)`;
   - stagger 40–60 ms per glyph or line.

## 6. Hero storyboard (desktop 1440 × 900)

The comparison uses only same-harness numbers: RTX 3090, Qwen3.8-27B UD-Q4_K_XL, spec_sweep, T=1, 400-token answers. A0 is the typical app at 38.9 t/s and ours is 78.0 t/s (`BENCHMARKI-NVIDIA-2026-10-16.md:28`).

| t | Frame |
|---|---|
| 0.00 s | Black with grain. The heat shader fades in at 0 → 35% (a dim ember field low in the frame). Overline "RTX 3090 · Qwen3.8-27B · zmierzone" types in. |
| 0.10–0.60 s | „Ten sam sprzęt.” Each glyph rises 0.4em from a mask, weight 300 → 800, width 75 → 100, 35 ms stagger. |
| 0.35–0.85 s | „Ten sam model.” Same treatment. |
| 0.70–1.40 s | „Po prostu szybciej.” Width animates 75 → 125 (the line literally widens, as if accelerating). The fill is the heat ramp; a speed streak passes through it once. |
| 0 s (layout) | One full screen (100svh). The token highway (`fx/Highway`, one 2D canvas) runs full bleed behind everything, out from under the headline (the far rows sit behind it) toward the viewer. The headline sits around the vertical middle on a soft dark halo with a deep shadow, CTAs right under it; at the near end two glass windshields (left steel „Typowa aplikacja”, right ember „Podkręt”), each with its own speedometer on the outer edge (`fx/Dial`, one scale 0–140: steel needle at 35,9, ember needle at 114,8) and „3,2× szybciej” in big heat numerals between the windshields; the small print at the very bottom. The headline is larger (min(11vw, 17svh, 9rem), the steel line 0,4 of it). |
| 1.20 s | The drive rises in, full bleed under the CTAs: the token highway (`fx/Highway`, one 2D canvas) as a race on our lab card (RX 7900 XTX × Qwen3.8-27B, one script, ABBA). Both lanes write the same text in answers of 500 tokens (the demo length, stated in the small print) at the measured median: „Typowa aplikacja” 35,9 t/s (steel, dim, crawling dashes) vs „Podkręt” 114,8 t/s (ember). The newest row is written at the horizon and the road moves one row per row written, so everything on our road comes 3,2× as often: the cross lines of a faint perspective grid on the open ground beside each lane, the long white-hot edge dashes, the chequered finish line after every answer. Ours only: rows smear back up the road and flare white-hot near the camera, warp streaks fly out of the vanishing point over the lane, the field of view glows warm on the right while the typical side sits in shade. Windshields at the lanes' near ends: name, answer number, live counter „412 / 500 tokenów”, progress bar and the current answer itself, readable, written token by token behind a caret (four lines, newest at the bottom; a new answer starts an empty panel); a stamp „Gotowe · 4,4 s” / „Gotowe · 13,9 s” (500 ÷ measured t/s) flashes once per finished answer. Streaks fly out of the vanishing point over the whole screen (the typical side few, steel, slow; ours many, ember, fast; three depths for parallax). |
| page idle + cluster on screen | The race starts at 0 / 500 on both lanes; both gauges make their one entrance (arcs sweep, needles swing, the factor counts up, heat-field flare, one bloom). Ours finishes at 4,4 s and starts answer 2; the typical app finishes at 13,9 s, by then ours is on answer 4. The lanes loop independently; nothing resets. No pulse; only a ±0,3 t/s needle jitter. |
| then, nonstop | The highway keeps flowing (`home/stream/*.ts`, a lazy chunk per language). Pause bottom right; off screen the loop sleeps and continues where it was. Server HTML, no JS and reduced motion: the moment the slower answer is done, both chips „500 / 500” with their finish times (4,4 s vs 13,9 s), one still road frame, the final dial. |

The cursor moves a faint heat light across the shader. In the headline, a radial highlight follows the cursor (CSS `--mx/--my`).

Mobile 390 (≤ 900 px): the headline in the upper half; right under the CTAs the two windshields stacked (three lines each), so the first screen shows the headline and both answers being written; then the two gauges side by side with the speed-up between them, the small print last.

## 7. Scroll scenes

1. **Skan** (sticky, 250vh):
   - a stylised RTX 3090 (SVG: shroud, two fans, PCB edge, 12 memory packages) is swept by a light bar driven by `--p`;
   - four spec callouts pop at p = .25/.4/.55/.7: 24 GB, 936 GB/s, 300 W, Ampere sm_86.
2. **Dobór** (sticky, 250vh):
   - a horizontal VRAM bar of 24 GB;
   - blocks drop in: the Qwen3.8-27B weights (17.6 GB file, 19.5 GB used by our engine at 64k context) → „pasuje”;
   - a ghost Q8_0 block (29.05 GB) hits the bar's end and bounces → „nie pasuje”.
3. **Przyspieszenie** (sticky, 300vh): three glowing segments stack up:
   - L0, typowa aplikacja: 38.9;
   - L1, najlepsze flagi + MTP: 63.3;
   - nasz silnik: 78.0.

   The giant counter climbs at each layer and the segment colour heats along the ramp.

## 8. Interaction kit

| Element | Behaviour |
|---|---|
| Magnetic buttons | translate ≤ 6px toward the cursor; fine pointers only |
| Hover-tilt cards | ≤ 6° tilt with a glare gradient following the cursor; disabled under reduced motion |
| Cursor glow | one fixed radial light, `mix-blend-mode: screen`, fine pointers only |
| Picker | radio-group semantics, arrow keys, visible focus |
| Source popovers | every number has an "źródło" tip (file:line plus conditions), reachable with the keyboard |

## 9. Honesty rules carried into the design

- Every number comes from `src/lib/data/measurements.ts`. That module reads the cards registry generated from `product/BENCHMARKI-NVIDIA-2026-10-16.md` and the cloud scorecards, and every value keeps its file:line.
- The race and the bars only compare numbers from the same script.
- Where scripts differ (the RX 7900 XTX), the UI says so next to the number.
- No "bit w bit" claim. The claim is „Ten sam model, ta sama jakość — zmierzone” (KLD within upstream noise on the 3060), linked to the methodology.
- GSAP is not used. Its "Standard no-charge" licence would allow it, but native CSS, Web Animations and rAF are enough.

## 10. Critique rounds

See §11 (filled in after each round).

## 11. Scores

| Round | WOW | Originality | Polish | Notes |
|---|---|---|---|---|
| 1 | 6 | 6 | 4 | The race doesn't own the hero (small gauges; the headline appears late, after the lede). Numbers are inconsistent across pages (XTX 109 vs 1,7×; ×2,00 vs 2,0×; hero lane times vs the 500-word HUD). Explorer grid has empty-state bugs and the queue page has no estimate. Pricing/FAQ follow a template rhythm and include dev copy. Scroll-scene overflow and odometer half-digits. Screens: `screens/v2/r1/`. |
| 2 | 6 | 6 | 5.5 | Hero race reads as a dashboard, not a spectacle. Redline (80) is never reached by 78,0, against a promised 70. Race text is unreadable (lines cut, no fade). Heat colour also used for non-speed things (VRAM block, kernel dots, selected chips). Multiplier/precision/unit inconsistency (2,0× ×4 styles; GiB vs GB; PL dot decimals). Quality/engine are weak, and the two-line headline became a habit. Global `.bar` class collided with the header (rounded band), fixed by the main agent. Screens: `screens/v2/r2/`. |
| 3 | 6.5 | 6 | 5.5 | Hero t3 is striking, but the page gets quieter after the hero. The race answer window is too small and the 2,0× stamp covers text. The middle sections are flat (small VRAM bar; static-looking dot grid; outlined "KLD" contours). The headline device is overused. Charts send mixed signals (Bonsai KLD outside the drawn noise band under a "within noise" badge; hatching carries 4 meanings; red arc starts at ~80 while "70" is red). Collisions on mobile and in the explorer. Lighthouse mobile /pl/: 52 (LCP 4.5 s, TBT 1.8 s on SwiftShader). Screens: `screens/v2/r3/`. |
| 4 | 6 | 6 | 6 | After the user's review: live-feed race, pair switcher, auto-play scenes, results subpage, vendor gallery, bento detail pages, model colours. Juror: the race doesn't read as a race in still frames (right lane restarts; opens on the 1.5× pair; small dials). Some scenes put key content under the glass header. Data-viz details (bars not on a shared zero; answer length stated four ways; LFM violet read as "purple"). Heat glow on a 1.05× gain. Detail redesign too timid. Screens: `screens/v2/r4/`, `before-detail/`, `after-detail/`. |
| 5 | 6.5 | 6 | 5.5 | After the user's hero, nav, section, onboarding and global-heat requests. Hero t3 is "a real SOTD moment", and the hero typography is "award-grade". Open: the scene-03 counter ended at 74,1 vs the 78,0 label (fixed after the round: it snaps to the measured value); content under the glass header in scan/boost; the race has no finish stamp and the gauges are small; onboarding/methodology/legal in the light theme break the concept; the quality legend doesn't match its markers. Screens: `screens/v2/r5/`. |
| 6 | 7 | 7 | 6 | After the crash/resume: fixed a site-wide `hydration_mismatch` (block popover inside `<p>` → remount, so counters and the race were blank/half-drawn in the user's browser); the hero intro is transform-only (QA 40/40 fresh loads incl. CPU 6×, slow network, no-JS); final values are in the SSR HTML everywhere; onboarding opens with its headline. Open: the race doesn't show the winner; live readouts above the median (80,2 vs 78,0); 4 display styles; light pages off-brand; empty onboarding result. Screens: `screens/v2/r6/`, `hero-qa/`. |
| 8 | 7 | 6 | 7 | Polish up (fit clipped, verdict slot, heat in the middle, results bars, home cards as gallery tiles). Open: mobile race stacks lanes so the fast lane is ~1450 px down; the gauge is reused 6×; one generic GPU drawing for every card; sticky headings still graze the nav in scan/boost/fit; quality needs a legend. "A second big moment after the hero" is needed for 8. Screens: `screens/v2/r8/`. |
| 9 | 6.5 | 6 | 6.5 | Measured-only hero digits, mobile race above the fold, cinematic full-stack scene, per-card GPU art, gauge only in the hero, quality without a legend, bit-exact final run-4 numbers. Open: a counter caught mid-roll, heat on the worse KLD number, multipliers everywhere. Screens: `screens/v2/r9/`. |
| 10 | 7 | 6 | 7 | Exact settled numbers, heat by gain, shared-scale result bars, scan callout ring, flat stack. Open: heat repetition, hero past the fold, mobile scan/boost/fit breakage, mixed number faces. Screens: `screens/v2/r10/`. |
| 11 | 7 | 6.5 | 7 | Hero fits the fold, mobile fixes, one figure face, one heat colour for every multiplier, gradient headlines only in hero and final. Open: the race shown three ways, boost still rolling 3.3 s after scroll (the timeline was 5 s), 4090 label crop. Screens: `screens/v2/r11/`. |
| 12 | 7 | 6 | 7 | Verdict only after both lanes finish, faster scan/boost (2.6/2.8 s), −59 % chip, results heat band, per-family GPU light and Ada silhouette. Open: the middle of the page repeats one layout; it wants a second set-piece, model colours vs heat palette, quality chart balance. Screens: `screens/v2/r12/`. |

**Status:** after 12 rounds the scores have plateaued at about 7 / 6–6.5 / 7 since round 6. The ≥ 8/8/8 target is not met. Later jurors partly contradict earlier ones and the user (heat on our number vs on the gap; model colours, which the user required, called off-palette; more heat vs less heat). The ≥ 8/8/8 target is not met; the work stopped at the session budget. The next round's fixes are the juror R4 list (`agent://LandingWow.JurorR4`, copied into REPORT.md).
