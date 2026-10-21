<script lang="ts" module>
	export interface DuelLane {
		id: 'cold' | 'hot';
		/** "Bez Enigma LABZ" / "Z Enigma LABZ". */
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
	 * Two terminal panes, side by side, streaming the same answer nonstop: without Enigma LABZ (cold,
	 * steel) and with it (hot, a turning heat edge), at exactly the measured median t/s; the hot side
	 * emits in steps of the measured MTP tokens per step. Each pane follows its newest line and wraps
	 * from the end of the answer straight into the next copy, so the stream is endless; under it a
	 * counter of tokens written grows, ours at the measured ratio, with our live lead. The final CTA.
	 *
	 * The text is an example, the pace is measured. Every token is laid out from the first frame
	 * (two stacked copies per pane); writing only toggles classes, the window moves by transform.
	 * The loop runs only while on screen and not paused, and continues where it stopped. SSR, no JS
	 * and reduced motion: one static frame `T0` seconds in (ours has written as much more as it is
	 * faster), no loop.
	 */
	import type { Snippet } from 'svelte';
	import { onMount, untrack } from 'svelte';
	import Ratio from '$lib/cards/Ratio.svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFrame, reducedMotion } from './motion';

	let {
		lanes,
		gain,
		text,
		lang,
		labels,
		summary,
		caption
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
	let playing = $state(true);
	let onScreen = $state(false);
	let feeds: HTMLElement[] = $state([]);
	let counts: HTMLElement[] = $state([]);
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
	const rm = typeof window !== 'undefined' && reducedMotion();
	onMount(() => {
		spans = feeds.map((f) => Array.from(f.querySelectorAll<HTMLElement>('.tk')));
		lit = feeds.map((f) => f.querySelectorAll('.tk.on').length);
		shown = [...first];
		clock = T0;
		measure();
		seek(T0, true);
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
				clock += d;
				seek(clock, false, d);
			})
		);
	});
</script>

<figure class="duel" class:run={playing && onScreen && !rm} use:visible={(v) => (onScreen = v)}>
	<p class="sr-only">{summary}</p>
	<div class="panes" aria-hidden="true">
		{#each lanes as l, i (l.id)}
			{@const d = headOf(first[i])}
			<div class="pane {l.id}">
				{#if l.id === 'hot'}<span class="edge"></span>{/if}
				<div class="face">
					<header class="ph">
						<div class="info">
							<p class="tag"><span class="dot"></span>{l.tag}</p>
							<p class="who">{l.who}</p>
							<p class="rate"><b>{num(l.tps, lang)}</b><span>t/s</span></p>
							{#if l.id === 'hot'}<p class="gain"><Ratio value={gain} {lang} size="sm" /><span>{labels.faster}</span></p>{/if}
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
		/* the big rate scales with the header (not on .pane: containment breaks its subgrid) */
		container-type: inline-size;
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
