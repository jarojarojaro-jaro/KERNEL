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
	 * The hero race, an endless loop: two lanes, each a large speedometer next to the same short
	 * answer, which is laid out in full from the first frame as a dim preview and lit token by token
	 * at the lane's measured pace. One cycle = the slower side writes the answer once, then a short
	 * rest; in that time the faster side writes as many full answers as its pace fits (2 for
	 * 78,0 vs 38,9 t/s), each followed by its own short rest. A pip per finished answer fills next to
	 * the lane's name. Then both sides restart together, forever. Pause is always available.
	 *
	 * Honesty: tokens are emitted at exactly the measured median t/s, in steps of `burst` tokens
	 * (measured MTP tokens accepted per step, a deterministic 3,3,4,… pattern with the measured
	 * mean). The digits show only the measured median. The motion lives in the needle: while a lane
	 * writes, it breathes within ±3% of the median and ticks on each emitted step (zero-mean); while
	 * the lane rests between answers it falls back towards 0, and it climbs again with the next one.
	 *
	 * The answer is cut into token-sized pieces so the piece count matches TOK_PER_WORD (report 06
	 * §2.1.2); the text is an example, the pace is measured.
	 *
	 * SSR / first paint: the race is shown 0,6 s in (first words lit, needles on the median), and the
	 * client continues from exactly that state. Every token is always laid out (CLS 0): emitting only
	 * toggles a class; the needles move by transform. The frame loop runs only while playing on screen.
	 * Reduced motion: one static frame, both answers complete, needles on the median, no loop.
	 */
	import type { Snippet } from 'svelte';
	import { onMount, untrack } from 'svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFrame, reducedMotion, Spring, whenIdle } from './motion';
	import Speedo from './Speedo.svelte';

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
		pl: { pause: 'Wstrzymaj wyścig', resume: 'Wznów wyścig', live: 'na żywo', paused: 'pauza', median: 'zmierzone', answers: 'odpowiedzi' },
		en: { pause: 'Pause the race', resume: 'Resume the race', live: 'live', paused: 'paused', median: 'measured', answers: 'answers' }
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
	/** Each side's time for one answer: tokens ÷ measured median t/s. */
	const ends = $derived(lanes.map((l) => pieces.length / l.tps));
	const slowest = $derived(Math.max(...ends));
	/** One cycle: the slower side's answer plus a short rest; both sides restart together after it. */
	const cycle = $derived(slowest + Math.max(1.4, 0.45 * slowest));
	/** Full answers per cycle: as many as the side's pace fits into the slower side's one. */
	const passes = $derived(ends.map((e) => Math.max(1, Math.floor(slowest / e + 1e-9))));
	const slots = $derived(passes.map((n) => cycle / n));
	/** The race as first painted (and continued from by the client). */
	const T0 = 0.6;
	/** Seconds the heat field runs hot at the start of each cycle. */
	const HEAT_S = 2.6;
	const step = $derived(max <= 120 ? 20 : max <= 250 ? 50 : 100);

	/** Deterministic emission: tokens written and steps taken after `time` seconds at the median. */
	function runAt(l: LiveLane, time: number) {
		const burst = l.burst ?? 1;
		let budget = l.tps * time;
		let acc = 0;
		let pos = 0;
		let steps = 0;
		let k = Math.floor(burst);
		while (budget >= k && pos < pieces.length) {
			budget -= k;
			acc += burst;
			pos = Math.min(pieces.length, pos + k);
			steps++;
			k = Math.floor(acc + burst) - Math.floor(acc);
		}
		return { pos, steps };
	}
	/** Lane `i` at cycle time `tm`: tokens lit, steps taken, writing or resting, answers finished. */
	function laneAt(i: number, tm: number) {
		const s = Math.min(passes[i] - 1, Math.floor(tm / slots[i]));
		const tau = tm - s * slots[i];
		const writing = tau < ends[i];
		const r = writing ? runAt(lanes[i], tau) : { pos: pieces.length, steps: Infinity };
		return { pass: s, writing, pos: r.pos, steps: r.steps, done: s + (writing ? 0 : 1) };
	}

	const first = $derived(lanes.map((_, i) => laneAt(i, T0)));

	let playing = $state(false);
	let onScreen = $state(false);
	/** Answers finished this cycle, per lane (fills the pips). */
	// svelte-ignore state_referenced_locally
	let done = $state(first.map((f) => f.done));
	/** The lane is resting between answers (the needle falls, the digits dim). */
	// svelte-ignore state_referenced_locally
	let resting = $state(first.map((f) => !f.writing));
	let feeds: HTMLElement[] = $state([]);
	let dials: Speedo[] = $state([]);

	let clock = T0;
	// svelte-ignore state_referenced_locally
	let lit = first.map((f) => f.pos);
	// svelte-ignore state_referenced_locally
	let stepsSeen = first.map((f) => f.steps);
	// svelte-ignore state_referenced_locally
	let passSeen = first.map((f) => f.pass);
	// svelte-ignore state_referenced_locally
	const springs = lanes.map((l) => new Spring(l.tps, 90, 16));
	// svelte-ignore state_referenced_locally
	const kick = lanes.map(() => 0);
	// svelte-ignore state_referenced_locally
	const phase = lanes.map((_, i) => i * 2.1 + 0.7);

	/** Light (or, after a restart, dim) the lane's tokens so exactly `pos` are lit. */
	function light(i: number, pos: number) {
		const f = feeds[i];
		if (!f || pos === lit[i]) return;
		const kids = f.children;
		if (pos > lit[i]) for (let j = lit[i]; j < pos; j++) kids[j]?.classList.add('on');
		else for (let j = pos; j < lit[i]; j++) kids[j]?.classList.remove('on');
		lit[i] = pos;
		follow(i);
	}
	/** Narrow windows: keep the newest lit line at the bottom (transform; no-op when the text fits). */
	const shift: number[] = [];
	function follow(i: number) {
		const f = feeds[i];
		const win = f?.parentElement;
		if (!f || !win) return;
		const h = win.clientHeight;
		const last = f.children[Math.max(0, lit[i] - 1)] as HTMLElement | undefined;
		const y = h >= f.offsetHeight || !last || lit[i] === 0 ? 0 : Math.max(0, Math.min(f.offsetHeight - h, last.offsetTop + last.offsetHeight - h));
		if (y !== shift[i]) {
			shift[i] = y;
			f.style.transform = y ? `translate3d(0, ${-y}px, 0)` : '';
		}
	}

	/** Live needle target while writing: the median × (1 + 3% × m), m ∈ [−1, 1] from three sines. */
	function readoutAt(i: number, time: number) {
		const p = phase[i];
		const m = 0.5 * Math.sin(time * 2.3 + p) + 0.3 * Math.sin(time * 4.1 + 2 * p) + 0.2 * Math.sin(time * 7.7 + 3 * p);
		return lanes[i].tps * (1 + 0.03 * m);
	}

	/** Put every lane at cycle time `tm` at once (no needle physics): first paint, reduced motion. */
	function seek(tm: number) {
		lanes.forEach((_, i) => {
			const s = laneAt(i, tm);
			light(i, s.pos);
			stepsSeen[i] = s.steps;
			passSeen[i] = s.pass;
			follow(i);
		});
		done = lanes.map((_, i) => laneAt(i, tm).done);
		resting = lanes.map((_, i) => !laneAt(i, tm).writing);
	}

	onMount(() => {
		// the SSR markup already shows T0; align the bookkeeping with the DOM
		lit = lanes.map((_, i) => feeds[i]?.querySelectorAll('.tk.on').length ?? 0);
		if (reducedMotion()) {
			// one readable frame: both answers complete, needles on the median, every pip filled
			lanes.forEach((_, i) => light(i, pieces.length));
			done = [...passes];
			resting = lanes.map(() => false);
			return;
		}
		seek(T0);
		return whenIdle(() => {
			playing = true;
			onheat?.(true);
		});
	});

	// the frame loop lives only while playing on screen
	$effect(() => {
		if (!playing || !onScreen) return;
		return untrack(() =>
			onFrame((dt) => {
				const d = Math.min(dt, 0.1);
				const before = clock % cycle;
				clock += d;
				const tm = clock % cycle;
				const restart = tm < before;
				if (restart) onheat?.(true);
				else if (before < HEAT_S && tm >= HEAT_S) onheat?.(false);
				let nd: number[] | null = null;
				let nr: boolean[] | null = null;
				for (let i = 0; i < lanes.length; i++) {
					const l = lanes[i];
					const s = laneAt(i, tm);
					const fresh = s.pass !== passSeen[i] || restart;
					if (fresh) {
						passSeen[i] = s.pass;
						stepsSeen[i] = 0;
						light(i, 0);
					}
					// a zero-mean tick per emitted step: bigger steps than the mean kick up, smaller down
					if (s.writing && s.steps > stepsSeen[i]) {
						const burst = l.burst ?? 1;
						kick[i] += (s.pos - lit[i] - (s.steps - stepsSeen[i]) * burst) * 0.015 * l.tps;
						stepsSeen[i] = s.steps;
					}
					light(i, s.pos);
					const sp = springs[i];
					sp.target = s.writing ? readoutAt(i, clock) : 0;
					sp.step(d);
					kick[i] *= Math.exp(-d / 0.09);
					dials[i]?.set(Math.max(0, sp.x + kick[i]));
					if (s.done !== done[i]) (nd ??= [...done])[i] = s.done;
					if (!s.writing !== resting[i]) (nr ??= [...resting])[i] = !s.writing;
				}
				if (nd) done = nd;
				if (nr) resting = nr;
			})
		);
	});

	function toggle() {
		playing = !playing;
		onheat?.(playing && clock % cycle < HEAT_S);
	}
