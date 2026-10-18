<script lang="ts" module>
	export interface Lane {
		id: string;
		label: string;
		sub?: string;
		tps: number;
		hot: boolean;
	}
</script>

<script lang="ts">
	/**
	 * The race: the same answer streamed in parallel lanes at measured speeds.
	 * Words appear at t/s ÷ tokens-per-word (TOK_PER_WORD, report 06 §2.1.2); each lane has a
	 * tachometer (needle on a spring, stays at the measured value when the lane finishes), a rolling
	 * t/s odometer, a token counter and (optionally) a stopwatch. The answer scrolls in a window of
	 * whole lines with a soft top fade; the hot lane's newest words glow briefly. When the hot lane
	 * finishes, the speed-up is stamped in its own slot beside "gotowe" (never over the text).
	 *
	 * Performance: the clock runs in a plain variable; the rendered state (words, tokens, progress)
	 * updates at most 15×/s, the rAF subscription exists only while playing and on screen. At rest
	 * (server HTML, before it is seen, reduced motion) the race shows its finished state; it plays the
	 * first time it is on screen, and leaving the viewport, a hidden tab or a bfcache restore jumps
	 * to the finished state. Under reduced motion it plays only on request. Pause and replay always work.
	 */
	import { heatOf } from '$lib/cards/explorer';
	import { onMount, untrack } from 'svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { fmtRatio } from '$lib/format';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFinish, onFrame, reducedMotion } from './motion';
	import Odometer from './Odometer.svelte';
	import Tacho from './Tacho.svelte';

	let {
		lanes,
		text,
		lang,
		autoplay = true,
		loop = true,
		hold = 3,
		max,
		redline,
		/** Accessible summary of what the animation shows (numbers + conditions). */
		summary,
		/** Changing this key restarts the race (e.g. when the picker changes card or model). */
		runKey = '',
		/** Show each lane's elapsed seconds (off when the answer length differs from other timings on the page). */
		clock = true,
	}: {
		lanes: Lane[];
		text: string;
		lang: 'pl' | 'en';
		autoplay?: boolean;
		loop?: boolean;
		hold?: number;
		max?: number;
		redline?: number;
		summary: string;
		runKey?: string;
		clock?: boolean;
	} = $props();

	const L = {
		pl: { pause: 'Wstrzymaj wyścig', resume: 'Wznów wyścig', replay: 'Od nowa', done: 'gotowe', tok: 'tokenów', faster: 'szybciej', still: 'wciąż pisze…' },
		en: { pause: 'Pause the race', resume: 'Resume the race', replay: 'Replay', done: 'done', tok: 'tokens', faster: 'faster', still: 'still writing…' }
	};
	const t = $derived(L[lang]);
	const words = $derived(text.split(/\s+/).filter(Boolean));
	const TRAIL = 5;
	/** Render rate of the race state (words, counters, bars): enough to read, cheap to paint. */
	const HZ = 15;
	const totalTok = $derived(Math.round(words.length * TOK_PER_WORD[lang]));
	const ends = $derived(lanes.map((l) => totalTok / l.tps));
	const slowest = $derived(Math.max(...ends));
	const LEAD = 0.7; // seconds of "ready" before the start
	const top = $derived(max ?? Math.ceil((Math.max(...lanes.map((l) => l.tps)) * 1.25) / 20) * 20);
	const red = $derived(redline ?? Math.round(top * 0.7));
	/** Dial tick step: about ten major ticks whatever the scale. */
	const step = $derived(top <= 120 ? 10 : top <= 250 ? 20 : 50);


	/** Rendered clock (quantised to HZ); the real clock is `clockT` below. */
	// svelte-ignore state_referenced_locally
	let elapsed = $state(LEAD + slowest);
	// svelte-ignore state_referenced_locally
	let clockT = LEAD + slowest;
	let playing = $state(false);
	let onScreen = $state(false);
	let reduce = false;
	let started = false;
	/** The finished race (server HTML, offscreen, hidden tab): every lane at its final state. */
	function toEnd() {
		setClock(LEAD + slowest);
		playing = false;
	}

	function setClock(v: number) {
		clockT = v;
		const q = Math.floor(v * HZ) / HZ;
		if (q !== elapsed) elapsed = q;
	}

	onMount(() => {
		reduce = reducedMotion();
		return onFinish(toEnd);
	});
	/** Visibility: the first time the race is on screen it plays (autoplay); leaving mid-race ends it. */
	function seen(v: boolean) {
		onScreen = v;
		if (reduce) return;
		if (v && !started && autoplay) {
			started = true;
			setClock(0);
			playing = true;
		} else if (!v && playing) toEnd();
	}

	// The rAF subscription lives only while the race plays on screen.
	$effect(() => {
		if (!playing || !onScreen) return;
		return untrack(() =>
			onFrame((dt) => {
				const end = LEAD + slowest + (loop ? hold : 0);
				const next = clockT + dt;
				if (next >= end) {
					if (loop && !reduce) setClock(0);
					else {
						setClock(LEAD + slowest);
						playing = false;
						return false;
					}
				} else setClock(next);
			})
		);
	});

	// Restart when the parent swaps the data (not on the first run: onMount decides that).
	let seenKey: string | null = null;
	$effect(() => {
		const k = runKey;
		if (seenKey === null) {
			seenKey = k;
			return;
		}
		seenKey = k;
		untrack(() => {
			if (reduce || !onScreen) toEnd();
			else {
				setClock(0);
				playing = true;
			}
		});
	});

	export function replay() {
		setClock(0);
		playing = true;
	}

	function toggle() {
		if (!playing && clockT >= LEAD + slowest) replay();
		else playing = !playing;
	}

	const run = $derived(Math.max(0, elapsed - LEAD));
	const ls = $derived(
		lanes.map((l, i) => {
			const done = run >= ends[i];
			const tok = Math.min(totalTok, Math.floor(run * l.tps));
			const w = done ? words.length : Math.min(words.length, Math.floor((run * l.tps) / TOK_PER_WORD[lang]));
			return { done, tok, w, time: Math.min(run, ends[i]), running: elapsed > LEAD && !done };
		})
	);
	const hotIdx = $derived(lanes.findIndex((l) => l.hot));
	const coldIdx = $derived(lanes.findIndex((l) => !l.hot));
	const ratio = $derived(hotIdx >= 0 && coldIdx >= 0 ? lanes[hotIdx].tps / lanes[coldIdx].tps : 0);

	const hotDone = $derived(hotIdx >= 0 && ls[hotIdx].done);
