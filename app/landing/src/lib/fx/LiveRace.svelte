<script lang="ts" module>
	export interface LiveLane {
		id: string;
		label: string;
		sub?: string;
		/** Measured decode speed (t/s): the average emission rate, exactly. */
		tps: number;
		hot: boolean;
		/** Measured tokens accepted per step (MTP); absent = one token per step. */
		burst?: number;
		/** Measured per-prompt range of the decode speed; the live rate never leaves it. */
		lo?: number;
		hi?: number;
	}
</script>

<script lang="ts">
	/**
	 * The hero race as a live feed: two frameless typographic streams side by side, each with a thin
	 * lane rule (progress through the answer: the fast lane visibly pulls ahead), a compact dial and a
	 * small t/s readout as instruments. Both lanes write the same answer; the fast lane finishes and
	 * rests (its rule full and glowing) while the slow one keeps crawling, then both start over: a
	 * continuous feed with no end state.
	 * Tokens are emitted in steps: `burst` tokens per step (measured MTP tokens accepted per step,
	 * spread as a deterministic 3,3,4,… pattern with the measured mean). The live rate is the measured
	 * median times (1 + m(t)), m a zero-mean sum of slow sines whose amplitude keeps the rate inside
	 * the measured per-prompt range [lo, hi] (±1% where the sheet gives no range); tokens are drawn
	 * from a budget that integrates that rate, so the long-run average is exactly the median. The
	 * readout shows the live rate (digits tick); each emitted step kicks the needle slightly up and a
	 * spring settles it back. Each step's tokens light up together
	 * and cool down. Under the text, a rhythm strip draws every step of the last seconds (bar height =
	 * tokens in the step): bursts vs single tokens on one time scale.
	 *
	 * The answer is cut into token-sized pieces so the piece count matches TOK_PER_WORD (report 06
	 * §2.1.2); the text is an example, the pace is measured.
	 *
	 * Layout stability (CLS): each pass of the answer is laid out once, all tokens present but
	 * transparent; emitting a token only adds a class (colour + glow), the window follows the newest
	 * line with a transform on the top-anchored paragraph, and the lane rule fills with scaleX.
	 * Nothing moves in layout per frame. Performance: class toggles only, no reactive re-render; the
	 * frame loop runs only while playing on screen and first starts on load idle; strip canvas DPR ≤ 1.5.
	 * Reduced motion: one static, readable frame.
	 */
	import type { Snippet } from 'svelte';
	import { onMount, untrack } from 'svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { fmtRatio } from '$lib/format';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFrame, reducedMotion, whenIdle } from './motion';
	import Odometer from './Odometer.svelte';
	import Tacho from './Tacho.svelte';

	let {
		lanes,
		text,
		lang,
		max,
		redline,
		summary,
		prompt = '',
		startDelay = 0,
		onheat,
		meta
	}: {
		lanes: LiveLane[];
		text: string;
		lang: 'pl' | 'en';
		max: number;
		redline: number;
		summary: string;
		prompt?: string;
		startDelay?: number;
		onheat?: (hot: boolean) => void;
		meta?: Snippet;
	} = $props();

	const L = {
		pl: { pause: 'Wstrzymaj wyścig', resume: 'Wznów wyścig', faster: 'szybciej', live: 'na żywo', paused: 'pauza' },
		en: { pause: 'Pause the race', resume: 'Resume the race', faster: 'faster', live: 'live', paused: 'paused' }
	};
	const t = $derived(L[lang]);

	/** The answer as token-sized pieces (count ≈ words × TOK_PER_WORD). */
	const pieces = $derived.by(() => {
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
	});
	/** Seconds the finished fast lane rests while the slow one keeps writing, before both restart. */
	const HOLD = 2.6;
	/** Seconds of history in the rhythm strip. */
	const STRIP_S = 1.6;

	const hotIdx = $derived(lanes.findIndex((l) => l.hot));
	const coldIdx = $derived(lanes.findIndex((l) => !l.hot));
	const ratio = $derived(hotIdx >= 0 && coldIdx >= 0 ? lanes[hotIdx].tps / lanes[coldIdx].tps : 0);
	const step = $derived(max <= 120 ? 20 : max <= 250 ? 50 : 100);

	let playing = $state(false);
	let onScreen = $state(false);
	let started = $state(false);
	/** Live readout per lane (t/s, 0.1 steps) and needle value; null until the launch has landed. */
	let liveRate: (number | null)[] = $state([]);
	let needle: (number | null)[] = $state([]);
	let kick: number[] = [];
	let phase: number[] = [];
	let shown = 0;
	/** The fast lane has written the whole answer (this pass). */
	let finished = $state(false);
	let finishAt = 0;
	let feeds: HTMLElement[] = $state([]);
	let fills: HTMLElement[] = $state([]);
	let strips: HTMLCanvasElement[] = $state([]);

	type LaneRun = { next: number; acc: number; pos: number; budget: number; events: { t: number; k: number }[] };
	let clock = 0;
	let since = 0;
	let runs: LaneRun[] = [];
	/** Per lane: the paragraph's current upward offset (px). */
	let shift: number[] = [];

	function reset() {
		clock = 0;
		since = 0;
		restart();
	}
	/** Lay out every token of the pass once per lane (invisible until emitted). */
	function build() {
		for (const f of feeds) {
			if (!f) continue;
			const frag = document.createDocumentFragment();
			for (const piece of pieces) {
				const s = document.createElement('span');
				s.className = 'tk';
				s.textContent = piece;
				frag.append(s);
			}
			f.replaceChildren(frag);
		}
	}
	/** A new pass for both lanes: the text goes dark, windows and rules return to the start. */
	function restart() {
		runs = lanes.map(() => ({ next: clock + 0.35, acc: 0, pos: 0, budget: 0, events: [] }));
		shift = lanes.map(() => 0);
		finished = false;
		for (const f of feeds) {
			if (!f) continue;
			for (const tk of f.children) tk.classList.remove('on', 'old');
			f.style.transform = '';
		}
		for (const fl of fills) if (fl) fl.style.transform = 'scaleX(0)';
	}

	function emit(i: number, k: number) {
		const f = feeds[i];
		const r = runs[i];
		if (!f) return;
		const tks = f.children;
		let last: HTMLElement | null = null;
		for (let j = 0; j < k && r.pos < pieces.length; j++) {
			last = tks[r.pos++] as HTMLElement;
			last.classList.add('on');
		}
		if (!last) return;
		// follow the newest line: transform only (the paragraph never moves in layout)
		const win = f.parentElement?.clientHeight ?? 0;
		const y = Math.max(0, last.offsetTop + last.offsetHeight - win);
		if (y !== shift[i]) {
			shift[i] = y;
			f.style.transform = y ? `translate3d(0, ${-y}px, 0)` : '';
		}
		const fl = fills[i];
		if (fl) fl.style.transform = `scaleX(${(r.pos / pieces.length).toFixed(4)})`;
	}

	/** Relative swing allowed around the median: inside [lo, hi] with a margin, else ±1%. */
	function swing(l: LiveLane) {
		if (l.lo === undefined || l.hi === undefined) return 0.01;
		return 0.9 * Math.min((l.hi - l.tps) / l.tps, (l.tps - l.lo) / l.tps);
	}
	/** Live rate of a lane at time t: the median × (1 + zero-mean slow sines), never outside [lo, hi]. */
	function rateAt(i: number, t: number) {
		const l = lanes[i];
		const p = phase[i] ?? 0;
		const m = 0.55 * Math.sin(t * 1.7 + p) + 0.3 * Math.sin(t * 3.1 + 2 * p) + 0.15 * Math.sin(t * 5.3 + 3 * p);
		return l.tps * (1 + swing(l) * m);
	}
	/** Advance one lane by dt: integrate the live rate into a token budget and emit due steps. */
	function advance(i: number, dt: number) {
		const l = lanes[i];
		const r = runs[i];
		const burst = l.burst ?? 1;
		if (clock < r.next || r.pos >= pieces.length) return;
		r.budget += rateAt(i, clock) * dt;
		let k = Math.floor(r.acc + burst) - Math.floor(r.acc);
		while (r.budget >= k && r.pos < pieces.length) {
			r.budget -= k;
			r.acc += burst;
			r.events.push({ t: clock, k });
			emit(i, k);
			kick[i] = (kick[i] ?? 0) + k * l.tps * 0.012;
			// the whole answer is written: this lane rests until the restart
			if (r.pos >= pieces.length && l.hot && !finished) {
				finished = true;
				finishAt = clock;
			}
			k = Math.floor(r.acc + burst) - Math.floor(r.acc);
		}
	}
	function trim(i: number) {
		const r = runs[i];
		while (r.events.length && r.events[0].t < clock - STRIP_S) r.events.shift();
	}

	const dpr = typeof devicePixelRatio === 'number' ? Math.min(1.5, devicePixelRatio) : 1;
	function drawStrip(i: number) {
		const cv = strips[i];
		if (!cv) return;
		const w = cv.clientWidth;
		const h = cv.clientHeight;
		if (cv.width !== Math.round(w * dpr)) {
			cv.width = Math.round(w * dpr);
			cv.height = Math.round(h * dpr);
		}
		const ctx = cv.getContext('2d');
		if (!ctx) return;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, w, h);
		const hot = lanes[i].hot;
		const unit = h / 4;
		for (const e of runs[i].events) {
			const age = clock - e.t;
			const x = w - (age / STRIP_S) * w;
			const bh = Math.min(h, unit * e.k);
			ctx.globalAlpha = Math.max(0.12, 1 - age / STRIP_S);
			ctx.fillStyle = hot ? (age < 0.12 ? '#fff3d6' : '#ff9a3a') : '#7d8794';
			ctx.fillRect(x - 1, h - bh, 2, bh);
		}
		ctx.globalAlpha = 1;
	}

	/** Reduced motion: one static frame, both lanes after the same 2.4 s of writing. */
	function staticFrame() {
		reset();
		// both lanes after the same 3 s of writing at their medians
		lanes.forEach((l, i) => {
			const r = runs[i];
			const steps = Math.floor(((3 - r.next) * l.tps) / (l.burst ?? 1));
			for (let s = 0; s < steps && r.pos < pieces.length; s++) {
				const k = Math.floor(r.acc + (l.burst ?? 1)) - Math.floor(r.acc);
				r.acc += l.burst ?? 1;
				emit(i, k);
			}
			if (l.hot && r.pos >= pieces.length) finished = true;
		});
		clock = 3;
		feeds.forEach((f) => f?.querySelectorAll('.tk.on').forEach((s) => s.classList.add('old')));
		lanes.forEach((_, i) => drawStrip(i));
	}

	onMount(() => {
		phase = lanes.map((_, i) => i * 2.1 + 0.7);
		build();
		reset();
		if (reducedMotion()) {
			staticFrame();
			started = true;
			return;
		}
		return whenIdle(() => {
			started = true;
			playing = true;
			onheat?.(true);
			// after the launch (slam + overshoot) has landed, the readouts and needles go live
			setTimeout(() => (shown = 1), 1500);
		}, startDelay * 1000);
	});

	// the frame loop lives only while playing on screen
	$effect(() => {
		if (!playing || !onScreen) return;
		return untrack(() =>
			onFrame((dt) => {
				const d = Math.min(dt, 0.1);
				clock += d;
				since += d;
				const live = shown === 1;
				const nr = live ? [...liveRate] : liveRate;
				const nn = live ? [...needle] : needle;
				for (let i = 0; i < lanes.length; i++) {
					advance(i, d);
					trim(i);
					drawStrip(i);
					kick[i] = (kick[i] ?? 0) * Math.exp(-d / 0.09);
					if (live) {
						const l = lanes[i];
						const rate = rateAt(i, clock);
						nr[i] = Math.round(rate * 10) / 10;
						nn[i] = Math.min(l.hi ?? l.tps * 1.01, Math.max(l.lo ?? l.tps * 0.99, rate)) + kick[i];
					}
				}
				if (live) {
					// the readout ticks at ~12 Hz (readable digits); the needle follows every frame
					liveTick += d;
					if (liveTick > 0.08) {
						liveTick = 0;
						liveRate = nr;
					}
					needle = nn;
				}
				if (since > 2.6 && since - d <= 2.6) onheat?.(false);
				if (finished && clock - finishAt > HOLD) restart();
			})
		);
	});

	let liveTick = 0;

	function toggle() {
		playing = !playing;
		if (!playing) onheat?.(false);
	}