</script>

<div class="live" use:visible={(v) => (onScreen = v)}>
	<p class="sr-only">{summary}</p>
	<!-- race header: the question (chip) on the left, model · card · source · live · pause on the right -->
	<div class="controls">
		{#if prompt}<p class="prompt" class:on={playing} aria-hidden="true"><span class="caret">›</span>{prompt}</p>{/if}
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
	<div class="lanes" aria-hidden="true">
		{#each lanes as l, i (l.id)}
			<div class="lane" class:hot={l.hot} class:rest={resting[i]}>
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
						<div class="tally">
							<span class="tl">{t.answers}</span>
							{#each { length: passes[i] }, j (j)}<span class="pip" class:on={j < done[i]}></span>{/each}
						</div>
					</div>
					<!-- the whole answer, always laid out: dim preview, lit as the lane writes it -->
					<div class="win"><p class="feed" bind:this={feeds[i]}>{#each pieces as piece, j (j)}<span class="tk" class:on={j < first[i].pos}>{piece}</span>{/each}</p></div>
				</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.live {
		display: grid;
		gap: clamp(0.9rem, 2vh, 1.5rem);
	}
	/* the question both lanes answer, set like a typed prompt */
	.prompt {
		margin: 0 auto 0 0;
		display: inline-flex;
		align-items: baseline;
		gap: 0.5rem;
		padding: 0.3rem 0.75rem;
		border: 1px solid rgb(255 122 26 / 0.35);
		border-radius: var(--r-pill);
		background: rgb(255 122 26 / 0.06);
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
	.controls {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
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
	/* two lanes side by side, a hairline between them. Decorative (the sr-only summary carries the
	 * facts): never selected or copied. */
	.lanes {
		-webkit-user-select: none;
		user-select: none;
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		column-gap: clamp(1rem, 4.5vw, 4.5rem);
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
	/* wide: the big dial on the left, name and the answer on the right */
	.lane {
		--g: clamp(10rem, min(5rem + 13vw, 33svh), 18rem);
		position: relative;
		display: grid;
		grid-template-columns: var(--g) minmax(0, 1fr);
		align-items: center;
		column-gap: clamp(1rem, 2vw, 1.75rem);
		min-width: 0;
	}
	.dial {
		width: var(--g);
		min-width: 0;
	}
	.body {
		container: lanebody / inline-size;
		display: grid;
		align-content: center;
		gap: 0.75rem;
		min-width: 0;
	}
	/* name and the answer pips on one line, the setup below */
	.head {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		grid-template-areas: 'label tally' 'sub sub';
		align-items: center;
		gap: 0.2rem 0.75rem;
		min-width: 0;
	}
	.label {
		grid-area: label;
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
		grid-area: sub;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	/* one pip per answer the lane finishes in a cycle */
	.tally {
		grid-area: tally;
		display: flex;
		align-items: center;
		gap: 0.35rem;
		flex: none;
		padding-bottom: 0.15rem;
	}
	.tl {
		margin-right: 0.15rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.pip {
		width: 0.7rem;
		height: 0.7rem;
		border-radius: 50%;
		box-shadow: inset 0 0 0 1.5px var(--line-strong);
		transition:
			background 0.25s,
			box-shadow 0.25s;
	}
	.pip.on {
		background: var(--before);
		box-shadow: inset 0 0 0 1.5px var(--before);
		animation: pip 0.5s var(--ease-spring);
	}
	.hot .pip.on {
		background: var(--heat-4);
		box-shadow:
			inset 0 0 0 1.5px var(--heat-4),
			0 0 12px rgb(255 122 26 / 0.75);
	}
	@keyframes pip {
		from {
			transform: scale(1.8);
		}
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
		transition: opacity 0.35s var(--ease-out);
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
	.rest .tps {
		opacity: 0.45;
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
	/* the answer: always complete in layout; unwritten tokens are a dim preview. Five lines,
	 * following the newest one (transform only). */
	.win {
		position: relative;
		overflow: clip;
		height: calc(5 * 1.5em);
		font-size: clamp(0.95rem, 0.8rem + 0.35vw, 1.15rem);
		mask-image: linear-gradient(transparent, #000 0.9em);
	}
	.feed {
		margin: 0;
		transition: transform 0.2s var(--ease-out);
		font-size: inherit;
		line-height: 1.5;
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
	/* a narrow text column beside the dial: name, setup and pips each on their own line */
	@container lanebody (max-width: 22rem) {
		.head {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'label' 'sub' 'tally';
			justify-items: start;
		}
	}
	/* narrower: each lane is a column, the dial on top as large as the column and the screen allow */
	@media (max-width: 1000px) {
		.lane {
			--g: min(100%, clamp(8rem, 30svh, 16rem));
			grid-template-columns: minmax(0, 1fr);
			justify-items: center;
			align-items: start;
			row-gap: 0.85rem;
		}
		.body {
			width: 100%;
		}
		.head {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'label' 'sub' 'tally';
			justify-items: center;
			gap: 0.3rem;
			text-align: center;
		}
		.tally {
			padding-bottom: 0;
		}
		.win {
			height: calc(4 * 1.5em);
		}
		.state {
			display: none;
		}
	}
	/* small tablets and phones: the prompt on its own line, then model · card · source · pause */
	@media (max-width: 760px) {
		.controls {
			gap: 0.45rem 0.6rem;
		}
		.prompt {
			flex: 1 0 100%;
			min-width: 0;
			padding: 0;
			border: 0;
			background: none;
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}
		.meta {
			flex: 1 1 0;
			flex-wrap: nowrap;
			white-space: nowrap;
		}
	}
	/* phones: compact names, four short lines of the answer */
	@media (max-width: 640px) {
		.lanes {
			column-gap: 1.1rem;
		}
		.lane {
			row-gap: 0.6rem;
		}
		.sub,
		.tl {
			display: none;
		}
		.label {
			font-size: 0.85rem;
		}
		.pip {
			width: 0.55rem;
			height: 0.55rem;
		}
		.win {
			height: calc(4 * 1.45em);
			font-size: 0.8rem;
		}
		.feed {
			line-height: 1.45;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.prompt.on .caret,
		.hot .tps,
		.pip.on,
		.feed :global(.tk.on),
		.hot .feed :global(.tk.on) {
			animation: none;
		}
		.feed {
			transition: none;
		}
	}
</style>
