<script lang="ts">
	/**
	 * Jak to możliwe, as three visuals and almost no prose:
	 * (a) the stack: six layers between the model (top) and the graphics card (bottom) light up in
	 *     sequence as slabs, each with a mini icon and a short label; a token pulse then runs down
	 *     through them. Text only (no numbers).
	 * (b) layer 02 up close: one token's kernel launches as a timeline, upstream vs ours on the same
	 *     time scale (RTX 3090 × Qwen, HERO_RUN.kernels). Bars = kernels (work per launch = GPU ms ÷
	 *     launches), gaps = GPU waiting (gap ms ÷ launches). Our lane starts as upstream and merges
	 *     ~2.5 launches into one: the gaps visibly close while its counters run 1956 → 795 launches,
	 *     3,83 → 2,55 ms of gaps, 24,9 → 24,5 ms of GPU work. Zoomed into the first 40 upstream launches.
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
	const stackTl = new Autoplay(1.5, '0px 0px -20% 0px');
	const ICONS = [
		'M6 6h8v8H6zM8 3v3M12 3v3M8 14v3M12 14v3M3 8h3M3 12h3M14 8h3M14 12h3',
		'M3 7h5v6H3zM10 7h7v6h-7z',
		'M3 10h10M10 6l4 4-4 4M17 4v12',
		'M4 5l5 5-5 5M10 5l5 5-5 5',
		'M4 5h12v3H4zM4 9.5h12v3H4zM4 14h12v2H4z',
		'M5 3v14M10 3v14M15 3v14M3.5 7h3M8.5 12h3M13.5 6h3'
	];

	// ---- (b) kernel timeline ----
	const zoomTl = new Autoplay(2.2, '0px 0px -20% 0px');
	const f = $derived(easeInOutCubic(clamp01((zoomTl.p - 0.12) / 0.75)));
	const UP = K.up.v;
	const OURS = K.ours.v;
	const N = 40;
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
</script>

<section id="engine" class="engine heat-top" aria-labelledby="engine-title">
	<div class="inner">
		<h2 id="engine-title" class="statement">{c.title.replace('|', ' ')}</h2>

		<div class="grid">
			<!-- (a) the stack -->
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

			<div class="right">
				<!-- (b) layer 02 up close -->
				<figure class="zoom" use:zoomTl.view>
					<figcaption class="zh">
						<span class="zk">02</span>
						<span class="zt">{c.zoom}</span>
						<span class="zm"><ModelMark model={HERO_RUN.model} size="0.7em" /> {HERO_MODEL} · {HERO_CARD.name}</span>
						<SourceTip {lang} src={kSrc} note={c.zoomNote} />
						<Replay {lang} onclick={zoomTl.replay} disabled={zoomTl.playing} />
					</figcaption>
					{#each [0, 1] as lane (lane)}
						<div class="lane" class:ours={lane === 1}>
							<p class="ln">{lane ? c.ours : c.up}</p>
							<svg class="track" viewBox="0 0 1000 40" preserveAspectRatio="none" aria-hidden="true">
								{#each bars as b, i (i)}
									{#if lane === 0}
										<rect x={b.x0} y="6" width={b.w0} height="28" rx="1.5" />
									{:else}
										<rect x={lerp(b.x0, b.x1, f)} y="6" width={lerp(b.w0, b.w1, f) + (f > 0.98 ? 0.6 : 0)} height="28" rx="1.5" />
									{/if}
								{/each}
							</svg>
							<dl class="nums">
								<div class="n-main"><dt>{c.kernels}</dt><dd>{num(lane ? live.n : UP, lang, 0)}</dd></div>
								<div><dt>{c.gaps}</dt><dd>{num(lane ? live.gap : K.gapMs[0].v, lang, 2)}<small>&nbsp;ms</small></dd></div>
								<div><dt>{c.gpu}</dt><dd>{num(lane ? live.gpu : K.gpuMs[0].v, lang, 1)}<small>&nbsp;ms</small></dd></div>
							</dl>
						</div>
					{/each}
					<p class="sr-only">{c.up}: {UP} {c.kernels}, {c.gaps} {num(K.gapMs[0].v, lang, 2)} ms, {c.gpu} {num(K.gpuMs[0].v, lang, 1)} ms. {c.ours}: {OURS} {c.kernels}, {c.gaps} {num(K.gapMs[1].v, lang, 2)} ms, {c.gpu} {num(K.gpuMs[1].v, lang, 1)} ms.</p>
				</figure>

				<!-- (c) where the gain comes from -->
				<div class="split" class:in={zoomTl.p > 0.55}>
					<p class="sh">{c.split}</p>
					{#each rows as r, ri (r.card.id + r.run.model)}
						<div class="row" style="--d:{ri * 120}ms">
							<p class="rw">
								<ModelMark model={r.run.model} size="0.7em" />
								<b>{MODEL_STYLE[r.run.model].short}</b>
								<span>{r.card.short}</span>
							</p>
							<div class="bwrap">
								<div class="sbar" style="--len:{w(r.total)}">
									{#each r.segs as s (s.label)}
										<span class="seg" class:mine={s.ours} style="flex-grow:{w(s.v)}">
											<b class="speedup" class:speedup--down={s.v < 1} style="--rh:{heatOf(s.v)}">{fmtRatio(s.v, lang)}</b>
										</span>
									{/each}
								</div>
								<!-- what each segment is, right under its bar (never truncated inside a narrow segment) -->
								<p class="cap2">
									{#each r.segs as s, si (s.label)}{#if si > 0}<span class="x" aria-hidden="true">×</span>{/if}<span class="ck" class:mine={s.ours}>{s.label}</span>{/each}
								</p>
							</div>
							<SourceTip {lang} src={r.run.gain!.src} note={r.note} />
						</div>
					{/each}
				</div>
			</div>
		</div>
	</div>
</section>

<style>
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		display: grid;
		gap: clamp(2rem, 4vw, 3.5rem);
	}
	.statement {
		margin: 0;
		max-width: 20ch;
		font-family: var(--font-display);
		font-size: clamp(2.1rem, 0.8rem + 3vw, 4.2rem);
		font-weight: 820;
		font-stretch: 112%;
		line-height: 0.95;
		letter-spacing: -0.04em;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.4fr);
		gap: clamp(2rem, 5vw, 5rem);
		align-items: start;
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
	/* the token's path from the model down to the card; a pulse runs it once the stack is lit */
	.pulse {
		position: absolute;
		left: 50%;
		top: 1.6rem;
		bottom: 1.6rem;
		width: 1px;
		background: linear-gradient(var(--line-strong), var(--line-strong));
		overflow: hidden;
	}
	.pulse::after {
		content: '';
		position: absolute;
		left: -1px;
		width: 3px;
		height: 18%;
		background: linear-gradient(transparent, var(--text-hi), transparent);
		box-shadow: 0 0 10px var(--text-hi);
		transform: translate3d(0, -100%, 0);
		opacity: 0;
	}
	.pulse.run::after {
		opacity: 1;
		animation: pulse 2.6s cubic-bezier(0.5, 0, 0.5, 1) infinite;
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
		gap: 0.45rem;
		transform: rotateX(8deg) rotateY(-10deg);
		transform-style: preserve-3d;
	}
	.slab {
		position: relative;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		grid-template-areas: 'icon name key' 'icon sub key';
		align-items: center;
		column-gap: 0.9rem;
		padding: 0.7rem 1rem;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: linear-gradient(180deg, rgb(255 255 255 / 0.035), rgb(255 255 255 / 0.01)), var(--bg-1);
		box-shadow: 0 10px 24px -16px rgb(0 0 0 / 0.9);
		opacity: 0.25;
		transform: translate3d(-1.25rem, 0, 0);
		transition:
			opacity 0.35s var(--ease-out),
			transform 0.45s var(--ease-spring),
			border-color 0.6s;
	}
	.slab.in {
		opacity: 1;
		transform: none;
		animation: lit 0.9s var(--ease-out);
	}
	@keyframes lit {
		0% {
			border-color: var(--text-hi);
			box-shadow:
				0 0 0 1px rgb(237 234 227 / 0.5),
				0 0 28px rgb(237 234 227 / 0.25);
		}
	}
	.slab.focus.in {
		border-color: rgb(237 234 227 / 0.45);
	}
	.si {
		grid-area: icon;
		display: grid;
		place-items: center;
		width: 2.2rem;
		height: 2.2rem;
		border-radius: 8px;
		background: rgb(237 234 227 / 0.06);
		color: var(--text-hi);
	}
	.sn {
		grid-area: name;
		font-weight: 680;
		font-size: var(--fs-sm);
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

	/* ---- (b) zoom ---- */
	.right {
		display: grid;
		gap: clamp(1.5rem, 3vw, 2.25rem);
		min-width: 0;
	}
	.zoom {
		margin: 0;
		display: grid;
		gap: 1.1rem;
		padding: clamp(1.25rem, 2.5vw, 1.75rem);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
	}
	.zh {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.8rem;
	}
	.zk {
		padding: 0.1rem 0.45rem;
		border: 1px solid var(--text-hi);
		border-radius: 3px;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-hi);
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
	.lane {
		display: grid;
		grid-template-columns: 6.5rem minmax(0, 1fr);
		grid-template-areas: 'ln track' '. nums';
		align-items: center;
		column-gap: 1rem;
		row-gap: 0.4rem;
	}
	.ln {
		grid-area: ln;
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.ours .ln {
		color: var(--text-hi);
		font-weight: 650;
	}
	/* the waiting shows through as a dotted floor (dotted = overhead); kernels sit on it */
	.track {
		grid-area: track;
		width: 100%;
		height: 2.6rem;
		background: radial-gradient(circle, rgb(125 135 148 / 0.55) 1px, transparent 1.4px) 0 50% / 6px 6px;
		border-radius: 4px;
	}
	.track rect {
		fill: var(--before);
	}
	.ours .track rect {
		fill: var(--text-hi);
	}
	.nums {
		grid-area: nums;
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.2rem 1.6rem;
		font-variant-numeric: tabular-nums;
	}
	.nums div {
		display: flex;
		align-items: baseline;
		gap: 0.45rem;
	}
	.nums dt {
		order: 2;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.nums dd {
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-md);
		color: var(--text);
	}
	.n-main dd {
		font-size: clamp(1.4rem, 1rem + 1vw, 1.9rem);
		font-weight: 500;
		letter-spacing: -0.04em;
		color: var(--before);
	}
	.ours dd {
		color: var(--text-hi);
	}
	.ours .n-main dd {
		color: var(--text-hi);
	}
	.nums small {
		font-size: 0.7em;
		color: var(--text-mute);
	}

	/* ---- (c) split bars ---- */
	.split {
		display: grid;
		gap: 0.9rem;
	}
	.sh {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.row {
		display: grid;
		grid-template-columns: 9.5rem minmax(0, 1fr) auto;
		align-items: center;
		gap: 1rem;
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
	.bwrap {
		display: grid;
		gap: 0.35rem;
		min-width: 0;
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
	.sbar {
		display: flex;
		flex: none;
		gap: 3px;
		width: calc(var(--len) * 100%);
		transform-origin: 0 50%;
		transform: scaleX(0);
		transition: transform 0.8s var(--ease-out) var(--d);
	}
	.split.in .sbar {
		transform: none;
	}
	.seg {
		flex-basis: 0;
		min-width: 0;
		display: flex;
		align-items: baseline;
		gap: 0.45rem;
		padding: 0.45rem 0.6rem;
		border-radius: 5px;
		background: rgb(125 135 148 / 0.18);
		border: 1px solid rgb(125 135 148 / 0.4);
		overflow: hidden;
		white-space: nowrap;
	}
	.seg.mine {
		background: linear-gradient(90deg, rgb(226 64 28 / 0.25), rgb(255 122 26 / 0.3));
		border-color: rgb(255 122 26 / 0.6);
		box-shadow: 0 0 16px -4px rgb(255 122 26 / 0.45);
	}
	.seg b {
		font-size: var(--fs-md);
	}
	.seg:not(.mine) b {
		background: none;
		color: var(--text-hi);
		-webkit-text-fill-color: currentColor;
	}
	@media (max-width: 1000px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.slabs {
			transform: none;
		}
	}
	@media (max-width: 640px) {
		.lane {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'ln' 'track' 'nums';
		}
		.row {
			grid-template-columns: minmax(0, 1fr) auto;
			grid-template-areas: 'rw src' 'bar bar';
		}
		.rw {
			grid-area: rw;
		}
		.row :global(.src-btn),
		.row > :global(:last-child) {
			grid-area: src;
		}
		.bwrap {
			grid-area: bar;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.slab,
		.sbar {
			transition: none;
		}
		.slab.in,
		.pulse.run::after {
			animation: none;
		}
	}
</style>