</script>

<div class="live" use:visible={(v) => (onScreen = v)}>
	<p class="sr-only">{summary}</p>
	{#if prompt}<p class="prompt" class:on={playing} aria-hidden="true"><span class="caret">›</span>{prompt}</p>{/if}
	<div class="lanes" aria-hidden="true">
		{#each lanes as l, i (l.id)}
			<div class="lane" class:hot={l.hot} class:on={playing} class:done={l.hot && finished}>
				<div class="inst">
					<div class="gauge">
						<Tacho value={needle[i] ?? (started ? l.tps : 0)} glowing={l.hot} slam={l.hot} {max} {redline} {step} tone={l.hot ? 'hot' : 'cold'} label="{l.label}: {num(l.tps, lang)} t/s" />
					</div>
					<div class="who">
						<span class="label">{l.label}</span>
						{#if l.sub}<span class="sub">{l.sub}</span>{/if}
					</div>
					<div class="rate">
						<span class="tps"><Odometer value={liveRate[i] ?? (started ? l.tps : 0)} decimals={1} {lang} duration={liveRate[i] != null ? 160 : l.hot ? 1300 : 900} minInt={2} pad overshoot={liveRate[i] != null ? 0 : l.hot ? 1.8 : 0} /></span>
						<span class="unit">t/s</span>
					</div>
				</div>
				<div class="rule"><span class="fill" bind:this={fills[i]}></span></div>
				<div class="feed"><p bind:this={feeds[i]}></p></div>
				<div class="foot">
					<canvas class="strip" bind:this={strips[i]}></canvas>
					{#if l.hot && ratio > 0}<span class="gain speedup" class:speedup--down={ratio < 1}>{fmtRatio(ratio, lang)} <small>{t.faster}</small></span>{/if}
				</div>
			</div>
		{/each}
	</div>
	<div class="controls">
		{#if meta}<div class="meta">{@render meta()}</div>{/if}
		<span class="state" class:on={playing}>{playing ? t.live : t.paused}</span>
		<button type="button" class="ctl" onclick={toggle} aria-label={playing ? t.pause : t.resume} aria-pressed={!playing}>
			{#if playing}
				<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z" fill="currentColor" /></svg>
			{:else}
				<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" fill="currentColor" /></svg>
			{/if}
		</button>
	</div>
</div>

<style>
	.live {
		display: grid;
		gap: clamp(1rem, 2vh, 1.5rem);
	}
	/* the question both lanes answer, set like a typed prompt */
	.prompt {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		letter-spacing: 0.02em;
		color: var(--text);
	}
	.caret {
		color: var(--heat-3);
		font-weight: 700;
	}
	.prompt.on .caret {
		animation: blink 1.1s steps(2) infinite;
	}
	@keyframes blink {
		50% {
			opacity: 0.25;
		}
	}
	/* two frameless streams; a hairline between them */
	.lanes {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		column-gap: clamp(2rem, 5vw, 5rem);
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
	.lane {
		position: relative;
		display: grid;
		gap: 0.85rem;
		min-width: 0;
	}
	/* instruments: compact dial · who · small readout (fixed height: never moves the text) */
	.inst {
		display: grid;
		grid-template-columns: 3.25rem minmax(0, 1fr) auto;
		align-items: center;
		gap: 0.9rem;
		height: 3.5rem;
	}
	.gauge {
		width: 3.25rem;
	}
	.who {
		display: grid;
		gap: 0.15rem;
		min-width: 0;
		overflow: hidden;
	}
	.label {
		font-weight: 680;
		font-stretch: 110%;
		font-size: var(--fs-sm);
		letter-spacing: -0.005em;
		line-height: 1.2;
		color: var(--text);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
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
	.rate {
		display: flex;
		align-items: baseline;
		gap: 0.3rem;
	}
	.tps {
		font-size: clamp(1.45rem, 1rem + 1.1vw, 2.05rem);
		font-weight: 500;
		letter-spacing: -0.04em;
		color: var(--before);
	}
	/* hot metal: the digits glow and drift through the heat ramp, continuously alive */
	.hot .tps {
		color: var(--heat-4);
		text-shadow:
			0 0 10px rgb(255 122 26 / 0.6),
			0 0 26px rgb(226 64 28 / 0.35);
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
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.1em;
	}
	/* lane rule = progress through the answer: the fast lane runs ahead with a glowing head */
	.rule {
		position: relative;
		height: 1px;
		background: var(--line-strong);
	}
	.fill {
		position: absolute;
		inset: -0.5px 0;
		transform-origin: 0 50%;
		transform: scaleX(0);
		background: linear-gradient(90deg, transparent, var(--before));
		transition: transform 0.12s linear;
	}
	.hot.done .fill {
		box-shadow:
			0 0 12px rgb(255 122 26 / 0.9),
			0 0 30px rgb(255 193 90 / 0.5);
	}
	.hot .fill {
		inset: -1px 0;
		background: linear-gradient(90deg, rgb(226 64 28 / 0.2), var(--heat-3) 70%, var(--heat-5));
		box-shadow: 0 0 12px rgb(255 122 26 / 0.7);
	}
	/* the answer: the main content, frameless, a top-anchored window scrolled by transform */
	.feed {
		--lines: 5;
		position: relative;
		height: calc(var(--lines) * 1.5em);
		overflow: clip;
		mask-image: linear-gradient(transparent, #000 1.6em, #000 calc(100% - 0.4em), transparent);
		font-size: clamp(1.02rem, 0.85rem + 0.45vw, 1.3rem);
		line-height: 1.5;
		letter-spacing: -0.005em;
		color: #8b9099;
	}
	.feed p {
		position: relative;
		margin: 0;
		transition: transform 0.2s var(--ease-out);
		will-change: transform;
	}
	/* every token of the pass is laid out from the start; unemitted ones are invisible */
	.feed :global(.tk:not(.on)) {
		color: transparent;
		text-shadow: none;
	}
	.feed :global(.tk.on) {
		animation: lit-cold 0.9s var(--ease-out) both;
	}
	@keyframes lit-cold {
		from {
			color: var(--text-hi);
		}
	}
	/* hot lane: the text is hot metal; each step's tokens flash white-hot and cool to orange */
	.hot .feed {
		color: var(--heat-3);
		text-shadow: 0 0 14px rgb(255 122 26 / 0.35);
	}
	.hot .feed :global(.tk.on) {
		animation: lit-hot 1.1s var(--ease-out) both;
	}
	@keyframes lit-hot {
		0% {
			color: #fff;
			text-shadow:
				0 0 6px #fff3d6,
				0 0 18px #ffc15a;
		}
		30% {
			color: var(--heat-4);
			text-shadow: 0 0 12px rgb(255 160 60 / 0.8);
		}
	}
	.feed :global(.tk.old) {
		animation: none;
	}
	.foot {
		display: flex;
		align-items: center;
		gap: var(--sp-4);
		height: 1.6rem;
	}
	.strip {
		flex: 1;
		min-width: 0;
		height: 1rem;
	}
	.gain {
		flex: none;
		font-size: var(--fs-md);
		white-space: nowrap;
	}
	.gain small {
		font-size: 0.6em;
		font-family: var(--font-mono);
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	.controls {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding-top: 0.75rem;
		border-top: 1px solid var(--line);
	}
	.meta {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	/* fixed width: switching "live"/"paused" never moves the row */
	.state {
		min-width: 8ch;
		text-align: right;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.state.on {
		color: var(--heat-4);
	}
	.ctl {
		display: inline-grid;
		place-items: center;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: transparent;
		color: var(--text-hi);
		cursor: pointer;
		transition: background var(--dur-2), border-color var(--dur-2);
	}
	.ctl:hover {
		background: var(--bg-2);
		border-color: var(--text-mute);
	}
	@media (max-width: 900px) {
		.lanes {
			grid-template-columns: minmax(0, 1fr);
			row-gap: 1.6rem;
		}
		.lanes::before {
			display: none;
		}
		.feed {
			--lines: 3;
		}
	}
	@media (max-width: 640px) {
		.inst {
			grid-template-columns: 2.75rem minmax(0, 1fr) auto;
			gap: 0.7rem;
			height: 3rem;
		}
		.gauge {
			width: 2.75rem;
		}
		.feed {
			font-size: var(--fs-sm);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.prompt.on .caret,
		.hot .tps,
		.feed :global(.tk.on),
		.hot .feed :global(.tk.on) {
			animation: none;
		}
		.feed p,
		.fill {
			transition: none;
		}
	}
</style>
