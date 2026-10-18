<script lang="ts" module>
	export interface LiveLane {
		id: string;
		label: string;
		sub?: string;
		/** Measured decode speed (t/s, the median): the emission rate, exactly. */
		tps: number;
		hot: boolean;
		/** Measured tokens accepted per step (MTP); absent = one token per step. */
		burst?: number;
	}
</script>

<script lang="ts">
	/**
	 * The hero race: both lanes write the same short answer, shown in full from the first frame as a
	 * dim preview that each lane lights up token by token at its measured pace, so you always see how
	 * far each side has got (no scrolling window, nothing cropped). Under the lanes one shared finish
	 * track: a runner per side, a running timer that stops at that side's finish time, and, once the
	 * fast side is through, a big speed-up figure. When both are done the race holds for a moment and
	 * starts over: a continuous feed. Pause is always available.
	 *
	 * Honesty: tokens are emitted at exactly the measured median t/s, in steps of `burst` tokens
	 * (measured MTP tokens accepted per step, a deterministic 3,3,4,… pattern with the measured
	 * mean); finish times = tokens ÷ median. The live readout breathes only BELOW the median, within
	 * [0,97 × median, median]; the needle kicks a little on each emitted step and a spring settles it
	 * back to the readout. The measured median is printed next to each readout.
	 *
	 * The answer is cut into token-sized pieces so the piece count matches TOK_PER_WORD (report 06
	 * §2.1.2); the text is an example, the pace is measured.
	 *
	 * SSR / first paint: the race is shown 0,6 s in (prompt, first words lit, timers running), and the
	 * client continues from exactly that state. Every token is always laid out (CLS 0): emitting only
	 * toggles a class; runners move by transform. The frame loop runs only while playing on screen.
	 * Reduced motion: one static frame at the moment the fast side finishes.
	 */
	import { heatOf } from '$lib/cards/explorer';
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
		onheat?: (hot: boolean) => void;
		meta?: Snippet;
	} = $props();

	const L = {
		pl: { pause: 'Wstrzymaj wyścig', resume: 'Wznów wyścig', faster: 'szybciej', same: 'ten sam skrypt', live: 'na żywo', paused: 'pauza', median: 'zmierzone' },
		en: { pause: 'Pause the race', resume: 'Resume the race', faster: 'faster', same: 'the same script', live: 'live', paused: 'paused', median: 'measured' }
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
	/** Each side's finish time: tokens ÷ measured median t/s. */
	const ends = $derived(lanes.map((l) => pieces.length / l.tps));
	/** The race as first painted (and continued from by the client). */
	const T0 = 0.6;
	/** Seconds the finished race (both sides through, the verdict up) holds before it starts over. */
	const HOLD = 4;
	/** Seconds of history in the rhythm strip. */
	const STRIP_S = 1.6;

	const hotIdx = $derived(lanes.findIndex((l) => l.hot));
	const coldIdx = $derived(lanes.findIndex((l) => !l.hot));
	const ratio = $derived(hotIdx >= 0 && coldIdx >= 0 ? lanes[hotIdx].tps / lanes[coldIdx].tps : 0);
	const step = $derived(max <= 120 ? 20 : max <= 250 ? 50 : 100);

	type LaneRun = { acc: number; pos: number; budget: number; events: { t: number; k: number }[] };
	/** Deterministic emission: the lane's state after `time` seconds at its median rate. */
	function runAt(l: LiveLane, time: number): LaneRun {
		const burst = l.burst ?? 1;
		const r: LaneRun = { acc: 0, pos: 0, budget: l.tps * time, events: [] };
		let k = Math.floor(r.acc + burst) - Math.floor(r.acc);
		while (r.budget >= k && r.pos < pieces.length) {
			r.budget -= k;
			r.acc += burst;
			r.pos = Math.min(pieces.length, r.pos + k);
			k = Math.floor(r.acc + burst) - Math.floor(r.acc);
		}
		return r;
	}
	const first = $derived(lanes.map((l) => runAt(l, T0).pos));
	const fmtS = (s: number) => `${num(s, lang, 1)}\u00a0s`;

	let playing = $state(false);
	let onScreen = $state(false);
	/** Live readout per lane (t/s, 0.1 steps) and needle value; null = show the median. */
	let liveRate: (number | null)[] = $state([]);
	let needle: (number | null)[] = $state([]);
	let kick: number[] = [];
	let phase: number[] = [];
	/** The fast side has written the whole answer (this pass). */
	let finished = $state(false);
	let doneAt = 0;
	let feeds: HTMLElement[] = $state([]);
	let trails: HTMLElement[] = $state([]);
	let timers: HTMLElement[] = $state([]);
	let strips: HTMLCanvasElement[] = $state([]);

	let clock = 0;
	let since = 0;
	let runs: LaneRun[] = [];

	/** Put every lane at time `time` (DOM classes, runners, timers), deterministically. */
	function seek(time: number) {
		clock = time;
		runs = lanes.map((l) => runAt(l, time));
		finished = hotIdx >= 0 && runs[hotIdx].pos >= pieces.length;
		doneAt = finished ? Math.max(...ends) : 0;
		lanes.forEach((_, i) => {
			const f = feeds[i];
			if (f) for (let j = 0; j < f.children.length; j++) f.children[j].classList.toggle('on', j < runs[i].pos);
			paint(i);
		});
	}
	function paint(i: number) {
		const r = runs[i];
		const tr = trails[i];
		if (tr) tr.style.transform = `translate3d(${((r.pos / pieces.length - 1) * 100).toFixed(2)}%, 0, 0)`;
		const tm = timers[i];
		if (tm) tm.textContent = fmtS(Math.min(clock, ends[i]));
	}

	function emit(i: number, k: number) {
		const f = feeds[i];
		const r = runs[i];
		for (let j = 0; j < k && r.pos < pieces.length; j++) f?.children[r.pos++]?.classList.add('on');
	}

	/** Live readout: the median × (1 − 3% × w), w ∈ [0, 1] from slow sines: never above the median. */
	function readoutAt(i: number, time: number) {
		const p = phase[i] ?? 0;
		const m = 0.55 * Math.sin(time * 1.7 + p) + 0.3 * Math.sin(time * 3.1 + 2 * p) + 0.15 * Math.sin(time * 5.3 + 3 * p);
		return lanes[i].tps * (1 - 0.03 * ((m + 1) / 2));
	}
	/** Advance one lane by dt at its median rate and emit the steps that are due. */
	function advance(i: number, dt: number) {
		const l = lanes[i];
		const r = runs[i];
		const burst = l.burst ?? 1;
		if (r.pos >= pieces.length) return;
		r.budget += l.tps * dt;
		let k = Math.floor(r.acc + burst) - Math.floor(r.acc);
		while (r.budget >= k && r.pos < pieces.length) {
			r.budget -= k;
			r.acc += burst;
			r.events.push({ t: clock, k });
			emit(i, k);
			kick[i] = (kick[i] ?? 0) + k * l.tps * 0.01;
			k = Math.floor(r.acc + burst) - Math.floor(r.acc);
		}
		if (l.hot && r.pos >= pieces.length && !finished) finished = true;
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

	onMount(() => {
		phase = lanes.map((_, i) => i * 2.1 + 0.7);
		if (reducedMotion()) {
			// one readable frame: the moment the fast side crosses the line
			seek(hotIdx >= 0 ? ends[hotIdx] : T0);
			return;
		}
		seek(T0);
		return whenIdle(() => {
			playing = true;
			onheat?.(true);
		});
	});

	let liveTick = 0;
	// the frame loop lives only while playing on screen
	$effect(() => {
		if (!playing || !onScreen) return;
		return untrack(() =>
			onFrame((dt) => {
				const d = Math.min(dt, 0.1);
				clock += d;
				since += d;
				const nr = [...liveRate];
				const nn = [...needle];
				for (let i = 0; i < lanes.length; i++) {
					advance(i, d);
					paint(i);
					drawStrip(i);
					kick[i] = (kick[i] ?? 0) * Math.exp(-d / 0.09);
					const rate = readoutAt(i, clock);
					nr[i] = Math.floor(rate * 10) / 10;
					nn[i] = rate + kick[i];
				}
				// the readout ticks at ~12 Hz (readable digits); the needle follows every frame
				liveTick += d;
				if (liveTick > 0.08) {
					liveTick = 0;
					liveRate = nr;
				}
				needle = nn;
				if (since > 2.6 && since - d <= 2.6) onheat?.(false);
				const allDone = runs.every((r) => r.pos >= pieces.length);
				if (allDone && !doneAt) doneAt = clock;
				if (allDone && clock - doneAt > HOLD) {
					seek(0);
					since = 0;
					onheat?.(true);
				}
			})
		);
	});

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
						<Tacho value={needle[i] ?? l.tps} glowing={l.hot} {max} {redline} {step} tone={l.hot ? 'hot' : 'cold'} label="{l.label}: {num(l.tps, lang)} t/s" />
					</div>
					<div class="who">
						<span class="label">{l.label}</span>
						{#if l.sub}<span class="sub">{l.sub}</span>{/if}
					</div>
					<div class="rate">
						<span class="tps"><Odometer value={liveRate[i] ?? l.tps} decimals={1} {lang} duration={0} minInt={2} pad /></span>
						<span class="unit">t/s</span>
						<!-- the measured median, always visible next to the live readout -->
						<span class="med">{t.median} <b>{num(l.tps, lang, 1)}</b></span>
					</div>
				</div>
				<!-- the whole answer, always laid out: dim preview, lit as the lane writes it -->
				<p class="feed" bind:this={feeds[i]}>{#each pieces as piece, j (j)}<span class="tk" class:on={j < first[i]}>{piece}</span>{/each}</p>
				<canvas class="strip" bind:this={strips[i]}></canvas>
			</div>
		{/each}
	</div>
	<!-- one shared finish track: runner, finish line and a running timer per side -->
	<div class="track" class:won={finished} aria-hidden="true">
		{#each lanes as l, i (l.id)}
			<div class="trow" class:hot={l.hot} style="grid-row:{i + 1}">
				<span class="tn">{l.label}</span>
				<span class="tline"><span class="trail" bind:this={trails[i]} style="transform: translate3d({((first[i] / pieces.length - 1) * 100).toFixed(2)}%, 0, 0)"></span></span>
				<span class="tt" bind:this={timers[i]}>{fmtS(Math.min(T0, ends[i]))}</span>
			</div>
		{/each}
		{#if ratio > 0}
			<p class="verdict">
				<b class="speedup" class:speedup--down={ratio < 1} style="--rh:{heatOf(ratio)}">{fmtRatio(ratio, lang)}</b>
				<small>{t.faster} · {t.same}</small>
			</p>
		{/if}
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
		gap: clamp(0.75rem, 1.6vh, 1.25rem);
	}
	/* the question both lanes answer, set like a typed prompt */
	.prompt {
		display: flex;
		justify-content: center;
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
	/* two frameless streams; a hairline between them. Decorative (the sr-only summary carries the
	 * facts): never selected or copied. */
	.lanes {
		-webkit-user-select: none;
		user-select: none;
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
		align-content: start;
		gap: 0.6rem;
		min-width: 0;
	}
	/* instruments: compact dial · who · small readout (fixed height: never moves the text) */
	.inst {
		display: grid;
		grid-template-columns: var(--g) minmax(0, 1fr) auto;
		align-items: center;
		gap: 1.1rem;
		--g: clamp(4.5rem, 3.5rem + 1.8vw, 5.75rem);
		height: var(--g);
	}
	.gauge {
		width: var(--g);
	}
	.who {
		display: grid;
		gap: 0.15rem;
		min-width: 0;
		overflow: hidden;
	}
	.label {
		font-weight: 680;
		font-size: var(--fs-sm);
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
		display: grid;
		grid-template-columns: auto auto;
		justify-items: end;
		align-items: baseline;
		column-gap: 0.3rem;
		row-gap: 0.15rem;
	}
	.med {
		grid-column: 1 / -1;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.04em;
		color: var(--text-mute);
		white-space: nowrap;
	}
	.med b {
		font-weight: 500;
		color: var(--text);
	}
	.hot .med b {
		color: var(--heat-4);
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
	/* the answer: always complete in layout; unwritten tokens are a dim preview */
	.feed {
		margin: 0;
		font-size: clamp(1rem, 0.85rem + 0.4vw, 1.22rem);
		line-height: 1.55;
		letter-spacing: -0.005em;
		color: rgb(237 234 227 / 0.17);
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
	.strip {
		width: 100%;
		height: 1rem;
	}
	/* ---- the shared finish track ---- */
	.track {
		display: grid;
		/* the verdict has its own fixed slot inside the track: it never pushes past the panel */
		grid-template-columns: minmax(7rem, auto) minmax(0, 1fr) 4.5rem 11.5rem;
		align-items: center;
		column-gap: 1rem;
		row-gap: 0.55rem;
		padding: 1rem 1.1rem;
		border-radius: var(--r-lg);
		background: linear-gradient(90deg, rgb(255 255 255 / 0.025), rgb(255 122 26 / 0.04));
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.trow {
		display: contents;
	}
	.tn {
		grid-column: 1;
		font-size: var(--fs-xs);
		color: var(--text);
		white-space: nowrap;
	}
	.hot .tn {
		color: var(--text-hi);
		font-weight: 650;
	}
	/* the lane line ends in a finish post; the trail (with the runner at its head) slides along it */
	.tline {
		grid-column: 2;
		position: relative;
		height: 0.7rem;
		overflow: hidden;
		border-right: 2px solid var(--text-hi);
		background: repeating-linear-gradient(90deg, rgb(237 234 227 / 0.12) 0 2px, transparent 2px 10px) 0 50% / 100% 1px no-repeat;
	}
	.trail {
		position: absolute;
		inset: 0.25rem 0;
		border-radius: var(--r-pill);
		background: linear-gradient(90deg, transparent, var(--before));
		transition: transform 0.08s linear;
	}
	.trail::after {
		content: '';
		position: absolute;
		right: 0;
		top: 50%;
		width: 0.6rem;
		height: 0.6rem;
		margin-top: -0.3rem;
		border-radius: 50%;
		background: var(--before);
	}
	.hot .trail {
		background: linear-gradient(90deg, transparent, var(--heat-2) 40%, var(--heat-4));
		box-shadow: 0 0 12px rgb(255 122 26 / 0.6);
	}
	.hot .trail::after {
		background: var(--heat-5);
		box-shadow: 0 0 10px var(--heat-4);
	}
	.tt {
		grid-column: 3;
		justify-self: end;
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
		font-variant-numeric: tabular-nums;
		color: var(--text);
		white-space: nowrap;
	}
	.hot .tt {
		color: var(--heat-4);
	}
	/* the result, big, stamped when the fast side crosses the line (always laid out: no shift) */
	.verdict {
		grid-column: 4;
		grid-row: 1 / span 2;
		margin: 0;
		display: grid;
		justify-items: center;
		gap: 0.2rem;
		min-width: 0;
		text-align: center;
		visibility: hidden;
		transform: scale(0.92);
		transition:
			transform 0.4s var(--ease-spring),
			visibility 0s 0.4s;
	}
	.won .verdict {
		visibility: visible;
		transform: none;
		transition:
			transform 0.4s var(--ease-spring),
			visibility 0s;
	}
	.verdict b {
		font-size: clamp(2.4rem, 1.6rem + 2vw, 3.4rem);
		filter: drop-shadow(0 0 18px rgb(255 122 26 / 0.45));
	}
	.verdict small {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--heat-4);
		line-height: 1.3;
	}
	.controls {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: center;
		gap: var(--sp-3);
	}
	.meta {
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
		white-space: nowrap;
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
		transition:
			background var(--dur-2),
			border-color var(--dur-2);
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
	}
	@media (max-width: 640px) {
		.inst {
			--g: 4.25rem;
			gap: 0.8rem;
		}
		.sub {
			display: none;
		}
		.feed {
			font-size: var(--fs-sm);
		}
		.track {
			grid-template-columns: minmax(0, auto) minmax(0, 1fr) 3.6rem;
			padding: 0.8rem;
			column-gap: 0.7rem;
		}
		.tn {
			font-size: var(--fs-2xs);
		}
		.verdict {
			grid-column: 1 / -1;
			grid-row: 3;
			grid-auto-flow: column;
			align-items: baseline;
			gap: 0.6rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.prompt.on .caret,
		.hot .tps,
		.feed :global(.tk.on),
		.hot .feed :global(.tk.on) {
			animation: none;
		}
		.trail,
		.verdict,
		.won .verdict {
			transition: none;
		}
	}
</style>
