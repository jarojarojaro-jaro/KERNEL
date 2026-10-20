<script lang="ts" module>
	export interface DuelLane {
		id: 'cold' | 'hot';
		/** "Bez Podkrętu" / "Z Podkrętem". */
		tag: string;
		/** The variant's name ("Typowa aplikacja" / "Nasz silnik"). */
		who: string;
		/** Measured decode speed (t/s, the median). */
		tps: number;
		/** Measured tokens accepted per step (MTP); 1 without speculation. */
		burst: number;
	}
</script>

<script lang="ts">
	/**
	 * Two terminal panes, side by side, streaming the same answer nonstop: without Podkręt (cold,
	 * steel) and with it (hot, a turning heat edge), at exactly the measured median t/s; the hot side
	 * emits in steps of the measured MTP tokens per step. Each pane follows its newest line and wraps
	 * from the end of the answer straight into the next copy, so the stream is endless; under it a
	 * counter of tokens written grows, ours at the measured ratio, with our live lead. Used by the
	 * hero (with a small speedometer in each header, `dial`) and the final CTA.
	 *
	 * The text is an example, the pace is measured. Every token is laid out from the first frame
	 * (two stacked copies per pane); writing only toggles classes, the window moves by transform.
	 * The loop runs only while on screen and not paused, and continues where it stopped. SSR, no JS
	 * and reduced motion: one static frame `T0` seconds in (ours has written as much more as it is
	 * faster), no loop. With JS the dials read 0 until the loop first runs, then climb to the
	 * measured speed and stay there, never still: ours swings ±7% fast with a twitch on every MTP
	 * step (alternating sign), the typical app wobbles ±3% slowly; both are zero-mean, so the
	 * needle's average is exactly the measured median.
	 *
	 * `seam` (the hero): each rate sits in its header's top-right corner and the speed-up is one
	 * glowing badge on the seam between the panes (stacked panes on phones: between them).
	 */
	import type { Snippet } from 'svelte';
	import { onMount, untrack } from 'svelte';
	import Ratio from '$lib/cards/Ratio.svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFrame, reducedMotion, Spring } from './motion';
	import Speedo from './Speedo.svelte';

	let {
		lanes,
		gain,
		text,
		lang,
		labels,
		summary,
		caption,
		dial,
		countUp = false,
		seam = false,
		onstart
	}: {
		/** [cold, hot]. */
		lanes: DuelLane[];
		/** The measured speed-up (hot ÷ cold, or the run's measured total). */
		gain: number;
		text: string;
		lang: 'pl' | 'en';
		labels: { faster: string; tokens: string; pause: string; resume: string };
		/** The facts for screen readers (the panes are decorative). */
		summary: string;
		/** Left of the pause button, e.g. card · model · a note. */
		caption?: Snippet;
		/** A small speedometer in each pane header, on this scale. */
		dial?: { max: number; redline: number };
		/** Count the speed-up up from 1× when the stream first runs. */
		countUp?: boolean;
		/** Rates in the header corners, the speed-up as a badge between the panes. */
		seam?: boolean;
		/** The stream ran its first frame (e.g. a one-time flare). */
		onstart?: () => void;
	} = $props();

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
	const N = $derived(pieces.length);
	const hot = $derived(lanes[lanes.length - 1]);

	/** Tokens written after `t` seconds: whole MTP steps at the measured pace (mean = measured t/s). */
	const written = (l: DuelLane, t: number) => Math.floor(Math.floor((l.tps * t) / l.burst) * l.burst);
	/** Lit tokens in the two stacked copies: the first pass fills copy 1, then the head cycles in copy 2. */
	const headOf = (pos: number) => (pos < 2 * N ? pos : N + ((pos - N) % N));
	/** The static frame: ours is 90% through the answer, the slower side further back. */
	const T0 = $derived((0.9 * N) / hot.tps);
	const first = $derived(lanes.map((l) => written(l, T0)));
	const step = $derived(dial ? (dial.max <= 120 ? 20 : dial.max <= 250 ? 50 : 100) : 20);

	let playing = $state(true);
	let onScreen = $state(false);
	/** The loop has run at least one frame (count-up, dial climb). */
	let ran = $state(false);
	let feeds: HTMLElement[] = $state([]);
	let counts: HTMLElement[] = $state([]);
	let dials: Speedo[] = $state([]);
	let aheadEl: HTMLElement | undefined = $state();

	// per lane: spans, their line tops (cached on resize), lit count, window shift
	let spans: HTMLElement[][] = [];
	let tops: number[][] = [];
	let jump: number[] = [];
	let lineH = 0;
	let winH: number[] = [];
	let lit: number[] = [];
	let shown: number[] = [];
	let y: number[] = [0, 0];
	let clock = 0;
	let live = 0;
	// svelte-ignore state_referenced_locally
	const springs = lanes.map((l) => (l.id === 'hot' ? new Spring(0, 320, 16) : new Spring(0, 30, 10)));
	/** Per lane: MTP steps seen and the step twitch (alternating sign, decays in ~40 ms). */
	const stepsSeen = [0, 0];
	const kick = [0, 0];
	/** The speed-up badge's burst pulse (0..1) and its layers (seam mode). */
	let pulse = 0;
	let coreEl: HTMLElement | undefined = $state();
	let bloomEl: HTMLElement | undefined = $state();

	function measure() {
		feeds.forEach((f, i) => {
			if (!f) return;
			const ps = f.children as HTMLCollectionOf<HTMLElement>;
			lineH = parseFloat(getComputedStyle(ps[0]).lineHeight) || lineH;
			// line tops: an inline box's offsetTop is its content area, centred in the line
			tops[i] = spans[i].map((s) => s.offsetTop - (lineH - s.offsetHeight) / 2);
			jump[i] = ps[1] ? ps[1].offsetTop - ps[0].offsetTop : 0;
			winH[i] = f.parentElement?.clientHeight ?? 0;
		});
	}
	/** Light exactly `d` tokens of lane `i` (adds while writing, clears copy 2 when the head wraps). */
	function light(i: number, d: number) {
		const s = spans[i];
		if (!s || d === lit[i]) return;
		s[lit[i] - 1]?.classList.remove('hd');
		if (d > lit[i]) for (let j = lit[i]; j < d; j++) s[j].classList.add('on');
		else {
			for (let j = d; j < lit[i]; j++) s[j].classList.remove('on');
			// the head jumped back one copy: so does the window, the text above it is identical
			y[i] -= jump[i];
		}
		s[d - 1]?.classList.add('hd');
		lit[i] = d;
	}
	const FOLLOW = 0.07;
	/** Window shift that keeps the newest line near the bottom; the headroom covers the smooth
	 * follow's lag at this lane's scroll speed (px/s = t/s × copy height ÷ tokens per copy). */
	const target = (i: number) => Math.max(0, (tops[i]?.[Math.max(0, lit[i] - 1)] ?? 0) + lineH * 1.3 + (lanes[i].tps * (jump[i] ?? 0) * FOLLOW) / N - winH[i]);
	function place(i: number) {
		const f = feeds[i];
		if (!f) return;
		f.style.transform = y[i] > 0.5 ? `translate3d(0, ${(-y[i]).toFixed(1)}px, 0)` : '';
		// the top fades only once older lines scroll out (the first lines stay whole)
		f.parentElement?.classList.toggle('scrolled', y[i] > 0.5);
	}
	function count(i: number, pos: number) {
		if (pos === shown[i] || !counts[i]) return;
		shown[i] = pos;
		counts[i].textContent = num(pos, lang, 0);
		if (aheadEl) aheadEl.textContent = `+${num(shown[1] - shown[0], lang, 0)}`;
	}
	function seek(t: number, snap: boolean, dt = 0) {
		lanes.forEach((l, i) => {
			const pos = written(l, t);
			light(i, headOf(pos));
			count(i, pos);
			const to = target(i);
			y[i] = snap ? to : y[i] + (to - y[i]) * (1 - Math.exp(-dt / FOLLOW));
			place(i);
		});
	}
	/** Dial target: the median × (1 + a × m), m ∈ [−1, 1] from three sines (zero mean); ours ±7%
	 * at ~1–5 Hz, the typical app ±3% at ~0.1–0.7 Hz. */
	function readout(i: number, time: number) {
		const p = i * 2.1 + 0.7;
		const hot = lanes[i].id === 'hot';
		const [a, w] = hot ? [0.07, 6.3] : [0.03, 0.9];
		const m = 0.5 * Math.sin(time * w + p) + 0.3 * Math.sin(time * w * 2.13 + 2 * p) + 0.2 * Math.sin(time * w * 4.7 + 3 * p);
		return lanes[i].tps * (1 + a * m);
	}

	const rm = typeof window !== 'undefined' && reducedMotion();
	onMount(() => {
		spans = feeds.map((f) => Array.from(f.querySelectorAll<HTMLElement>('.tk')));
		lit = feeds.map((f) => f.querySelectorAll('.tk.on').length);
		shown = [...first];
		clock = T0;
		measure();
		seek(T0, true);
		// reduced motion: the dials rest on the measured speed; otherwise they read 0 until the loop runs
		dials.forEach((d, i) => d?.set(rm ? lanes[i].tps : 0));
		const ro = new ResizeObserver(() => {
			measure();
			lanes.forEach((_, i) => {
				y[i] = target(i);
				place(i);
			});
		});
		feeds.forEach((f) => f && ro.observe(f));
		return () => ro.disconnect();
	});

	// the frame loop lives only while playing on screen (never under reduced motion)
	$effect(() => {
		if (rm || !playing || !onScreen) return;
		return untrack(() =>
			onFrame((dt) => {
				const d = Math.min(dt, 0.1);
				if (!ran) {
					ran = true;
					onstart?.();
				}
				clock += d;
				live += d;
				seek(clock, false, d);
				for (let i = 0; i < dials.length; i++) {
					const l = lanes[i];
					const s = springs[i];
					s.target = readout(i, live);
					s.step(d);
					// our side twitches on every MTP step: ±2,5%, alternating, so it averages out
					const steps = Math.floor((l.tps * live) / l.burst);
					if (l.id === 'hot' && steps > stepsSeen[i]) {
						const sign = steps % 2 ? 1 : -1;
						kick[i] = sign * 0.025 * l.tps * (0.7 + 0.3 * Math.abs(Math.sin(steps * 1.7)));
						// the speed-up badge fires with our bursts (every 6th step, ~6 Hz: visible, not a buzz)
						if (steps % 6 === 0) pulse = 1;
					}
					stepsSeen[i] = steps;
					kick[i] *= Math.exp(-d / 0.04);
					dials[i]?.set(Math.max(0, s.x + kick[i]));
				}
				if (coreEl && bloomEl) {
					pulse *= Math.exp(-d / 0.11);
					coreEl.style.transform = `scale(${(1 + 0.045 * pulse).toFixed(4)})`;
					bloomEl.style.opacity = (0.6 + 0.4 * pulse).toFixed(3);
				}
			})
		);
	});