</script>

<div class="race" use:visible={seen}>
	<p class="sr-only">{summary}</p>
	<div class="lanes" aria-hidden="true">
		{#each lanes as l, i (l.id)}
			{@const s = ls[i]}
			<div class="lane" class:hot={l.hot} class:done={s.done} class:running={s.running} class:behind={!l.hot && s.running && hotDone} style="--prog:{totalTok ? s.tok / totalTok : 0}">
				<div class="head">
					<span class="label">{l.label}</span>
					{#if l.sub}<span class="sub">{l.sub}</span>{/if}
				</div>
				<div class="gauge">
					<Tacho value={s.running || s.done ? l.tps : 0} glowing={s.running} max={top} redline={red} {step} tone={l.hot ? 'hot' : 'cold'} label="{l.label}: {num(l.tps, lang)} t/s">
						<span class="readout">
							<span class="big"><Odometer value={elapsed > LEAD ? l.tps : 0} decimals={1} {lang} duration={900} minInt={2} /></span>
							<span class="unit">t/s</span>
						</span>
					</Tacho>
				</div>
				<div class="text" class:hot={l.hot}>
					<p>
						{#if s.w > 0}
							{@const shownW = words.slice(0, s.w)}
							{@const trail = l.hot && s.running ? Math.min(TRAIL, shownW.length) : 0}
							{shownW.slice(0, shownW.length - trail).join(' ')}
							{#each shownW.slice(shownW.length - trail) as w, k (s.w - trail + k)}<span class="tw" style="--age:{(trail - 1 - k) / TRAIL}">{w}</span>{' '}{/each}
						{/if}
						{#if s.running}<span class="caret"></span>{/if}
					</p>
				</div>
				<div class="track"><span class="trail"></span></div>
				<div class="foot">
					<span class="tok">{s.tok} / {totalTok} {t.tok}</span>
					<span class="status">
						{#if clock}
							<span class="time" class:stamp={s.done}>{#if s.done}{t.done} · {/if}{num(s.time, lang, 1)} s</span>
						{:else if s.done}
							<span class="time stamp">{t.done}</span>
						{:else if !l.hot && s.running && hotDone}
							<span class="time still">{t.still}</span>
						{/if}
						{#if l.hot && ratio > 0}<span class="stamp-big speedup" class:speedup--down={ratio < 1} class:show={s.done} style="--rh:{heatOf(ratio)}">{fmtRatio(ratio, lang)}</span>{/if}
					</span>
				</div>
			</div>
		{/each}
	</div>
	<div class="controls">
		<button type="button" class="ctl" onclick={toggle} aria-label={playing ? t.pause : t.resume}>
			{#if playing}
				<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z" fill="currentColor" /></svg>
			{:else}
				<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" fill="currentColor" /></svg>
			{/if}
		</button>
		<button type="button" class="ctl" onclick={replay} aria-label={t.replay}>
			<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3 8a5 5 0 1 0 1.6-3.7M3 2.5v2.8h2.8" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" /></svg>
		</button>
	</div>
</div>

<style>
	.race {
		position: relative;
		display: grid;
		gap: var(--sp-4);
	}
	.lanes {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr));
		gap: var(--sp-3);
	}
	.lane {
		position: relative;
		display: grid;
		grid-template-rows: auto auto 1fr auto auto;
		gap: var(--sp-3);
		padding: var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: linear-gradient(180deg, color-mix(in srgb, var(--bg-2) 92%, transparent), color-mix(in srgb, var(--bg-1) 88%, transparent));
		overflow: hidden;
		isolation: isolate;
	}
	.lane.hot::before {
		content: '';
		position: absolute;
		inset: -40% -20% auto;
		height: 80%;
		background: radial-gradient(closest-side, rgb(255 122 26 / 0.22), transparent);
		opacity: 0;
		transition: opacity 0.6s var(--ease-out);
		z-index: -1;
	}
	.lane.hot.running::before {
		opacity: 1;
	}
	.lane.hot.done::before {
		opacity: 0.45;
	}
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-1) var(--sp-3);
	}
	.label {
		font-weight: 700;
		font-stretch: 112%;
		color: var(--text-hi);
		font-size: var(--fs-md);
		letter-spacing: -0.01em;
	}
	.lane:not(.hot) .label {
		color: var(--text);
	}
	.sub {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.gauge {
		width: min(100%, 15rem);
		justify-self: center;
	}
	.readout {
		display: grid;
		justify-items: center;
		gap: 0.15rem;
	}
	.big {
		font-size: clamp(1.4rem, 1rem + 1.4vw, 2rem);
		font-weight: 600;
		color: var(--text-hi);
	}
	.lane:not(.hot) .big {
		color: var(--before);
	}
	.unit {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.1em;
	}
	/* answer text: a window of whole lines (bottom-anchored), soft 24px fade at the top */
	.text {
		--lines: 5;
		position: relative;
		height: calc(var(--lines) * 1.5em);
		overflow: clip;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		mask-image: linear-gradient(transparent, #000 24px);
		font-size: var(--fs-sm);
		line-height: 1.5;
		color: var(--text-mute);
	}
	.text.hot {
		color: var(--text);
	}
	/* heat trail: the hot lane's newest words glow and cool over the last few words */
	.tw {
		color: color-mix(in srgb, var(--heat-4) calc((1 - var(--age)) * 100%), var(--text));
		text-shadow: 0 0 10px rgb(255 122 26 / calc(0.7 * (1 - var(--age))));
	}
	.lane.behind .still {
		color: var(--before);
		animation: blink 1.2s steps(2) infinite;
	}
	.caret {
		display: inline-block;
		width: 0.5em;
		height: 1em;
		margin-left: 0.1em;
		vertical-align: -0.15em;
		background: currentColor;
		animation: blink 0.9s steps(2) infinite;
	}
	.text.hot .caret {
		background: var(--heat-4);
		box-shadow: 0 0 12px var(--heat-3);
	}
	@keyframes blink {
		50% {
			opacity: 0;
		}
	}
	.foot {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: center;
		gap: var(--sp-3);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		font-variant-numeric: tabular-nums;
	}
	.status {
		display: inline-flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		align-items: center;
		gap: var(--sp-3);
	}
	.time.stamp {
		color: var(--text-hi);
	}
	.lane.hot .time.stamp {
		color: var(--heat-4);
	}
	/* the speed-up stamped in its own slot beside "gotowe" when the hot lane finishes */
	.stamp-big {
		font-size: clamp(1.6rem, 1rem + 1.4vw, 2.4rem);
		filter: drop-shadow(0 0 16px rgb(255 122 26 / 0.45));
		opacity: 0;
		transform: scale(1.5);
		transform-origin: 100% 50%;
		transition:
			opacity 0.25s var(--ease-out),
			transform 0.55s var(--ease-spring);
	}
	.stamp-big.show {
		opacity: 1;
		transform: none;
	}
	.controls {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: var(--sp-2);
	}
	.ctl {
		display: inline-grid;
		place-items: center;
		width: 2.75rem;
		height: 2.75rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: var(--bg-2);
		color: var(--text-hi);
		cursor: pointer;
		transition:
			background var(--dur-2),
			transform var(--dur-1);
	}
	.ctl:hover {
		background: var(--bg-3);
	}
	.ctl:active {
		transform: scale(0.94);
	}
	/* progress track: the lane's share of the answer written so far (state at 15 Hz, eased in CSS) */
	.track {
		position: relative;
		height: 3px;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.trail {
		position: absolute;
		inset: 0;
		transform-origin: 0 50%;
		transform: scaleX(var(--prog));
		transition: transform 0.07s linear;
		background: linear-gradient(90deg, #2a3038, var(--before));
	}
	.lane.hot .trail {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 12px rgb(255 122 26 / 0.6);
	}
	@media (max-width: 640px) {
		.controls {
			flex-wrap: wrap;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.caret,
		.lane.behind .still {
			animation: none;
		}
		.trail {
			transition: none;
		}
	}
</style>
