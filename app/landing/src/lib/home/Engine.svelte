<script lang="ts">
	/**
	 * Jak to możliwe: one token on the RTX 3090 × Qwen run, as two dot grids side by side with the
	 * same dot size: upstream's kernel launches (kernels.up) on the left, ours (kernels.ours) on the
	 * right, so the density drop reads in one frame. Both counts are printed statically above the
	 * grids (no rolling counter to catch mid-roll). Once the scene is in view (auto-play, replay
	 * button; reduced motion: final state), groups of left dots
	 * (~2.5 launches each) fly left → right and fuse into one bone dot of the right grid; the left
	 * grid stays as a dim steel reference. Canvas 2D, DPR ≤ 1.5, redrawn only while the timeline runs.
	 * Below: only the gaps between kernels per token (the waiting we remove) and the honest note on
	 * where the 3090 gain comes from. Kernels are not speed, so no heat colour here.
	 */
	import { onMount } from 'svelte';
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import Replay from '$lib/fx/Replay.svelte';
	import { clamp01, easeInOutCubic, reducedMotion } from '$lib/fx/motion';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { localizeDecimals } from '$lib/format';
	import { findCard, MODEL_INFO } from '$lib/data/measurements';
	import { num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import Rich from './Rich.svelte';
	import { fill, fmtRatio, HERO_CARD, HERO_GAIN, HERO_KERNELS, HERO_MODEL, HERO_RUN } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].engine);
	const K = HERO_KERNELS;
	const UP = K.up.v;
	const OURS = K.ours.v;

	const tl = new Autoplay(3.4);
	const f = $derived(easeInOutCubic(clamp01(tl.p)));

	let canvas: HTMLCanvasElement | undefined = $state();
	let box: HTMLDivElement | undefined = $state();
	let draw: ((f: number) => void) | null = null;
	let raf = 0;

	$effect(() => {
		const v = f;
		if (!draw) return;
		cancelAnimationFrame(raf);
		raf = requestAnimationFrame(() => draw?.(v));
	});

	onMount(() => {
		if (!canvas || !box) return;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;
		type P = { x0: number; y0: number; x1: number; y1: number; lead: boolean; delay: number };
		let parts: P[] = [];
		let s = 2;
		let W = 0;
		let H = 0;
		const dpr = Math.min(1.5, devicePixelRatio || 1);
		const STEEL = 'rgb(125 135 148)';
		const BONE = 'rgb(237 234 227)';

		/** Grid that fits n cells into w×h, returns cell size and columns. */
		const grid = (n: number, w: number, h: number) => {
			const cell = Math.sqrt((w * h) / n);
			let cols = Math.max(1, Math.floor(w / cell));
			while (Math.ceil(n / cols) * (w / cols) > h && cols < n) cols++;
			return { cols, cell: w / cols };
		};
		const layout = () => {
			W = box!.clientWidth;
			H = box!.clientHeight;
			canvas!.width = Math.round(W * dpr);
			canvas!.height = Math.round(H * dpr);
			ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
			const gap = W * 0.06;
			const pw = (W - gap) / 2;
			// one cell size for both panels: the left one is filled by 1956, the right by 795 of the same dots
			const g = grid(UP, pw, H);
			s = Math.max(1.5, g.cell * 0.62);
			const at = (i: number, x0: number) => [x0 + (i % g.cols) * g.cell + g.cell / 2, Math.floor(i / g.cols) * g.cell + g.cell / 2];
			parts = Array.from({ length: UP }, (_, i) => {
				const grp = Math.floor((i * OURS) / UP);
				const first = Math.ceil((grp * UP) / OURS);
				const [x0, y0] = at(i, 0);
				const [x1, y1] = at(grp, pw + gap);
				const rnd = Math.abs((Math.sin(i * 12.9898) * 43758.5453) % 1);
				// left → right: the right-most columns of the left grid travel first
				return { x0, y0, x1, y1, lead: i === first, delay: (1 - (i % g.cols) / g.cols) * 0.35 + (Math.floor(i / g.cols) / Math.ceil(UP / g.cols)) * 0.15 + rnd * 0.05 };
			});
		};
		draw = (fv: number) => {
			ctx.clearRect(0, 0, W, H);
			// the upstream grid stays as a reference; dots that have "left" dim to steel ghosts
			for (const q of parts) {
				const k = clamp01((fv - q.delay) / 0.45);
				ctx.globalAlpha = 0.85 - 0.55 * k;
				ctx.fillStyle = STEEL;
				ctx.fillRect(q.x0 - s / 2, q.y0 - s / 2, s, s);
			}
			// travelling copies fuse into the right grid: members fade on arrival, the lead stays as bone
			for (const q of parts) {
				const k = easeInOutCubic(clamp01((fv - q.delay) / 0.45));
				if (k <= 0 || (!q.lead && k >= 1)) continue;
				const x = q.x0 + (q.x1 - q.x0) * k;
				const y = q.y0 + (q.y1 - q.y0) * k - Math.sin(k * Math.PI) * H * 0.06;
				ctx.globalAlpha = q.lead ? 0.5 + 0.5 * k : 0.7 * (1 - k);
				ctx.fillStyle = q.lead && k > 0.9 ? BONE : STEEL;
				ctx.fillRect(x - s / 2, y - s / 2, s, s);
			}
			ctx.globalAlpha = 1;
		};
		const ro = new ResizeObserver(() => {
			layout();
			draw?.(reducedMotion() ? 1 : f);
		});
		ro.observe(box);
		layout();
		draw(reducedMotion() ? 1 : f);
		return () => {
			ro.disconnect();
			cancelAnimationFrame(raf);
			draw = null;
		};
	});

	/** LFM2.5 runs (no speculation): the sheet's "our engine" factor, the whole gain there. */
	const lfm = (['rtx-3090', 'rtx-5060-ti-16'] as const).map((id) => {
		const card = findCard(id)!;
		return { card, run: card.runs.find((r) => r.model === 'lfm25')! };
	});
	const maxGap = $derived(Math.max(K.gapMs[0].v, K.gapMs[1].v));
	const src = $derived([K.up.src, K.ours.src, HERO_GAIN.src]);
	const note = $derived(`${HERO_CARD.name} · ${HERO_MODEL} ${HERO_RUN.quant}. ${c.dot}`);
	/** The sheet's "skąd zysk" cells in the page language (markdown code ticks removed). */
	const gainNote = $derived(
		[{ card: HERO_CARD, run: HERO_RUN }, ...lfm]
			.map(({ card, run }) => `${card.name} · ${MODEL_INFO[run.model].name}: ${(run.gainText?.[lang] ?? run.gain!.text).map((t) => localizeDecimals(t.replaceAll('\u0060', ''), lang)).join(' · ')}`)
			.join('. ')
	);