</script>

<figure class="duel" class:run={playing && onScreen && !rm} use:visible={(v) => (onScreen = v)}>
	<p class="sr-only">{summary}</p>
	<div class="panes" class:seam aria-hidden="true">
		{#each lanes as l, i (l.id)}
			{@const d = headOf(first[i])}
			<div class="pane {l.id}">
				{#if l.id === 'hot'}<span class="edge"></span>{/if}
				<div class="face">
					<header class="ph">
						<div class="row" class:dialed={!!dial} class:corner={seam}>
							{#if dial}
								<div class="gauge">
									<Speedo bind:this={dials[i]} value={l.tps} max={dial.max} redline={dial.redline} {step} tone={l.id} compact />
								</div>
							{/if}
							<div class="info">
								<p class="tag"><span class="dot"></span>{l.tag}</p>
								<p class="who">{l.who}</p>
								{#if !seam}<p class="rate"><b>{num(l.tps, lang)}</b><span>t/s</span></p>{/if}
								{#if l.id === 'hot' && !seam}<p class="gain"><Ratio value={gain} {lang} size="sm" replay={countUp && ran ? 1 : 0} duration={1400} /><span>{labels.faster}</span></p>{/if}
							</div>
							{#if seam}<p class="rate"><b>{num(l.tps, lang)}</b><span>t/s</span></p>{/if}
						</div>
					</header>
					<div class="win" data-clip-ok>
						<div class="feed" bind:this={feeds[i]}>
							{#each [0, 1] as k (k)}
								<p>
									{#each pieces as p, j (j)}<span class="tk" class:on={k * N + j < d} class:hd={k * N + j === d - 1}>{p}</span>{/each}
								</p>
							{/each}
						</div>
					</div>
					<p class="ct">
						<b bind:this={counts[i]}>{num(first[i], lang, 0)}</b> {labels.tokens}
						{#if l.id === 'hot'}<span class="ahead" bind:this={aheadEl}>+{num(first[1] - first[0], lang, 0)}</span>{/if}
					</p>
				</div>
			</div>
		{/each}
		{#if seam}
			<p class="seamgain">
				<span class="pill">
					<span class="bloom" bind:this={bloomEl}></span>
					<span class="ring"></span>
					<span class="core" bind:this={coreEl}><Ratio value={gain} {lang} size="md" replay={countUp && ran ? 1 : 0} duration={1400} /><span class="fx">{labels.faster}</span></span>
				</span>
			</p>
		{/if}
	</div>
	<figcaption class="cap">
		{#if caption}{@render caption()}{/if}
		<button type="button" class="pp" aria-pressed={!playing} aria-label={playing ? labels.pause : labels.resume} title={playing ? labels.pause : labels.resume} onclick={() => (playing = !playing)}>
			{#if playing}<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.5" y="2" width="2.4" height="8" rx="0.6" /><rect x="7.1" y="2" width="2.4" height="8" rx="0.6" /></svg>
			{:else}<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 2.2v7.6L10 6z" /></svg>{/if}
		</button>
	</figcaption>
</figure>

<style>
	.duel {
		margin: 0;
		display: grid;
		gap: var(--sp-4);
		min-width: 0;
	}
	/* both panes share three rows (header, window, counter): the windows always line up */
	.panes {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		grid-template-rows: auto auto auto;
		--cg: clamp(0.6rem, 1.5vw, 1.25rem);
		gap: 0 var(--cg);
	}

	/* a terminal pane; always dark, also in the light theme */
	.pane {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		--before: #7d8794;
		color-scheme: dark;
		position: relative;
		display: grid;
		grid-row: span 3;
		grid-template-rows: subgrid;
		border-radius: var(--r-lg);
		overflow: hidden;
		isolation: isolate;
		min-width: 0;
	}
	.face {
		position: relative;
		display: grid;
		grid-row: 1 / -1;
		grid-template-rows: subgrid;
		border-radius: inherit;
		background: linear-gradient(180deg, #101114, #0a0a0c);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.hot .face {
		margin: 1.5px;
		border-radius: calc(var(--r-lg) - 1.5px);
		background:
			radial-gradient(90% 55% at 50% 100%, rgb(255 122 26 / 0.2), transparent 70%),
			linear-gradient(180deg, #15100c, #0b0806);
		box-shadow: inset 0 1px 0 rgb(255 243 214 / 0.08);
	}
	.hot {
		box-shadow:
			0 0 0 1px rgb(255 122 26 / 0.25),
			0 0 60px -12px rgb(255 122 26 / 0.45),
			0 30px 60px -30px rgb(226 64 28 / 0.6);
	}
	/* the hot pane's living heat edge: a conic square turned by transform (compositor only) */
	.edge {
		position: absolute;
		z-index: -1;
		left: 50%;
		top: 50%;
		width: 160%;
		aspect-ratio: 1;
		translate: -50% -50%;
		background: conic-gradient(var(--heat-2), var(--heat-3) 10%, var(--heat-5) 17%, var(--heat-4) 24%, rgb(255 122 26 / 0.18) 40%, rgb(255 122 26 / 0.1) 75%, var(--heat-2));
		animation: turn 5s linear infinite paused;
		will-change: transform;
	}
	.run .edge {
		animation-play-state: running;
	}
	@keyframes turn {
		to {
			transform: rotate(1turn);
		}
	}

	.ph {
		padding: var(--sp-4) var(--sp-4) var(--sp-3);
		border-bottom: 1px solid rgb(255 255 255 / 0.07);
		/* the big rate and the dial scale with the header (not on .pane: containment breaks its subgrid) */
		container-type: inline-size;
	}
	/* with a dial: the small speedometer left of the header text */
	.row.dialed {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
		gap: var(--sp-3) var(--sp-4);
	}
	.gauge {
		width: clamp(3.75rem, 20cqi, 5.75rem);
	}
	.info {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		align-content: flex-start;
		gap: 0.2rem var(--sp-3);
		min-width: 0;
	}
	.info p {
		margin: 0;
	}
	.tag,
	.who,
	.ct {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.tag {
		flex-basis: 100%;
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text);
	}
	.hot .tag {
		color: var(--heat-4);
	}
	.dot {
		width: 0.42rem;
		height: 0.42rem;
		border-radius: 50%;
		background: var(--before);
	}
	.hot .dot {
		background: var(--heat-3);
		box-shadow: 0 0 10px var(--heat-3);
	}
	.who {
		flex-basis: 100%;
		min-width: 0;
	}
	/* the rate takes its full width (flex item, no shrink); the speed-up wraps below when it must */
	.rate {
		flex: 0 0 auto;
		display: flex;
		align-items: baseline;
		gap: 0.35rem;
		margin-top: var(--sp-2) !important;
	}
	.rate b {
		/* "114,8" in tabular digits: at most ~3.3em wide, so 15cqi keeps it inside a narrow header */
		font-family: var(--font-display);
		font-size: clamp(1.75rem, 15cqi, 3.6rem);
		font-weight: 850;
		font-stretch: 120%;
		letter-spacing: -0.03em;
		line-height: 1;
		font-variant-numeric: tabular-nums lining-nums;
		white-space: nowrap;
		min-width: 4ch;
		color: var(--before);
		/* room for the glyphs' overhang (stretched cut, tight tracking): the clipped heat must reach it */
		padding: 0.04em 0.12em 0.12em 0.02em;
		margin: -0.04em -0.12em -0.12em -0.02em;
	}
	.hot .rate b {
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 18px rgb(255 122 26 / 0.5));
	}
	.rate span {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.gain {
		margin-left: auto !important;
		display: grid;
		justify-items: end;
		gap: 0.15rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	/* with a dial the rate has less room: it scales with the header text column instead */
	.dialed .rate b {
		font-size: clamp(1.6rem, 12cqi, 3.2rem);
	}

	/* the stream window: the newest line sits at the bottom, older lines fade out at the top */
	.win {
		position: relative;
		height: var(--duel-win, 12rem);
		overflow: hidden;
		padding-inline: var(--sp-4);
		--fade: 0;
		-webkit-mask: linear-gradient(rgb(0 0 0 / calc(1 - var(--fade))), #000 32%);
		mask: linear-gradient(rgb(0 0 0 / calc(1 - var(--fade))), #000 32%);
		transition: --fade 0.6s var(--ease-out);
	}
	.win:global(.scrolled) {
		--fade: 1;
	}
	@property --fade {
		syntax: '<number>';
		inherits: false;
		initial-value: 0;
	}
	.feed {
		position: relative;
		padding-bottom: 0.2rem;
	}
	.feed p {
		margin: 0 0 1.6em;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		line-height: 1.6;
		overflow-wrap: anywhere;
	}
	.tk {
		opacity: 0;
		color: var(--before);
	}
	.tk.on {
		opacity: 1;
	}
	.hot .tk {
		color: var(--text-hi);
	}
	@media (prefers-reduced-motion: no-preference) {
		.run .hot .tk.on {
			animation: tk 0.7s ease-out;
		}
	}
	@keyframes tk {
		from {
			color: var(--heat-4);
			text-shadow: 0 0 10px rgb(255 122 26 / 0.8);
		}
	}
	/* the cursor after the newest token (out of flow: moving it never reflows the text) */
	.tk.hd {
		position: relative;
	}
	.tk.hd::after {
		content: '';
		position: absolute;
		left: 100%;
		top: 50%;
		width: 0.55em;
		height: 1.1em;
		translate: 0.1em -50%;
		background: var(--before);
	}
	.hot .tk.hd::after {
		background: var(--heat-4);
		box-shadow: 0 0 10px var(--heat-3);
	}
	.ct {
		margin: 0;
		padding: var(--sp-3) var(--sp-4);
		border-top: 1px solid rgb(255 255 255 / 0.07);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem 0.4rem;
	}
	.ct b {
		white-space: nowrap;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		color: var(--before);
	}
	.hot .ct b {
		color: var(--heat-4);
	}
	/* how many tokens ahead our side is, growing live */
	.ahead {
		white-space: nowrap;
		padding: 0.1rem 0.4rem;
		border-radius: var(--r-pill);
		background: rgb(255 122 26 / 0.16);
		box-shadow: inset 0 0 0 1px rgb(255 122 26 / 0.4);
		color: var(--heat-4);
		font-variant-numeric: tabular-nums;
	}

	.cap {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.pp {
		display: inline-grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		margin-left: auto;
		padding: 0;
		border: 1px solid var(--line-strong);
		border-radius: 50%;
		background: transparent;
		color: var(--text);
		cursor: pointer;
		transition:
			border-color var(--dur-2),
			color var(--dur-2);
	}
	.pp:hover {
		border-color: var(--text-hi);
		color: var(--text-hi);
	}
	.pp:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.pp svg {
		width: 0.75rem;
		height: 0.75rem;
		fill: currentColor;
	}
	@media (prefers-reduced-motion: reduce) {
		.pp {
			display: none;
		}
		.ring::before {
			animation: none;
		}
	}

	/* ---- seam layout (the hero): rates in the header corners, the speed-up between the panes ---- */
	.panes.seam {
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
	}
	.seam .pane.cold {
		grid-column: 1;
		grid-row: 1 / span 3;
	}
	.seam .pane.hot {
		grid-column: 3;
		grid-row: 1 / span 3;
	}
	.row.corner {
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
	}
	.corner .rate {
		align-self: start;
		justify-self: end;
		margin-top: 0 !important;
		flex-direction: column;
		align-items: flex-end;
		gap: 0.1rem;
	}
	.corner .rate b {
		font-size: clamp(1.4rem, 8.5cqi, 2.5rem);
		min-width: 0;
	}
	/* a narrow header (tablets): tighter gaps and tracking, so the labels never reach the rate */
	@container (max-width: 18rem) {
		.row.corner {
			column-gap: var(--sp-2);
		}
		.corner .gauge {
			width: 3.25rem;
		}
		.corner .tag {
			letter-spacing: 0.05em;
			gap: 0.3rem;
		}
	}
	/* the speed-up: the hero's loudest element after the headline. A dark plate with a white-hot
	 * core and a heat bloom that fires with our bursts; the seam line runs dim steel into the
	 * typical pane and bright heat into ours. */
	.seamgain {
		grid-column: 2;
		grid-row: 1 / span 3;
		align-self: center;
		position: relative;
		z-index: 1;
		margin: 0;
		display: grid;
		place-items: center;
	}
	.seamgain::before,
	.seamgain::after {
		content: '';
		position: absolute;
		z-index: -1;
		top: 50%;
	}
	.seamgain::before {
		left: calc(-1 * var(--cg));
		right: 50%;
		height: 1px;
		background: linear-gradient(90deg, rgb(125 135 148 / 0.35), rgb(125 135 148 / 0.7));
	}
	.seamgain::after {
		left: 50%;
		right: calc(-1 * var(--cg));
		height: 3px;
		margin-top: -1px;
		border-radius: 3px;
		background: linear-gradient(90deg, var(--heat-3), var(--heat-5));
		box-shadow:
			0 0 8px var(--heat-4),
			0 0 22px rgb(255 122 26 / 0.8);
	}
	.pill {
		position: relative;
		isolation: isolate;
		display: grid;
		padding: 1rem 1.5rem 0.9rem;
		border-radius: 1.5rem;
		box-shadow:
			0 0 0 1px rgb(255 193 90 / 0.45),
			0 0 70px -4px rgb(255 122 26 / 0.75),
			0 24px 60px -24px rgb(226 64 28 / 0.9);
	}
	/* the halo around the plate (opacity only: it fires with the bursts) */
	.bloom {
		position: absolute;
		z-index: -2;
		inset: -45% -35%;
		border-radius: 50%;
		background: radial-gradient(closest-side, rgb(255 193 90 / 0.55), rgb(255 122 26 / 0.3) 45%, rgb(226 64 28 / 0.12) 70%, transparent);
		opacity: 0.6;
		pointer-events: none;
		will-change: opacity;
	}
	/* a turning heat edge (compositor only) around a near-black plate */
	.ring {
		position: absolute;
		inset: 0;
		z-index: -1;
		overflow: hidden;
		border-radius: inherit;
	}
	.ring::before {
		content: '';
		position: absolute;
		left: 50%;
		top: 50%;
		width: 200%;
		aspect-ratio: 1;
		translate: -50% -50%;
		background: conic-gradient(var(--heat-2), var(--heat-3) 10%, var(--heat-5) 17%, var(--heat-4) 24%, rgb(255 122 26 / 0.25) 40%, rgb(255 122 26 / 0.15) 75%, var(--heat-2));
		animation: turn 2.6s linear infinite paused;
		will-change: transform;
	}
	.run .ring::before {
		animation-play-state: running;
	}
	.ring::after {
		content: '';
		position: absolute;
		inset: 2px;
		border-radius: calc(1.5rem - 2px);
		background:
			radial-gradient(60% 55% at 50% 42%, rgb(255 243 214 / 0.16), rgb(255 122 26 / 0.12) 55%, transparent 80%),
			#060403;
	}
	.core {
		display: grid;
		justify-items: center;
		gap: 0.35rem;
		line-height: 1;
		will-change: transform;
	}
	/* the factor: twice the size of a pane rate, white-hot to heat, with its own glow */
	.pill .core :global(.speedup) {
		--rx-fs: clamp(3rem, 1.6rem + 3.6vw, 5.75rem);
		background: linear-gradient(180deg, #fff 8%, var(--heat-5) 32%, var(--heat-4) 58%, var(--heat-3) 82%, var(--heat-2));
		-webkit-background-clip: text;
		background-clip: text;
		filter: drop-shadow(0 0 6px rgb(255 243 214 / 0.55)) drop-shadow(0 0 22px rgb(255 122 26 / 0.7));
	}
	.fx {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		font-weight: 600;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: var(--heat-5);
		text-shadow: 0 0 10px rgb(255 122 26 / 0.8);
	}
	/* phones and small tablets: the panes stack; the badge sits between them */
	@media (max-width: 720px) {
		.panes.seam {
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: repeat(7, auto);
		}
		.seam .pane.cold {
			grid-column: 1;
			grid-row: 1 / span 3;
		}
		.seam .pane.hot {
			grid-column: 1;
			grid-row: 5 / span 3;
		}
		.seamgain {
			grid-column: 1;
			grid-row: 4;
			padding-block: 1.25rem;
		}
		/* stacked: the seam runs vertically, dim up into the typical pane, bright down into ours */
		.seamgain::before,
		.seamgain::after {
			left: 50%;
			right: auto;
			margin: 0;
		}
		.seamgain::before {
			top: 0;
			bottom: 50%;
			width: 1px;
			height: auto;
			background: linear-gradient(180deg, rgb(125 135 148 / 0.35), rgb(125 135 148 / 0.7));
		}
		.seamgain::after {
			top: 50%;
			bottom: 0;
			width: 3px;
			height: auto;
			margin-left: -1px;
			background: linear-gradient(180deg, var(--heat-3), var(--heat-5));
		}
	}
	/* a narrow header: the dial sits above the header text */
	@container (max-width: 14rem) {
		.row.dialed {
			grid-template-columns: minmax(0, 1fr);
			justify-items: start;
		}
		.gauge {
			width: 4.25rem;
		}
		.dialed .rate b {
			font-size: clamp(1.6rem, 15cqi, 3.2rem);
		}
	}
	@media (max-width: 520px) {
		.ph {
			padding: var(--sp-3);
		}
		.gain {
			flex-basis: 100%;
			margin-left: 0 !important;
			justify-items: start;
		}
		.win {
			height: var(--duel-win-sm, 13rem);
			padding-inline: var(--sp-3);
		}
		.feed p {
			font-size: 0.6875rem;
		}
		.ct {
			padding: var(--sp-2) var(--sp-3);
		}
	}
</style>
