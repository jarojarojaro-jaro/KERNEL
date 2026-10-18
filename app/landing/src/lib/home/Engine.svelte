<script lang="ts">
	/**
	 * Jak to możliwe: the page's second big scene, full-bleed and cinematic, almost no prose:
	 * (a) the stack: six layers between the model (top) and the graphics card (bottom) light up in
	 *     sequence as slabs, each with a mini icon and a short label; a token pulse then runs down
	 *     through them. Text only (no numbers).
	 * (b) layer 02 up close: one token's kernel launches as a timeline, upstream vs ours on the same
	 *     time scale (RTX 3090 × Qwen, HERO_RUN.kernels). Bars = kernels (work per launch = GPU ms ÷
	 *     launches), gaps = GPU waiting (gap ms ÷ launches). Our lane starts as upstream and merges
	 *     ~2.5 launches into one: the gaps visibly close while its counters run 1956 → 795 launches,
	 *     3,83 → 2,55 ms of gaps, 24,9 → 24,5 ms of GPU work. Zoomed into the first 72 upstream launches, drawn as a
	 *     full-width band; giant live counters above it.
	 * (c) where the gain comes from, as split bars (log scale, so segments multiply): 3090 Qwen =
	 *     upstream MTP flags × our engine; LFM2.5 (no speculation) = our engine only. From run.gain.
	 * Auto-played on entering the viewport (replay button); reduced motion shows the final state.
	 */
	import { heatOf } from '$lib/cards/explorer';
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01, easeInOutCubic } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { findCard, MODEL_INFO, type CardView, type RunView } from '$lib/data/measurements';
	import { localizeDecimals } from '$lib/format';
	import { num, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { copy } from '$lib/site/copy';
	import { fmtRatio, HERO_CARD, HERO_KERNELS, HERO_MODEL, HERO_RUN } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].engine);
	const K = HERO_KERNELS;

	// ---- (a) stack ----
	const stackTl = new Autoplay(1.8, '0px 0px -20% 0px');
	const ICONS = [
		'M6 6h8v8H6zM8 3v3M12 3v3M8 14v3M12 14v3M3 8h3M3 12h3M14 8h3M14 12h3',
		'M3 7h5v6H3zM10 7h7v6h-7z',
		'M3 10h10M10 6l4 4-4 4M17 4v12',
		'M4 5l5 5-5 5M10 5l5 5-5 5',
		'M4 5h12v3H4zM4 9.5h12v3H4zM4 14h12v2H4z',
		'M5 3v14M10 3v14M15 3v14M3.5 7h3M8.5 12h3M13.5 6h3'
	];

	// ---- (b) kernel timeline ----
	const zoomTl = new Autoplay(2.6, '0px 0px -15% 0px');
	const f = $derived(easeInOutCubic(clamp01((zoomTl.p - 0.12) / 0.75)));
	const UP = K.up.v;
	const OURS = K.ours.v;
	const N = 72;
	const G = Math.round((N * OURS) / UP);
	const wU = K.gpuMs[0].v / UP;
	const gU = K.gapMs[0].v / UP;
	const wO = K.gpuMs[1].v / OURS;
	const gO = K.gapMs[1].v / OURS;
	const T = N * (wU + gU);
	const sx = (ms: number) => (ms / T) * 1000;
	/** Per upstream launch i: its own rect and its share of our merged kernel (group g). */
	const bars = Array.from({ length: N }, (_, i) => {
		const g = Math.floor((i * G) / N);
		const first = Math.ceil((g * N) / G);
		const size = Math.ceil(((g + 1) * N) / G) - first;
		const k = i - first;
		return { x0: sx(i * (wU + gU)), w0: sx(wU), x1: sx(g * (wO + gO) + (k * wO) / size), w1: sx(wO / size) };
	});
	const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
	const live = $derived({
		n: Math.round(lerp(UP, OURS, f)),
		gap: lerp(K.gapMs[0].v, K.gapMs[1].v, f),
		gpu: lerp(K.gpuMs[0].v, K.gpuMs[1].v, f)
	});
	const kSrc = [K.up.src, K.ours.src, K.gapMs[0].src, K.gpuMs[0].src].filter(Boolean);

	// ---- (c) where the gain comes from ----
	type Seg = { label: string; v: number; ours: boolean };
	const lfm = (id: string): { card: CardView; run: RunView } => {
		const card = findCard(id)!;
		return { card, run: card.runs.find((r) => r.model === 'lfm25')! };
	};
	const rows = $derived.by(() => {
		const q = { card: HERO_CARD, run: HERO_RUN };
		const l1 = lfm('rtx-3090');
		const l2 = lfm('rtx-5060-ti-16');
		const mk = (x: { card: CardView; run: RunView }, segs: Seg[]) => ({
			...x,
			segs,
			total: segs.reduce((a, s) => a * s.v, 1),
			note: `${x.card.name} · ${MODEL_INFO[x.run.model].name}: ${(x.run.gainText?.[lang] ?? x.run.gain!.text).map((t) => localizeDecimals(t.replaceAll('\u0060', ''), lang)).join(' · ')}`
		});
		return [
			mk(q, [
				{ label: c.flags, v: q.run.gain!.flags!.v, ours: false },
				{ label: c.mine, v: q.run.gain!.engine!.v, ours: true }
			]),
			mk(l1, [{ label: c.allOurs, v: l1.run.gain!.engine!.v, ours: true }]),
			mk(l2, [{ label: c.allOurs, v: l2.run.gain!.engine!.v, ours: true }])
		];
	});
	const maxTotal = $derived(Math.max(...rows.map((r) => r.total)));
	const w = (v: number) => Math.log(v) / Math.log(maxTotal);
	/** Title as two lines: the claim (bone) and the payoff (heat). */
	const titleParts = $derived(c.title.split('|'));
