<script lang="ts" module>
	export interface LiveLane {
		id: string;
		label: string;
		sub?: string;
		/** Measured decode speed (t/s, the median). */
		tps: number;
		hot: boolean;
		/** Measured tokens accepted per step (MTP); absent = one token per step. */
		burst?: number;
	}
</script>

<script lang="ts">
	/**
	 * The hero race, nonstop: two lanes, each a large speedometer beside the same long text being
	 * written. When the race starts (page idle, race on screen) both needles climb from 0 to their
	 * measured speed and stay there for as long as the page is open, breathing within ±3% of the
	 * median and ticking on each emitted step. Each lane writes the text at the speed its needle
	 * shows, so the long-run pace is exactly the measured median; the window follows the newest line
	 * smoothly. After the last paragraph the text simply goes on with the first one: no restarts,
	 * no pauses between answers. Pause is always available; off screen the loop sleeps and later
	 * continues where it was.
	 *
	 * Honesty: the digits show only the measured median; the needle's jitter is zero-mean (three
	 * sines), and tokens come in steps of `burst` (the measured MTP tokens accepted per step, a
	 * deterministic 3,3,4,… pattern with the measured mean). Text: the opening paragraph (`opening`,
	 * in the server HTML) and then the rest (`more`, a lazily loaded chunk), cut into token-sized
	 * pieces so the piece count matches TOK_PER_WORD (report 06 §2.1.2). The text is an example.
	 *
	 * DOM: only a few screens of text exist at any time. Pieces are appended ahead of the writing
	 * head in batches, and whole lines that scrolled out above the window are removed (greedy line
	 * breaking makes the lines below reflow identically), with the window shift corrected by the
	 * removed height. Line tops are cached when pieces are added, so a frame reads no layout:
	 * writing toggles a class, the window and the needles move by transform.
	 *
	 * SSR / no JS: needles on the median, the opening paragraph shown as written. With JS the dials
	 * read 0 and the opening is a dim preview until the race starts. Reduced motion: one static
	 * frame (needles on the median, the opening written), no loop.
	 */
	import { onMount, untrack } from 'svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFrame, reducedMotion, Spring, whenIdle } from './motion';
	import Speedo from './Speedo.svelte';

	let {
		lanes,
		opening,
		more,
		lang,
		max,
		redline,
		summary,
		onheat
	}: {
		lanes: LiveLane[];
		/** The text's first paragraph (server HTML). */
		opening: string;
		/** The rest of the text, paragraph by paragraph (loaded once the page is idle). */
		more?: () => Promise<string[]>;
		lang: 'pl' | 'en';
		max: number;
		redline: number;
		summary: string;
		onheat?: (hot: boolean) => void;
	} = $props();

	const L = {
		pl: { pause: 'Wstrzymaj wyścig', resume: 'Wznów wyścig', median: 'zmierzone' },
		en: { pause: 'Pause the race', resume: 'Resume the race', median: 'measured' }
	};
	const t = $derived(L[lang]);
	const step = $derived(max <= 120 ? 20 : max <= 250 ? 50 : 100);

	/** A paragraph as token-sized pieces (count ≈ words × TOK_PER_WORD). */
	function tokenize(text: string): string[] {
		const words = text.split(/\s+/).filter(Boolean);
		const chars = words.reduce((n, w) => n + w.length, 0);
		const per = chars / (words.length * TOK_PER_WORD[lang]);
		const out: string[] = [];
		for (const w of words) {
			const n = Math.max(1, Math.round(w.length / per));
			const size = Math.ceil(w.length / n);
			for (let i = 0; i < w.length; i += size) out.push(w.slice(i, i + size) + (i + size >= w.length ? ' ' : ''));
		}
		return out;
	}
	/** The opening, as rendered by the server (never re-rendered: the race owns these nodes). */
	// svelte-ignore state_referenced_locally
	const head = tokenize(opening);
	/** The whole text, paragraph by paragraph; grows once `more` has loaded. */
	let paras: string[][] = [head];

	/** Seconds the heat field runs hot when the race starts. */
	const HEAT_S = 2.6;
	/** Window follow time constant (s). */
	const FOLLOW = 0.08;
	/** Unwritten pieces kept laid out ahead of the head, and how many to add at a time. */
	const AHEAD = 90;
	const BATCH = 180;

	type Run = {
		els: HTMLElement[];
		/** Token cost per element: 1 = a piece, 0 = a paragraph break. */
		cost: number[];
		/** Cached line top per element (feed coordinates). */
		tops: number[];
		/** Elements written. */
		lit: number;
		/** Where the next appended piece comes from. */
		para: number;
		at: number;
		budget: number;
		acc: number;
		kick: number;
		spring: Spring;
		/** Window shift (px), its height, the line height and pieces per line (for the follow lead). */
		y: number;
		win: number;
		lineH: number;
		perLine: number;
	};

	let started = $state(false);
	let playing = $state(true);
	let onScreen = $state(false);
	let feeds: HTMLElement[] = $state([]);
	let dials: Speedo[] = $state([]);
	let runs: Run[] = [];
	let clock = 0;
	let heatOn = false;

	const topOf = (el: HTMLElement, cost: number, lineH: number) => (cost ? el.offsetTop - (lineH - el.offsetHeight) / 2 : el.offsetTop);

	function measure(i: number) {
		const r = runs[i];
		const f = feeds[i];
		if (!r || !f) return;
		r.lineH = parseFloat(getComputedStyle(f).lineHeight) || r.lineH;
		r.win = f.parentElement?.clientHeight ?? r.win;
		r.tops = r.els.map((el, j) => topOf(el, r.cost[j], r.lineH));
		const n = r.tops.length;
		const lines = n ? (r.tops[n - 1] - r.tops[0]) / r.lineH + 1 : 1;
		r.perLine = Math.max(1, n / lines);
	}
	/** Lay out `n` more elements of lane `i` after the last one (pieces, paragraph breaks). */
	function append(i: number, n: number) {
		const r = runs[i];
		const f = feeds[i];
		if (!r || !f) return;
		const frag = document.createDocumentFragment();
		const from = r.els.length;
		for (let c = 0; c < n; c++) {
			const toks = paras[r.para % paras.length];
			let el: HTMLElement;
			if (r.at >= toks.length) {
				el = document.createElement('span');
				el.className = 'br';
				r.cost.push(0);
				r.para = (r.para + 1) % paras.length;
				r.at = 0;
			} else {
				el = document.createElement('span');
				el.className = 'tk';
				el.textContent = toks[r.at++];
				r.cost.push(1);
			}
			frag.append(el);
			r.els.push(el);
		}
		f.append(frag);
		for (let j = from; j < r.els.length; j++) r.tops.push(topOf(r.els[j], r.cost[j], r.lineH));
	}
	/** Write `k` more pieces of lane `i` (paragraph breaks pass for free). */
	function emit(i: number, k: number) {
		const r = runs[i];
		while (k > 0 && r.lit < r.els.length) {
			r.els[r.lit].classList.add('on');
			k -= r.cost[r.lit++];
		}
		if (r.els.length - r.lit < AHEAD) append(i, BATCH);
	}
	/** Window shift that keeps the newest line near the bottom; the lead covers the follow lag. */
	function target(i: number) {
		const r = runs[i];
		const top = r.tops[Math.max(0, r.lit - 1)] ?? 0;
		const lead = ((Math.max(0, r.spring.x) * r.lineH) / r.perLine) * FOLLOW;
		return Math.max(0, top + r.lineH * 1.25 + lead - r.win);
	}
	function place(i: number) {
		const f = feeds[i];
		const r = runs[i];
		if (!f || !r) return;
		f.style.transform = r.y > 0.5 ? `translate3d(0, ${(-r.y).toFixed(1)}px, 0)` : '';
		// the top fades only once older lines scroll out (the first lines stay whole)
		f.parentElement?.classList.toggle('scrolled', r.y > 0.5);
	}
	/** Drop whole lines that scrolled out above the window (keeping two), then fix the shift. */
	function trim(i: number) {
		const r = runs[i];
		if (r.y < 6 * r.lineH) return;
		const cut = r.y - 2 * r.lineH;
		let n = 0;
		while (n < r.lit - 1 && r.tops[n] < cut) n++;
		if (n <= 0) return;
		for (let j = 0; j < n; j++) r.els[j].remove();
		const keep = r.els[n];
		const shift = r.tops[n] - topOf(keep, r.cost[n], r.lineH);
		r.els = r.els.slice(n);
		r.cost = r.cost.slice(n);
		r.tops = r.tops.slice(n).map((v) => v - shift);
		r.lit -= n;
		r.y -= shift;
		place(i);
	}

	/** Needle target: the median × (1 + 3% × m), m ∈ [−1, 1] from three sines (zero mean). */
	function readoutAt(i: number, time: number) {
		const p = i * 2.1 + 0.7;
		const m = 0.5 * Math.sin(time * 2.3 + p) + 0.3 * Math.sin(time * 4.1 + 2 * p) + 0.2 * Math.sin(time * 7.7 + 3 * p);
		return lanes[i].tps * (1 + 0.03 * m);
	}

	onMount(() => {
		runs = lanes.map((_, i) => {
			const els = Array.from(feeds[i]?.querySelectorAll<HTMLElement>('.tk') ?? []);
			return { els, cost: els.map(() => 1), tops: [], lit: 0, para: 0, at: head.length, budget: 0, acc: 0, kick: 0, spring: new Spring(0, 55, 14), y: 0, win: 0, lineH: 24, perLine: 10 };
		});
		lanes.forEach((_, i) => measure(i));
		const ro = new ResizeObserver(() =>
			lanes.forEach((_, i) => {
				measure(i);
				runs[i].y = target(i);
				place(i);
			})
		);
		feeds.forEach((f) => f?.parentElement && ro.observe(f.parentElement));
		if (reducedMotion()) {
			// one static frame: the opening written, the needles on the median
			lanes.forEach((l, i) => {
				emit(i, head.length);
				dials[i]?.set(l.tps);
			});
			return () => ro.disconnect();
		}
		dials.forEach((d) => d?.set(0));
		const cancel = whenIdle(() => {
			started = true;
			heatOn = true;
			onheat?.(true);
			more?.()
				.then((rest) => (paras = [head, ...rest.map(tokenize)]))
				.catch(() => {
					/* the opening alone keeps going round */
				});
		});
		return () => {
			cancel();
			ro.disconnect();
		};
	});

	// the frame loop lives only while the race runs on screen; it continues where it stopped
	$effect(() => {
		if (!started || !playing || !onScreen) return;
		return untrack(() =>
			onFrame((dt) => {
				const d = Math.min(dt, 0.1);
				clock += d;
				if (heatOn && clock >= HEAT_S) {
					heatOn = false;
					onheat?.(false);
				}
				for (let i = 0; i < lanes.length; i++) {
					const l = lanes[i];
					const r = runs[i];
					const burst = l.burst ?? 1;
					r.spring.target = readoutAt(i, clock);
					r.spring.step(d);
					// the lane writes at the speed its needle shows
					r.budget += Math.max(0, r.spring.x) * d;
					let k = Math.floor(r.acc + burst) - Math.floor(r.acc);
					while (r.budget >= k) {
						r.budget -= k;
						r.acc += burst;
						emit(i, k);
						// a zero-mean tick per step: steps above the mean kick up, below it down
						r.kick += (k - burst) * 0.015 * l.tps;
						k = Math.floor(r.acc + burst) - Math.floor(r.acc);
					}
					r.kick *= Math.exp(-d / 0.09);
					dials[i]?.set(Math.max(0, r.spring.x + r.kick));
					r.y += (target(i) - r.y) * (1 - Math.exp(-d / FOLLOW));
					place(i);
					trim(i);
				}
			})
		);
	});

	function toggle() {
		playing = !playing;
		if (!playing && heatOn) {
			heatOn = false;
			onheat?.(false);
		}
	}