</script>

<section id="engine" class="engine" aria-labelledby="engine-title">
	<div class="wrap" use:tl.view>
		<div class="layout">
			<header class="head">
				<h2 id="engine-title" class="statement">{c.title.replace('|', ' ')}</h2>
				<p class="lede">{c.lede}</p>
			</header>
			<!-- the full stack, layer by layer (text only; numbers come from the registry below) -->
			<ol class="layers">
				{#each c.layers as [name, desc], i (name)}
					<li class:focus={i === 1}>
						<span class="li">{String(i + 1).padStart(2, '0')}</span>
						<span class="lt">{name}</span>
						<span class="ld">{desc}</span>
					</li>
				{/each}
			</ol>
			<p class="example"><span class="ex-n">02</span>{c.example} · {HERO_CARD.name} · {HERO_MODEL}</p>
			<div class="viz">
				<div class="counts">
					<p class="ct">
						<span class="cv">{num(UP, lang, 0)}</span>
						<span class="cl">{c.kernels} · {c.up}</span>
					</p>
					<p class="ct ours">
						<span class="cv">{num(OURS, lang, 0)}</span>
						<span class="cl">{c.kernels} · {c.ours} <SourceTip {lang} {src} {note} /></span>
					</p>
				</div>
				<div class="dots" bind:this={box}>
					<canvas bind:this={canvas} aria-hidden="true"></canvas>
				</div>
				<p class="dot-note">{c.dot} <Replay {lang} onclick={tl.replay} disabled={tl.playing} /></p>
				<p class="sr-only">{c.kernels}: {c.up} {UP}, {c.ours} {OURS}.</p>
			</div>
			<div class="side">
				<div class="timeline">
					<p class="th">{c.gaps}</p>
					{#each [0, 1] as i (i)}
						<div class="row" class:ours={i === 1}>
							<span class="who">{i ? c.ours : c.up}</span>
							<span class="gapbar" style="--w:{K.gapMs[i].v / maxGap}"></span>
							<span class="ms"><b>{num(K.gapMs[i].v, lang, 2)}</b>&nbsp;ms</span>
						</div>
					{/each}
					<p class="gpu-note">{fill(c.gpuSame, { a: num(K.gpuMs[0].v, lang), b: num(K.gpuMs[1].v, lang) })}</p>
				</div>
				<p class="honest">
					<Rich
						text={c.honest}
						vars={{ card: HERO_CARD.name, cardA: lfm[0].card.name, cardB: lfm[1].card.name }}
						speed={{
							flags: { text: fmtRatio(HERO_GAIN.flags!.v, lang), v: HERO_GAIN.flags!.v },
							engine: { text: fmtRatio(HERO_GAIN.engine!.v, lang), v: HERO_GAIN.engine!.v },
							lfmA: { text: fmtRatio(lfm[0].run.gain!.engine!.v, lang), v: lfm[0].run.gain!.engine!.v },
							lfmB: { text: fmtRatio(lfm[1].run.gain!.engine!.v, lang), v: lfm[1].run.gain!.engine!.v }
						}}
					/>
					<SourceTip {lang} src={[HERO_GAIN.src, ...lfm.map((l) => l.run.gain!.src)]} note={gainNote} />
				</p>
			</div>
		</div>
	</div>
</section>

<style>
	.layout {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
		grid-template-areas:
			'head   layers'
			'ex     ex'
			'viz    side';
		gap: var(--sp-6) clamp(2rem, 5vw, 5rem);
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
	}
	.head {
		grid-area: head;
		display: grid;
		align-content: start;
		gap: var(--sp-4);
	}
	.layers {
		grid-area: layers;
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-4) var(--sp-5);
		align-content: start;
	}
	.layers li {
		display: grid;
		grid-template-columns: auto 1fr;
		column-gap: var(--sp-3);
		row-gap: 0.2rem;
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
	}
	.layers li.focus {
		border-top-color: var(--text-hi);
	}
	.li {
		grid-row: span 2;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		padding-top: 0.2rem;
	}
	.lt {
		font-weight: 700;
		font-stretch: 108%;
		color: var(--text-hi);
		font-size: var(--fs-sm);
	}
	.ld {
		font-size: var(--fs-xs);
		line-height: 1.45;
		color: var(--text-mute);
	}
	.example {
		grid-area: ex;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding-top: var(--sp-4);
		border-top: 1px solid var(--line);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text);
	}
	.ex-n {
		padding: 0.15rem 0.45rem;
		border: 1px solid var(--text-hi);
		border-radius: 3px;
		color: var(--text-hi);
	}
	/* one statement, one width: no condensed/wide formula here */
	.statement {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.1rem, 0.8rem + 3vw, 4.2rem);
		font-weight: 820;
		font-stretch: 112%;
		line-height: 0.95;
		letter-spacing: -0.04em;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.side {
		grid-area: side;
		display: grid;
		gap: var(--sp-6);
		align-content: start;
	}
	.lede {
		max-width: 44ch;
	}
	.viz {
		grid-area: viz;
		display: grid;
		gap: var(--sp-4);
	}
	/* both final counts, printed statically over their grids */
	.counts {
		display: grid;
		grid-template-columns: 1fr 1fr;
		column-gap: 6%;
	}
	.ct {
		display: grid;
		gap: var(--sp-1);
	}
	.cv {
		font-family: var(--font-mono);
		font-size: clamp(3rem, 1.5rem + 4.4vw, 6.5rem);
		font-weight: 300;
		letter-spacing: -0.06em;
		line-height: 0.9;
		color: var(--before);
	}
	.ours .cv {
		color: var(--text-hi);
	}
	.cl {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text);
	}
	.dots {
		position: relative;
		height: clamp(12rem, 18vw, 17rem);
	}
	canvas {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
	}
	.dot-note {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.04em;
	}
	/* only the waiting between kernels: the part our engine shortens (dotted = overhead) */
	.timeline {
		display: grid;
		gap: var(--sp-3);
		align-content: start;
	}
	.th {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	.row {
		display: grid;
		grid-template-columns: 6.5rem minmax(0, 1fr) 5.5rem;
		align-items: center;
		gap: var(--sp-3);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.row.ours .who {
		color: var(--text-hi);
	}
	.gapbar {
		display: block;
		height: 1.1rem;
		width: calc(var(--w) * 100%);
		border: 1px solid var(--line-strong);
		border-radius: 3px;
		background: radial-gradient(circle, rgb(125 135 148 / 0.9) 1.2px, transparent 1.6px) 0 0 / 6px 6px;
	}
	.row.ours .gapbar {
		border-color: var(--text-hi);
		background: radial-gradient(circle, rgb(237 234 227 / 0.9) 1.2px, transparent 1.6px) 0 0 / 6px 6px;
	}
	.ms {
		font-family: var(--font-mono);
		white-space: nowrap;
		color: var(--text);
		text-align: right;
	}
	.ms b {
		font-size: var(--fs-lg);
		font-weight: 500;
		color: var(--text-hi);
	}
	.gpu-note {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.honest {
		font-size: var(--fs-sm);
		line-height: 1.55;
		color: var(--text);
		max-width: 56ch;
		padding-left: var(--sp-4);
		border-left: 2px solid var(--line-strong);
	}
	@media (max-width: 900px) {
		.layout {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'head' 'layers' 'ex' 'viz' 'side';
		}
		.dots {
			height: 62vw;
		}
		.row {
			grid-template-columns: 5.5rem minmax(0, 1fr) 4.5rem;
		}
	}
	@media (max-width: 560px) {
		.layers {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