</script>

<section id="engine" class="engine heat-top" aria-labelledby="engine-title">
	<div class="atmo" aria-hidden="true"></div>
	<div class="inner">
		<h2 id="engine-title" class="statement"><span class="t1">{titleParts[0]}</span> <span class="t2">{titleParts[1] ?? ''}</span></h2>

		<div class="grid">
			<!-- (a) the stack: model → card, lit layer by layer -->
			<div class="stack" use:stackTl.view>
				<p class="cap cap--model"><span class="ci" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="M10 2l7 4v8l-7 4-7-4V6zM3 6l7 4 7-4M10 10v8" /></svg></span>{c.model}</p>
				<div class="pulse" class:run={stackTl.p >= 1} aria-hidden="true"></div>
				<ol class="slabs">
					{#each c.layers as [name, sub], i (name)}
						<li class="slab" class:in={stackTl.p >= (i + 1) / 7} class:focus={i === 1} style="--i:{i}">
							<span class="si" aria-hidden="true"><svg viewBox="0 0 20 20"><path d={ICONS[i]} /></svg></span>
							<span class="sn">{name}</span>
							<span class="ss">{sub}</span>
							<span class="sk" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
						</li>
					{/each}
				</ol>
				<p class="cap cap--card"><span class="ci" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="M2 6h16v9H2zM5 15v2M8 15v2M11 15v2M14 15v2M6 9h4v3H6z" /></svg></span>{c.card}</p>
			</div>

			<!-- (b) layer 02 up close: giant live counters -->
			<div class="close" use:zoomTl.view>
				<p class="zh">
					<span class="zk">02</span>
					<span class="zt">{c.zoom}</span>
					<span class="zm"><ModelMark model={HERO_RUN.model} size="0.7em" /> {HERO_MODEL} · {HERO_CARD.name}</span>
					<SourceTip {lang} src={kSrc} note={c.zoomNote} />
					<Replay {lang} onclick={zoomTl.replay} disabled={zoomTl.playing} />
				</p>
				<p class="giant" aria-hidden="true">
					<span class="g-up">{num(UP, lang, 0)}</span>
					<span class="g-ar">→</span>
					<span class="g-ours">{num(live.n, lang, 0)}</span>
				</p>
				<p class="g-cap">{c.kernels}</p>
				<dl class="pair">
					<div><dt>{c.gaps}</dt><dd><span class="pu">{num(K.gapMs[0].v, lang, 2)}</span> → <b>{num(live.gap, lang, 2)}</b>&nbsp;ms</dd></div>
					<div><dt>{c.gpu}</dt><dd><span class="pu">{num(K.gpuMs[0].v, lang, 1)}</span> → <b>{num(live.gpu, lang, 1)}</b>&nbsp;ms</dd></div>
				</dl>
				<p class="sr-only">{c.up}: {UP} {c.kernels}, {c.gaps} {num(K.gapMs[0].v, lang, 2)} ms, {c.gpu} {num(K.gpuMs[0].v, lang, 1)} ms. {c.ours}: {OURS} {c.kernels}, {c.gaps} {num(K.gapMs[1].v, lang, 2)} ms, {c.gpu} {num(K.gpuMs[1].v, lang, 1)} ms.</p>
			</div>
		</div>
	</div>

	<!-- the kernel timeline as a full-bleed band: bars = kernels, the dotted floor = GPU waiting -->
	<div class="band" aria-hidden="true">
		{#each [0, 1] as lane (lane)}
			<div class="lane" class:ours={lane === 1}>
				<span class="ln">{lane ? c.ours : c.up}</span>
				<svg class="track" viewBox="0 0 1000 40" preserveAspectRatio="none">
					{#each bars as b, i (i)}
						{#if lane === 0}
							<rect x={b.x0} y="4" width={b.w0} height="32" rx="1" />
						{:else}
							<rect x={lerp(b.x0, b.x1, f)} y="4" width={lerp(b.w0, b.w1, f) + (f > 0.98 ? 0.6 : 0)} height="32" rx="1" />
						{/if}
					{/each}
				</svg>
			</div>
		{/each}
	</div>

	<div class="inner">
		<!-- (c) where the gain comes from, compact -->
		<div class="split" class:in={zoomTl.p > 0.55}>
			<p class="sh">{c.split} <SourceTip {lang} src={rows.map((r) => r.run.gain!.src)} note={rows.map((r) => r.note).join(' — ')} /></p>
			<div class="rows">
				{#each rows as r, ri (r.card.id + r.run.model)}
					<div class="row" style="--d:{ri * 120}ms">
						<p class="rw">
							<ModelMark model={r.run.model} size="0.7em" />
							<b>{MODEL_STYLE[r.run.model].short}</b>
							<span>{r.card.short}</span>
						</p>
						<div class="sbar" style="--len:{w(r.total)}">
							{#each r.segs as s (s.label)}
								<span class="seg" class:mine={s.ours} style="flex-grow:{w(s.v)}">
									<b class="speedup" class:speedup--down={s.v < 1} style="--rh:{heatOf(s.v)}">{fmtRatio(s.v, lang)}</b>
								</span>
							{/each}
						</div>
						<p class="cap2">
							{#each r.segs as s, si (s.label)}{#if si > 0}<span class="x" aria-hidden="true">×</span>{/if}<span class="ck" class:mine={s.ours}>{s.label}</span>{/each}
						</p>
					</div>
				{/each}
			</div>
		</div>
	</div>
</section>

<style>
	.engine {
		position: relative;
		isolation: isolate;
		overflow: clip;
		padding-block: clamp(4rem, 3rem + 4vw, 8rem);
		background: #070606;
	}
	/* the scene's atmosphere: a heat bloom from below and a faint measuring grid */
	.atmo {
		position: absolute;
		inset: 0;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(55% 45% at 70% 62%, rgb(255 122 26 / 0.16), transparent 70%),
			radial-gradient(45% 40% at 15% 30%, rgb(226 64 28 / 0.1), transparent 70%),
			linear-gradient(rgb(237 234 227 / 0.035) 1px, transparent 1px) 0 0 / 100% 4rem,
			linear-gradient(90deg, rgb(237 234 227 / 0.035) 1px, transparent 1px) 0 0 / 4rem 100%;
		mask-image: linear-gradient(transparent, #000 15%, #000 85%, transparent);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(2rem, 4vw, 3.5rem);
	}
	.statement {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.6rem, 1rem + 5.4vw, 7rem);
		font-weight: 820;
		line-height: 0.92;
		letter-spacing: -0.045em;
		text-wrap: balance;
	}
	.t1 {
		display: block;
		color: var(--text-hi);
	}
	.t2 {
		display: block;
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 35%, var(--heat-4) 70%, var(--heat-5));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 0.3em rgb(255 122 26 / 0.3));
	}
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.25fr);
		gap: clamp(2rem, 5vw, 5rem);
		align-items: center;
	}

	/* ---- (a) stack ---- */
	.stack {
		position: relative;
		display: grid;
		gap: 0.6rem;
		perspective: 1400px;
	}
	.cap {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text);
	}
	.cap--card {
		color: var(--heat-4);
	}
	.ci svg,
	.si svg {
		width: 1.15rem;
		height: 1.15rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.4;
		stroke-linejoin: round;
		stroke-linecap: round;
	}
	/* the token's path from the model down to the card: a heat filament, a spark runs it */
	.pulse {
		position: absolute;
		left: 50%;
		top: 1.6rem;
		bottom: 1.6rem;
		width: 2px;
		margin-left: -1px;
		background: linear-gradient(var(--heat-2), var(--heat-3), var(--heat-4));
		box-shadow: 0 0 10px rgb(255 122 26 / 0.7);
		overflow: hidden;
	}
	.pulse::after {
		content: '';
		position: absolute;
		left: -1px;
		width: 4px;
		height: 18%;
		background: linear-gradient(transparent, var(--heat-5), transparent);
		box-shadow: 0 0 12px var(--heat-5);
		transform: translate3d(0, -100%, 0);
	}
	@media (prefers-reduced-motion: no-preference) {
		.pulse.run::after {
			animation: pulse 2.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
		}
	}
	@keyframes pulse {
		to {
			transform: translate3d(0, 650%, 0);
		}
	}
	.slabs {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.5rem;
	}
	.slab {
		position: relative;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		grid-template-areas: 'icon name key' 'icon sub key';
		align-items: center;
		column-gap: 1rem;
		padding: 0.85rem 1.1rem;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: linear-gradient(180deg, rgb(255 255 255 / 0.04), rgb(255 255 255 / 0.01)), var(--bg-1);
		box-shadow: 0 12px 26px -16px rgb(0 0 0 / 0.9);
		filter: brightness(0.55);
		transition:
			transform 0.45s var(--ease-spring),
			filter 0.4s,
			border-color 0.6s;
	}
	.slab.in {
		filter: none;
		border-color: rgb(255 122 26 / 0.3);
		animation: lit 0.9s var(--ease-out);
	}
	@keyframes lit {
		0% {
			border-color: var(--heat-4);
			box-shadow:
				0 0 0 1px rgb(255 193 90 / 0.6),
				0 0 32px rgb(255 122 26 / 0.5);
		}
	}
	.slab.focus.in {
		border-color: var(--heat-3);
		background:
			linear-gradient(90deg, rgb(255 122 26 / 0.18), transparent 70%),
			var(--bg-1);
		box-shadow:
			0 0 0 1px rgb(255 122 26 / 0.4),
			0 0 40px -6px rgb(255 122 26 / 0.75);
	}
	.si {
		grid-area: icon;
		display: grid;
		place-items: center;
		width: 2.4rem;
		height: 2.4rem;
		border-radius: 8px;
		background: rgb(255 122 26 / 0.08);
		color: var(--heat-4);
	}
	.sn {
		grid-area: name;
		font-weight: 700;
		font-size: var(--fs-md);
		color: var(--text-hi);
		line-height: 1.2;
	}
	.ss {
		grid-area: sub;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.04em;
	}
	.sk {
		grid-area: key;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.slab.focus .sk {
		color: var(--heat-4);
	}

	/* ---- (b) close-up counters ---- */
	.close {
		display: grid;
		gap: 0.6rem;
		min-width: 0;
	}
	.zh {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.8rem;
	}
	.zk {
		padding: 0.1rem 0.45rem;
		border: 1px solid var(--heat-3);
		border-radius: 3px;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--heat-4);
	}
	.zt {
		font-weight: 700;
		color: var(--text-hi);
	}
	.zm {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		margin-right: auto;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.giant {
		margin: 0.4rem 0 0;
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0 0.25em;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(3.4rem, 1.5rem + 6vw, 8.5rem);
		font-weight: 800;
		line-height: 0.9;
		letter-spacing: -0.05em;
	}
	.g-up {
		color: var(--before);
	}
	.g-ar {
		font-size: 0.45em;
		color: var(--text-mute);
	}
	.g-ours {
		color: var(--heat-5);
		filter: drop-shadow(0 0 20px rgb(255 122 26 / 0.55));
	}
	.g-cap {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text);
	}
	.pair {
		margin: 0.8rem 0 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.6rem 2.5rem;
	}
	.pair div {
		display: grid;
		gap: 0.2rem;
	}
	.pair dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.pair dd {
		margin: 0;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums;
		font-size: clamp(1.4rem, 1rem + 1vw, 2rem);
		font-weight: 700;
		color: var(--text);
	}
	.pu {
		color: var(--before);
	}
	.pair b {
		color: var(--heat-4);
	}

	/* ---- the full-bleed band ---- */
	.band {
		margin-block: clamp(2.5rem, 5vw, 4.5rem);
		display: grid;
		gap: 0.9rem;
		padding-block: 1.2rem;
		border-block: 1px solid rgb(255 122 26 / 0.25);
		background: linear-gradient(90deg, rgb(255 122 26 / 0.02), rgb(255 122 26 / 0.07) 50%, rgb(255 122 26 / 0.02));
	}
	.lane {
		position: relative;
	}
	.ln {
		position: absolute;
		left: max(var(--gutter), calc((100% - 90rem) / 2));
		top: 50%;
		transform: translateY(-50%);
		z-index: 1;
		padding: 0.2rem 0.6rem;
		border-radius: 4px;
		background: rgb(7 6 6 / 0.85);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text);
	}
	.ours .ln {
		color: var(--heat-4);
	}
	.track {
		display: block;
		width: 100%;
		height: clamp(2.8rem, 2rem + 2vw, 4.4rem);
		background: radial-gradient(circle, rgb(125 135 148 / 0.5) 1px, transparent 1.4px) 0 50% / 7px 7px;
	}
	.track rect {
		fill: rgb(125 135 148 / 0.75);
	}
	.ours .track rect {
		fill: var(--heat-4);
	}
	.ours .track {
		filter: drop-shadow(0 0 8px rgb(255 122 26 / 0.5));
	}

	/* ---- (c) split, compact ---- */
	.split {
		display: grid;
		gap: 0.9rem;
	}
	.sh {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.rows {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: clamp(1rem, 2.5vw, 2rem);
	}
	.row {
		display: grid;
		gap: 0.45rem;
		align-content: start;
	}
	.rw {
		display: flex;
		align-items: baseline;
		gap: 0.45rem;
		white-space: nowrap;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.rw b {
		color: var(--text-hi);
		font-weight: 650;
	}
	.sbar {
		display: flex;
		gap: 3px;
		width: calc(var(--len) * 100%);
		transform-origin: 0 50%;
	}
	@media (prefers-reduced-motion: no-preference) {
		.split.in .sbar {
			animation: bar-in 0.8s var(--ease-out) var(--d) backwards;
		}
	}
	@keyframes bar-in {
		from {
			transform: scaleX(0);
		}
	}
	.seg {
		flex-basis: 0;
		min-width: 0;
		display: flex;
		align-items: baseline;
		padding: 0.4rem 0.6rem;
		border-radius: 5px;
		background: rgb(125 135 148 / 0.18);
		border: 1px solid rgb(125 135 148 / 0.4);
		overflow: hidden;
		white-space: nowrap;
	}
	.seg.mine {
		background: var(--heat-ramp-hot);
		border-color: rgb(255 243 214 / 0.5);
		box-shadow: 0 0 22px -4px rgb(255 122 26 / 0.7);
	}
	.seg b {
		font-size: var(--fs-md);
	}
	.seg.mine b {
		background: none;
		color: #1a0b03;
		-webkit-text-fill-color: currentColor;
		filter: none;
	}
	.seg:not(.mine) b {
		background: none;
		color: var(--text-hi);
		-webkit-text-fill-color: currentColor;
	}
	.cap2 {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.2rem 0.5rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.ck {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
	}
	.ck::before {
		content: '';
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 2px;
		background: rgb(125 135 148 / 0.6);
	}
	.ck.mine {
		color: var(--heat-4);
	}
	.ck.mine::before {
		background: var(--heat-3);
	}
	.cap2 .x {
		color: var(--text-mute);
	}
	@media (max-width: 1000px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.slabs {
			transform: none;
		}
		.rows {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 640px) {
		.ln {
			top: auto;
			bottom: calc(100% - 0.2rem);
			transform: none;
		}
		.lane {
			padding-top: 1.1rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.slab {
			transition: none;
		}
		.slab.in {
			animation: none;
		}
	}
</style>