</script>

<div class="live" use:visible={(v) => (onScreen = v)}>
	<p class="sr-only">{summary}</p>
	<div class="lanes" aria-hidden="true">
		{#each lanes as l, i (l.id)}
			<div class="lane" class:hot={l.hot}>
				<div class="dial">
					<Speedo bind:this={dials[i]} value={l.tps} {max} {redline} {step} tone={l.hot ? 'hot' : 'cold'}>
						<span class="tps">{num(l.tps, lang, 1)}</span>
						<span class="unit">t/s<span class="med">&nbsp;·&nbsp;{t.median}</span></span>
					</Speedo>
				</div>
				<div class="body">
					<div class="head">
						<span class="label">{l.label}</span>
						{#if l.sub}<span class="sub">{l.sub}</span>{/if}
					</div>
					<div class="win"><p class="feed" bind:this={feeds[i]}>{#each head as piece, j (j)}<span class="tk">{piece}</span>{/each}</p></div>
				</div>
			</div>
		{/each}
	</div>
	<button type="button" class="ctl" onclick={toggle} aria-label={playing ? t.pause : t.resume} aria-pressed={!playing}>
		{#if playing}
			<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z" fill="currentColor" /></svg>
		{:else}
			<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true"><path d="M4.5 2.5v11l9-5.5z" fill="currentColor" /></svg>
		{/if}
	</button>
</div>

<style>
	.live {
		/* column gap between the lanes; the dial size when it sits above the text */
		--cg: clamp(1.25rem, 4.5vw, 4.5rem);
		--gm: clamp(8rem, 30svh, 16rem);
		position: relative;
		container-type: inline-size;
	}
	/* two lanes side by side, a hairline between them. Decorative (the sr-only summary carries the
	 * facts): never selected or copied. */
	.lanes {
		-webkit-user-select: none;
		user-select: none;
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		column-gap: var(--cg);
		position: relative;
	}
	.lanes::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		left: 50%;
		width: 1px;
		background: linear-gradient(transparent, var(--line) 20%, var(--line) 80%, transparent);
	}
	/* pause: a small node on the hairline between the lanes */
	.ctl {
		position: absolute;
		z-index: 2;
		left: 50%;
		top: 50%;
		translate: -50% -50%;
		display: inline-grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: var(--bg-1);
		color: var(--text-hi);
		cursor: pointer;
		transition:
			background var(--dur-2),
			border-color var(--dur-2);
	}
	.ctl:hover {
		background: var(--bg-3);
		border-color: var(--text-mute);
	}
	.ctl:focus-visible {
		outline: 2px solid var(--focus, var(--text-hi));
		outline-offset: 2px;
	}
	/* wide: the big dial on the left, name and the streaming text on the right, as tall as the dial */
	.lane {
		--g: clamp(10rem, min(4rem + 17vw, 40svh), 22rem);
		position: relative;
		display: grid;
		grid-template-columns: var(--g) minmax(0, 1fr);
		column-gap: clamp(1rem, 2vw, 1.75rem);
		min-width: 0;
	}
	.dial {
		width: var(--g);
		min-width: 0;
		align-self: center;
	}
	.body {
		container: lanebody / inline-size;
		display: grid;
		grid-template-rows: auto minmax(0, 1fr);
		gap: 0.75rem;
		min-width: 0;
		padding-block: calc(var(--g) * 0.06);
	}
	.head {
		display: grid;
		gap: 0.2rem;
		min-width: 0;
	}
	.label {
		min-width: 0;
		font-weight: 720;
		font-size: clamp(1rem, 0.8rem + 0.45vw, 1.3rem);
		line-height: 1.15;
		letter-spacing: -0.01em;
		color: var(--text);
	}
	.hot .label {
		color: var(--text-hi);
	}
	.sub {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	/* the measured median in the open bottom of the dial */
	.tps {
		font-family: var(--font-display);
		font-weight: 760;
		font-size: 16cqi;
		line-height: 1;
		letter-spacing: -0.045em;
		font-variant-numeric: tabular-nums lining-nums;
		color: var(--before);
		/* a dark halo: the needle passes under the digits cleanly */
		text-shadow:
			0 0 3px #050506,
			0 0 8px #050506;
	}
	/* hot metal: the digits glow and drift through the heat ramp, continuously alive */
	.hot .tps {
		color: var(--heat-4);
		text-shadow:
			0 0 3px #050506,
			0 0 10px rgb(255 122 26 / 0.6),
			0 0 28px rgb(226 64 28 / 0.4);
		animation: metal 2.6s ease-in-out infinite alternate;
	}
	@keyframes metal {
		0% {
			color: var(--heat-3);
		}
		55% {
			color: var(--heat-4);
		}
		100% {
			color: var(--heat-5);
		}
	}
	.unit {
		margin-top: 2.5cqi;
		font-family: var(--font-mono);
		font-size: max(0.56rem, 4.6cqi);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
		white-space: nowrap;
	}
	@container (max-width: 12.5rem) {
		.med {
			display: none;
		}
	}
	/* the streaming text: a window that follows the newest line (transform only) */
	.win {
		position: relative;
		min-height: 0;
		overflow: clip;
		font-size: clamp(0.95rem, 0.8rem + 0.35vw, 1.15rem);
		/* the unwritten line below the newest one fades out */
		-webkit-mask-image: linear-gradient(#000 calc(100% - 1.1em), transparent);
		mask-image: linear-gradient(#000 calc(100% - 1.1em), transparent);
	}
	/* and once older lines scroll out, the top fades too (the first lines stay whole) */
	.win:global(.scrolled) {
		-webkit-mask-image: linear-gradient(transparent, #000 1.6em, #000 calc(100% - 1.1em), transparent);
		mask-image: linear-gradient(transparent, #000 1.6em, #000 calc(100% - 1.1em), transparent);
	}
	.feed {
		position: absolute;
		inset: 0 0 auto 0;
		margin: 0;
		font-size: inherit;
		line-height: 1.5;
		letter-spacing: -0.005em;
		color: rgb(237 234 227 / 0.17);
		will-change: transform;
	}
	.feed :global(.br) {
		display: block;
		height: 0.6em;
	}
	.feed :global(.tk.on) {
		color: #a3a8b1;
		animation: lit-cold 0.9s var(--ease-out) backwards;
	}
	@keyframes lit-cold {
		from {
			color: var(--text-hi);
		}
	}
	/* fast lane: the text is hot metal; each step's tokens flash white-hot and cool to orange */
	.hot .feed :global(.tk.on) {
		color: var(--heat-4);
		text-shadow: 0 0 14px rgb(255 122 26 / 0.35);
		animation: lit-hot 1.1s var(--ease-out) backwards;
	}
	@keyframes lit-hot {
		0% {
			color: #fff;
			text-shadow:
				0 0 6px #fff3d6,
				0 0 18px #ffc15a;
		}
	}
	/* no JS: the opening is shown as written */
	:global(html:not(.js)) .feed :global(.tk) {
		color: #a3a8b1;
	}
	:global(html:not(.js)) .hot .feed :global(.tk) {
		color: var(--heat-4);
	}
	/* narrower: each lane is a column, the dial on top as large as the column and the screen allow */
	@media (max-width: 1000px) {
		.lane {
			grid-template-columns: minmax(0, 1fr);
			justify-items: center;
			align-items: start;
			row-gap: 0.7rem;
		}
		.dial {
			width: min(100%, var(--gm));
		}
		.body {
			width: 100%;
			grid-template-rows: auto auto;
			padding-block: 0;
		}
		.head {
			justify-items: center;
			text-align: center;
		}
		.win {
			height: calc(6 * 1.5em);
		}
		/* the pause node sits on the hairline at the height of the lane names */
		.ctl {
			top: calc(min((100cqi - var(--cg)) / 2, var(--gm)) + 0.7rem + 0.6rem);
		}
	}
	/* phones: compact names, six short lines of the text */
	@media (max-width: 640px) {
		.live {
			--cg: 1.1rem;
		}
		.sub {
			display: none;
		}
		.label {
			font-size: 0.85rem;
		}
		.ctl {
			width: 1.75rem;
			height: 1.75rem;
			top: calc(min((100cqi - var(--cg)) / 2, var(--gm)) + 0.7rem + 0.5rem);
		}
		.win {
			height: calc(6 * 1.45em);
			font-size: 0.8rem;
		}
		.feed {
			line-height: 1.45;
		}
	}
	/* the smallest phones: room for both names beside the pause node (still a 24 px target) */
	@media (max-width: 360px) {
		.label {
			font-size: 0.78rem;
		}
		.ctl {
			width: 1.5rem;
			height: 1.5rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.ctl {
			display: none;
		}
		.hot .tps,
		.feed :global(.tk.on),
		.hot .feed :global(.tk.on) {
			animation: none;
		}
	}
</style>
