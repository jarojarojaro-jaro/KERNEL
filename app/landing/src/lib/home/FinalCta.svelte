<script lang="ts">
	/**
	 * Final CTA: the closing statement is a token stream, side by side, that never stops. The same
	 * answer flows in two terminal panes: without Podkręt (the typical app, a0) and with it (our
	 * engine, a2), RTX 3090 × Qwen3.8-27B, at exactly the measured median t/s; our side emits in
	 * steps of the measured MTP tokens per step. Each pane follows its newest line and wraps from the
	 * end of the answer straight into the next copy, so the stream is endless; under it a counter
	 * of tokens written grows, ours twice as fast. Not the hero race: no dials, no restarts.
	 *
	 * The text is an example, the pace is measured. Every token is laid out from the first frame
	 * (two stacked copies per pane); writing only toggles classes, the window moves by transform.
	 * The loop runs only while on screen and not paused. SSR, no JS and reduced motion: one static
	 * frame `T0` seconds in (ours has written twice as much), no loop.
	 */
	import { onMount, untrack } from 'svelte';
	import { magnetic, visible } from '$lib/fx/actions';
	import { onFrame, reducedMotion } from '$lib/fx/motion';
	import Ratio from '$lib/cards/Ratio.svelte';
	import { variantLabel } from '$lib/data/measurements';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { cardsHref, href, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, HERO_CARD, HERO_GAIN, HERO_MODEL, HERO_RUN, HERO_V } from './data';
	import Duo from './Duo.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].final);
	const cold = HERO_V.a0.decode!;
	const hot = HERO_V.a2.decode!;
	const gain = HERO_GAIN.total?.v ?? hot.v / cold.v;
	const lanes = [
		{ id: 'cold', key: 'a0' as const, tps: cold.v, burst: HERO_V.a0.tokStep?.v ?? 1 },
		{ id: 'hot', key: 'a2' as const, tps: hot.v, burst: HERO_V.a2.tokStep?.v ?? 1 }
	];

	/** The answer as token-sized pieces (count ≈ words × TOK_PER_WORD, as in the hero race). */
	const pieces = $derived.by(() => {
		const words = c.text.split(/\s+/).filter(Boolean);
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

	/** Tokens written after `t` seconds: whole MTP steps at the measured pace (mean = measured t/s). */
	const written = (l: (typeof lanes)[number], t: number) => Math.floor(Math.floor((l.tps * t) / l.burst) * l.burst);
	/** Lit tokens in the two stacked copies: the first pass fills copy 1, then the head cycles in copy 2. */
	const headOf = (pos: number) => (pos < 2 * N ? pos : N + ((pos - N) % N));
	/** The static frame: ours is 90% through the answer, the typical app about halfway. */
	const T0 = $derived((0.9 * N) / hot.v);
	const first = $derived(lanes.map((l) => written(l, T0)));

	const vars = $derived({ card: HERO_CARD.name, model: HERO_MODEL, quant: HERO_RUN.quant, a0: num(cold.v, lang), a2: num(hot.v, lang) });

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

	const rm = typeof window !== 'undefined' && reducedMotion();
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

<section class="final heat-top" aria-labelledby="final-title">
	<div class="heat" aria-hidden="true"></div>
	<div class="inner">
		<div class="copy">
			<Duo text={c.title} id="final-title" burn />
			<p class="lede">{c.lede}</p>
		</div>
		<figure class="duel" class:run={playing && onScreen && !rm} use:visible={(v) => (onScreen = v)}>
			<p class="sr-only">{fill(c.summary, vars)}</p>
			<div class="panes" aria-hidden="true">
				{#each lanes as l, i (l.id)}
					{@const d = headOf(first[i])}
					<div class="pane {l.id}">
						{#if l.id === 'hot'}<span class="edge"></span>{/if}
						<div class="face">
							<header class="ph">
								<p class="tag"><span class="dot"></span>{l.id === 'hot' ? c.with : c.without}</p>
								<p class="who">{variantLabel(HERO_RUN, l.key)[lang]}</p>
								<p class="rate"><b>{num(l.tps, lang)}</b><span>t/s</span></p>
								{#if l.id === 'hot'}<p class="gain"><Ratio value={gain} {lang} size="sm" /><span>{c.faster}</span></p>{/if}
							</header>
							<div class="win">
								<div class="feed" bind:this={feeds[i]}>
									{#each [0, 1] as k (k)}
										<p>
											{#each pieces as p, j (j)}<span class="tk" class:on={k * N + j < d} class:hd={k * N + j === d - 1}>{p}</span>{/each}
										</p>
									{/each}
								</div>
							</div>
							<p class="ct">
								<b bind:this={counts[i]}>{num(first[i], lang, 0)}</b> {c.tokens}
								{#if l.id === 'hot'}<span class="ahead" bind:this={aheadEl}>+{num(first[1] - first[0], lang, 0)}</span>{/if}
							</p>
						</div>
					</div>
				{/each}
			</div>
			<figcaption class="cap">
				<span>{HERO_CARD.name} · {HERO_MODEL} {HERO_RUN.quant}</span>
				<span class="note">{c.note}</span>
				<button type="button" class="pp" aria-pressed={!playing} aria-label={playing ? c.pause : c.resume} title={playing ? c.pause : c.resume} onclick={() => (playing = !playing)}>
					{#if playing}<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.5" y="2" width="2.4" height="8" rx="0.6" /><rect x="7.1" y="2" width="2.4" height="8" rx="0.6" /></svg>
					{:else}<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 2.2v7.6L10 6z" /></svg>{/if}
				</button>
			</figcaption>
		</figure>
		<div class="ctas">
			<a class="cta cta--bone" href={cardsHref(lang)} use:magnetic>{c.cards} <span class="arrow" aria-hidden="true">→</span></a>
			<a class="cta cta--line" href={href(lang, '/methodology')} use:magnetic>{c.method}</a>
		</div>
	</div>
</section>

<style>
	.final {
		position: relative;
		overflow: clip;
		padding-block: clamp(4rem, 3rem + 4vw, 7rem);
		background: var(--bg-0);
		isolation: isolate;
	}
	.heat {
		position: absolute;
		inset: auto -20% -40% -20%;
		height: 100%;
		z-index: -1;
		background:
			radial-gradient(35% 45% at 72% 85%, rgb(255 122 26 / 0.3), transparent 70%),
			radial-gradient(60% 60% at 70% 100%, rgb(226 64 28 / 0.42), rgb(122 46 31 / 0.15) 50%, transparent 75%);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
		grid-template-areas:
			'copy duel'
			'ctas duel';
		grid-template-rows: auto 1fr;
		gap: var(--sp-8) clamp(2rem, 5vw, 5rem);
		align-items: start;
	}
	.copy {
		grid-area: copy;
		align-self: end;
		display: grid;
		gap: var(--sp-6);
	}
	.ctas {
		grid-area: ctas;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
	}
	.duel {
		grid-area: duel;
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
		gap: 0 clamp(0.6rem, 1.5vw, 1.25rem);
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
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: end;
		align-content: start;
		gap: 0.2rem var(--sp-3);
		padding: var(--sp-4) var(--sp-4) var(--sp-3);
		border-bottom: 1px solid rgb(255 255 255 / 0.07);
	}
	.ph p {
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
		grid-column: 1 / -1;
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
		grid-column: 1 / -1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.rate {
		display: flex;
		align-items: baseline;
		gap: 0.35rem;
		margin-top: var(--sp-2) !important;
	}
	.rate b {
		font-family: var(--font-display);
		font-size: clamp(2rem, 1.2rem + 2.6vw, 3.6rem);
		font-weight: 850;
		font-stretch: 120%;
		letter-spacing: -0.045em;
		line-height: 0.9;
		font-variant-numeric: tabular-nums lining-nums;
		color: var(--before);
	}
	.hot .rate b {
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 18px rgb(255 122 26 / 0.5));
		padding-block: 0.04em 0.1em;
	}
	.rate span {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.gain {
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
		height: 12rem;
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
	.note::before {
		content: '· ';
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
		transition: border-color var(--dur-2), color var(--dur-2);
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

	@media (max-width: 900px) {
		.inner {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'copy' 'duel' 'ctas';
			grid-template-rows: none;
		}
	}
	@media (max-width: 520px) {
		.ph {
			grid-template-columns: minmax(0, 1fr);
			padding: var(--sp-3);
		}
		.gain {
			justify-items: start;
		}
		.win {
			height: 13rem;
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
