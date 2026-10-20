<script lang="ts">
	/**
	 * Jak to możliwe: one story instead of a dozen. Qwen3.8-27B UD-Q4_K_XL on the RX 7900 XTX, chat
	 * speed from upstream llama.cpp with default settings to our engine today, every milestone
	 * measured with the same script (QWEN_XTX_JOURNEY). One stepped line climbs through the five
	 * milestones on a 0–125 t/s scale: the two upstream ones cold steel, ours heating up to
	 * white-hot. Under each milestone, what we did to get there (the engine's layers). A giant
	 * readout rides the line: it holds on every plateau and climbs on every riser, landing exactly
	 * on the measured value; the multiplier vs the typical app lands at the end. Below, the same
	 * runs' code-edit workload as two bars.
	 * Auto-played on entering the viewport (armed below the fold, replay button); the line is
	 * revealed with clip-path, the spark and labels move by transform/opacity; reduced motion and
	 * SSR show the final state.
	 */
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01, easeInOutCubic } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import { findCard, MODEL_INFO, QWEN_XTX_JOURNEY as J } from '$lib/data/measurements';
	import { fmtRatio } from '$lib/format';
	import { num, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import Hl from './Hl.svelte';
	import { copy } from '$lib/site/copy';
	import { fill } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].engine);
	const card = findCard(J.card)?.name ?? '';
	const S = J.steps;
	const n = S.length;
	const first = S[0].v;
	const last = S[n - 1].v;

	// ---- geometry: viewBox 1000 × 300, scale 30–120 t/s (no empty band under the start); milestone i at the centre of column i ----
	const BOT = 30;
	const TOP = 120;
	const W = 1000;
	const H = 300;
	const col = W / n;
	const cx = (i: number) => (i + 0.5) * col;
	const PL = col * 0.3;
	/** Height of a value on the scale, 0 (bottom) … 1 (top). */
	const fy = (v: number) => (v - BOT) / (TOP - BOT);
	const yv = (v: number) => H * (1 - fy(v));
	/** The stepped line: a plateau round every milestone, a ramp between them. */
	const pts: [number, number][] = [[0, first]];
	S.forEach((s, i) => {
		pts.push([cx(i) - (i ? PL : 0), s.v], [cx(i) + PL, s.v]);
	});
	pts.push([W, last]);
	const line = pts.map(([x, v], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${yv(v).toFixed(1)}`).join(' ');
	const area = `${line} L${W} ${H} L0 ${H} Z`;
	/** Height of the line at x (piecewise linear), in t/s. */
	function valueAt(x: number): number {
		for (let i = 1; i < pts.length; i++) {
			const [x0, v0] = pts[i - 1];
			const [x1, v1] = pts[i];
			if (x <= x1) return x1 === x0 ? v1 : v0 + ((v1 - v0) * (x - x0)) / (x1 - x0);
		}
		return last;
	}

	// ---- timeline: one eased leg per riser, a short hold on every plateau ----
	const tl = new Autoplay(5.2, '0px 0px -20% 0px', { arm: true });
	const A = 0.06;
	const B = 0.9;
	const X = $derived.by(() => {
		const p = tl.p;
		if (p >= 1) return W;
		if (p <= A) return cx(0);
		if (p >= B) return cx(n - 1) + (W - cx(n - 1)) * easeInOutCubic((p - B) / (1 - B));
		const legs = n - 1;
		const u = ((p - A) / (B - A)) * legs;
		const i = Math.min(legs - 1, Math.floor(u));
		// each leg: 75 % moving, 25 % holding on the plateau it reached
		const k = easeInOutCubic(clamp01((u - i) / 0.75));
		return cx(i) + (cx(i + 1) - cx(i)) * k;
	});
	const done = $derived(X >= W);
	/** The readout: exactly the measured value at rest, the line's height while it climbs. */
	const shown = $derived(done ? last : valueAt(X));
	const lit = (i: number) => X >= cx(i) - 1;
	const heat = ['cold', 'cold', 'warm', 'hot', 'white'];
	/**
	 * Gap between our points and their labels below (rem): enough that the steep riser into the next
	 * point (left of it) passes above the label's top corner.
	 */
	const DY = [0, 0, 1.5, 2.6, 1.5];
	const ratio = $derived(fmtRatio(last / first, lang));
	const wide = Math.max(num(first, 'pl', 1).length, num(last, 'pl', 1).length);

	// ---- code editing: the same runs, two bars ----
	const codeTl = new Autoplay(1.6, '0px 0px -10% 0px', { arm: true });
	const ck = $derived(easeInOutCubic(clamp01(codeTl.p / 0.92)));
	const [cu, co] = J.code;

	/** Title as two lines: the claim (bone) and the payoff (heat). */
	const titleParts = $derived(fill(c.title, { a: num(first, lang, 1), b: num(last, lang, 1), x: fmtRatio(last / first, lang) }).split('|'));
</script>

<section id="engine" class="engine heat-top" aria-labelledby="engine-title">
	<div class="atmo" aria-hidden="true"></div>
	<div class="inner">
		<h2 id="engine-title" class="statement"><span class="t1"><Hl text={titleParts[0]} /></span> <span class="t2"><Hl text={titleParts[1] ?? ''} /></span></h2>

		<figure class="journey" class:done class:live={tl.inView} use:tl.view>
			<div class="top">
				<p class="wm"><ModelMark model={J.model} size="0.8em" /> <b>{MODEL_INFO[J.model].name}</b> · {card} <span class="wx">· {c.meta}</span></p>
				<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
			</div>

			<div class="chartbox">
				<!-- wide screens: the readout sits in the chart's empty top-left corner -->
				<div class="readout" aria-hidden="true">
					<span class="big" style:min-width={done ? null : `${wide - 0.9}ch`}>{num(shown, lang, 1)}</span>
					<span class="unit">t/s</span>
					<span class="mult"><b>{ratio}</b> {c.vs}</span>
				</div>
				<div class="plot" aria-hidden="true">
					<svg class="chart" viewBox="0 0 {W} {H}" preserveAspectRatio="none" style:clip-path={done ? null : `inset(-10% ${(100 - (X / W) * 100).toFixed(2)}% -10% 0)`}>
						<defs>
							<linearGradient id="jr-stroke" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={W} y2="0">
								<stop offset="0" stop-color="#7d8794" />
								<stop offset={(cx(1) + PL) / W} stop-color="#7d8794" />
								<stop offset={cx(2) / W} stop-color="#e2401c" />
								<stop offset={cx(3) / W} stop-color="#ff7a1a" />
								<stop offset={cx(4) / W} stop-color="#ffc15a" />
								<stop offset="1" stop-color="#fff3d6" />
							</linearGradient>
							<linearGradient id="jr-fill" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={W} y2="0">
								<stop offset="0" stop-color="#7d8794" stop-opacity="0.1" />
								<stop offset={(cx(1) + PL) / W} stop-color="#7d8794" stop-opacity="0.12" />
								<stop offset={cx(2) / W} stop-color="#e2401c" stop-opacity="0.2" />
								<stop offset="1" stop-color="#ff7a1a" stop-opacity="0.34" />
							</linearGradient>
						</defs>
						<path class="area" d={area} fill="url(#jr-fill)" />
						<path class="glow" d={line} stroke="url(#jr-stroke)" />
						<path class="line" d={line} stroke="url(#jr-stroke)" />
					</svg>
					{#each S as s, i (s.key)}
						<span class="node node--{heat[i]}" class:lit={lit(i)} style="--x:{cx(i) / W}; --y:{fy(s.v)}">
							<i class="dot"></i>
							<b class="nv">{num(s.v, lang, 1)}</b>
						</span>
					{/each}
					<span class="spark" class:on={tl.playing} style="--x:{X / W}; --y:{fy(valueAt(X))}"></span>
				</div>

				<!-- wide screens: each milestone's label sits in the chart by its point (upstream above, ours below) -->
				<ol class="steps">
					{#each c.steps as st, i (i)}
						<li class="step step--{heat[i]}" class:up={i < 2} class:lit={lit(i)} style="--d:{i * 60}ms; --x:{cx(i) / W}; --y:{fy(S[i].v)}; --dy:{DY[i]}rem">
							<b class="sn">{st.name}</b>
							<span class="ss">{st.sub}</span>
							{#if st.did.length}
								<ul class="did" aria-label={c.did}>
									{#each st.did as d (d)}<li>{d}</li>{/each}
								</ul>
							{/if}
							<span class="sr-only">: {num(S[i].v, lang, 1)} t/s</span>
						</li>
					{/each}
				</ol>
			</div>
		</figure>

		<div class="code" use:codeTl.view style="--k:{ck}; --u:{cu.v / co.v}">
			<p class="ch">{c.code}</p>
			<div class="crow">
				<span class="cbar cbar--up" aria-hidden="true"><i></i></span>
				<span class="cv cv--up">{num(cu.v, lang, 1)}</span>
			</div>
			<div class="crow">
				<span class="cbar cbar--ours" aria-hidden="true"><i></i></span>
				<span class="cv"><b>{num(ck >= 1 ? co.v : cu.v + (co.v - cu.v) * ck, lang, 1)}</b>&nbsp;t/s <span class="cx" class:shown={ck >= 1}>{fmtRatio(co.v / cu.v, lang)}</span></span>
			</div>
			<p class="cn">{c.codeNote}</p>
		</div>
	</div>
</section>

<style>
	.engine {
		position: relative;
		isolation: isolate;
		overflow: clip;
		padding-block: clamp(2.5rem, 1.5rem + 3vw, 5rem);
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
		gap: clamp(1rem, 2.5vh, 2rem);
	}
	.statement {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.4rem, 0.9rem + 4.6vw, min(6rem, 8.5svh));
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
		color: var(--text-hi);
	}

	/* ---- the journey ---- */
	.journey {
		margin: 0;
		display: grid;
		gap: clamp(0.8rem, 2vh, 1.4rem);
		padding: clamp(1rem, 0.5rem + 1.6vw, 1.8rem) clamp(1.1rem, 0.6rem + 2vw, 2.4rem);
		border: 1px solid rgb(255 122 26 / 0.24);
		border-radius: 22px;
		background:
			radial-gradient(60% 70% at 90% 100%, rgb(255 122 26 / 0.16), transparent 70%),
			linear-gradient(180deg, rgb(255 255 255 / 0.03), transparent 40%),
			#0b0908;
		box-shadow: 0 40px 80px -40px rgb(0 0 0 / 0.9);
	}
	/* one compact line: model · card · what is measured, the replay button at the end */
	.top {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: center;
		gap: 1rem;
	}
	.wm {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.2rem 0.4rem;
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.wm b {
		font-weight: 600;
		color: var(--text-hi);
	}
	.wx {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	/* one row: the counter, its unit, the multiplier once it lands */
	.readout {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem 0.9rem;
	}
	.big {
		display: inline-block;
		text-align: right;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(2.6rem, 1rem + 3.4vw, min(5rem, 8svh));
		font-weight: 820;
		line-height: 0.9;
		letter-spacing: -0.05em;
		color: var(--heat-5);
		text-shadow:
			0 0 18px rgb(255 193 90 / 0.45),
			0 0 56px rgb(255 122 26 / 0.45);
	}
	.unit {
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
		color: var(--text-mute);
		align-self: flex-end;
		margin-bottom: 0.4rem;
	}
	.mult {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		max-width: 11rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text);
		opacity: 0;
		transform: translate3d(0, 0.4rem, 0);
		transition:
			opacity 0.4s ease,
			transform 0.6s var(--ease-out);
	}
	.mult b {
		padding: 0.25em 0.6em 0.2em;
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		color: #140a04;
		font-family: var(--font-display);
		font-size: clamp(1.2rem, 0.9rem + 1vw, 1.8rem);
		font-weight: 820;
		letter-spacing: -0.02em;
		text-transform: none;
		box-shadow: 0 0 26px rgb(255 122 26 / 0.6);
	}
	.done .mult {
		opacity: 1;
		transform: none;
	}

	/* the chart: an SVG line (non-scaling stroke) with HTML nodes and labels over it */
	.chartbox {
		/* the chart takes what the viewport leaves after the heading, the top row and the milestones */
		--ph: clamp(9rem, 100svh - 36rem, 20rem);
		position: relative;
		display: grid;
		gap: clamp(0.8rem, 2vh, 1.4rem);
		margin-top: 2rem;
	}
	.plot {
		position: relative;
		height: var(--ph);
		background: repeating-linear-gradient(0deg, rgb(237 234 227 / 0.05) 0 1px, transparent 1px 20%);
		border-bottom: 1px solid var(--line-strong);
	}
	.chart {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.chart path {
		fill: none;
		vector-effect: non-scaling-stroke;
		stroke-linejoin: round;
	}
	.chart .area {
		stroke: none;
	}
	.chart .line {
		stroke-width: 3.5;
	}
	/* a wide translucent stroke under the line: the glow without a blur filter (cheap to repaint) */
	.chart .glow {
		stroke-width: 14;
		opacity: 0.16;
	}
	.node {
		position: absolute;
		left: calc(var(--x) * 100%);
		bottom: calc(var(--y) * 100%);
		width: 0;
		height: 0;
	}
	.dot {
		position: absolute;
		left: -0.45rem;
		top: -0.45rem;
		width: 0.9rem;
		height: 0.9rem;
		border-radius: 50%;
		background: var(--bg-0);
		border: 2px solid var(--before);
		transform: scale(0);
		transition: transform 0.5s var(--ease-spring);
	}
	.nv {
		position: absolute;
		left: 0;
		bottom: 0.8rem;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(1.1rem, 0.8rem + 1.1vw, 2rem);
		font-weight: 760;
		letter-spacing: -0.03em;
		line-height: 1;
		white-space: nowrap;
		color: var(--before);
		opacity: 0;
		transform: translate3d(-50%, 0.5rem, 0);
		transition:
			opacity 0.35s ease,
			transform 0.55s var(--ease-out);
	}
	.node.lit .dot {
		transform: none;
	}
	.node.lit .nv {
		opacity: 1;
		transform: translate3d(-50%, 0, 0);
	}
	.node--warm .dot {
		border-color: var(--heat-2);
	}
	.node--warm .nv {
		color: var(--heat-3);
	}
	.node--hot .dot {
		border-color: var(--heat-3);
	}
	.node--hot .nv {
		color: var(--heat-4);
	}
	.node--white .dot {
		border-color: var(--heat-5);
		background: var(--heat-4);
		box-shadow: 0 0 18px rgb(255 193 90 / 0.9);
	}
	.node--white .nv {
		color: #fff;
		font-size: clamp(1.4rem, 1rem + 1.6vw, 2.8rem);
		text-shadow: 0 0 20px rgb(255 122 26 / 0.7);
	}
	/* the last node breathes while the scene is on screen (opacity/transform of a pseudo-element) */
	.node--white .dot::after {
		content: '';
		position: absolute;
		inset: -0.6rem;
		border-radius: 50%;
		border: 2px solid var(--heat-4);
		opacity: 0;
	}
	@media (prefers-reduced-motion: no-preference) {
		.live.done .node--white .dot::after {
			animation: breathe 2.4s var(--ease-out) infinite;
		}
	}
	@keyframes breathe {
		0% {
			opacity: 0.8;
			transform: scale(0.4);
		}
		100% {
			opacity: 0;
			transform: scale(1.6);
		}
	}
	/* the spark at the line's leading edge while it climbs */
	.spark {
		position: absolute;
		left: calc(var(--x) * 100%);
		bottom: calc(var(--y) * 100%);
		width: 1.1rem;
		height: 1.1rem;
		margin: 0 0 -0.55rem -0.55rem;
		border-radius: 50%;
		background: radial-gradient(circle, #fff 0 25%, var(--heat-4) 45%, transparent 70%);
		box-shadow: 0 0 22px 6px rgb(255 122 26 / 0.65);
		opacity: 0;
		pointer-events: none;
		transition: opacity 0.3s ease;
	}
	.spark.on {
		opacity: 1;
	}

	/* what we did, under each milestone */
	.steps {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 0;
	}
	.step {
		display: grid;
		align-content: start;
		gap: 0.25rem;
		padding: 0.2rem 0.6rem 0;
		text-align: center;
		justify-items: center;
		opacity: 0.35;
		transition: opacity 0.5s ease var(--d);
	}
	.step.lit {
		opacity: 1;
	}
	.sn {
		font-weight: 700;
		font-size: var(--fs-md);
		line-height: 1.2;
		color: var(--text-hi);
	}
	.step--cold .sn {
		color: var(--text);
	}
	.step--white .sn {
		color: var(--heat-4);
	}
	.ss {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		line-height: 1.35;
	}
	.did {
		margin: 0.35rem 0 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.3rem;
		justify-items: center;
	}
	.did li {
		padding: 0.25rem 0.6rem;
		border-radius: var(--r-pill);
		border: 1px solid rgb(255 122 26 / 0.45);
		background: rgb(255 122 26 / 0.1);
		font-size: var(--fs-xs);
		font-weight: 600;
		line-height: 1.25;
		color: var(--text-hi);
	}
	.step--white .did li {
		border-color: var(--heat-4);
		background: rgb(255 193 90 / 0.16);
	}
	/* the readout sits in the chart's empty top-left corner (the line starts low there) */
	@media (min-width: 761px) {
		.readout {
			position: absolute;
			left: 0;
			top: 0;
			z-index: 2;
			max-width: 25%;
		}
	}
	@media (min-width: 761px) and (max-width: 1099px) {
		.readout .big {
			font-size: clamp(2rem, 0.4rem + 3vw, 3.2rem);
		}
		.readout .mult b {
			font-size: 1.1rem;
		}
	}
	/*
	 * Wide screens: the labels move into the chart's empty space, each by its point with a leader:
	 * upstream's above the low start (over the value), ours below the high end, and they appear when
	 * the line reaches their point.
	 */
	@media (min-width: 1100px) {
		.chartbox {
			--ph: clamp(14rem, 100svh - 27rem, 22rem);
		}
		.readout {
			max-width: 20%;
		}
		.steps {
			position: absolute;
			inset: 0 0 auto;
			height: var(--ph);
			display: block;
			pointer-events: none;
		}
		.step {
			position: absolute;
			left: calc(var(--x) * 100%);
			width: max-content;
			max-width: 16%;
			padding: 0;
			gap: 0.2rem;
			opacity: 0;
			transform: translate3d(-50%, 0.6rem, 0);
			transition:
				opacity 0.45s ease,
				transform 0.7s var(--ease-out);
		}
		.step.lit {
			opacity: 1;
			transform: translate3d(-50%, 0, 0);
		}
		.step.up {
			bottom: calc(var(--y) * 100% + 4.3rem);
			transform: translate3d(-50%, -0.6rem, 0);
		}
		.step.up.lit {
			transform: translate3d(-50%, 0, 0);
		}
		.step:not(.up) {
			top: calc((1 - var(--y)) * 100% + 0.6rem + var(--dy));
		}
		/* the leader: a hairline between the point (or its value) and the label */
		.step::before {
			content: '';
			position: absolute;
			left: 50%;
			width: 1px;
		}
		.step.up::before {
			top: calc(100% + 0.2rem);
			height: 1rem;
			background: linear-gradient(rgb(125 135 148 / 0.9), rgb(125 135 148 / 0.2));
		}
		.step:not(.up)::before {
			bottom: calc(100% + 0.2rem);
			height: calc(var(--dy) - 0.1rem);
			background: linear-gradient(var(--heat-3), rgb(255 122 26 / 0.15));
		}
		.step--white::before {
			background: linear-gradient(var(--heat-4), rgb(255 193 90 / 0.15));
		}
		.sn {
			font-size: var(--fs-sm);
		}
		.step--warm .sn,
		.step--hot .sn {
			color: var(--heat-4);
		}
		.step--white .sn {
			color: #fff;
		}
		.ss {
			margin-bottom: 0.1rem;
		}
		.did {
			margin: 0.2rem 0 0;
			gap: 0.25rem;
		}
		.did li {
			padding: 0.2rem 0.55rem;
			font-size: var(--fs-2xs);
			text-wrap: balance;
		}
	}

	/* ---- code editing ---- */
	.code {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: 0.6rem 1.2rem;
		padding-inline: clamp(1.2rem, 0.6rem + 2.4vw, 2.6rem);
	}
	.ch {
		grid-row: span 2;
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.2rem, 1rem + 0.8vw, 1.7rem);
		font-weight: 800;
		letter-spacing: -0.02em;
		color: var(--text-hi);
	}
	.crow {
		display: contents;
	}
	.cbar {
		position: relative;
		height: 0.8rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.05);
		overflow: hidden;
	}
	.cbar i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		transform-origin: 0 50%;
	}
	.cbar--up i {
		background: linear-gradient(90deg, #2a3038, var(--before));
		transform: scaleX(var(--u));
	}
	.cbar--ours i {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 18px rgb(255 122 26 / 0.6);
		transform: scaleX(calc(var(--u) + (1 - var(--u)) * var(--k)));
	}
	.cv {
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(1.1rem, 0.9rem + 0.8vw, 1.6rem);
		font-weight: 750;
		white-space: nowrap;
		color: var(--text);
	}
	.cv--up {
		color: var(--before);
	}
	.cv b {
		display: inline-block;
		min-width: 5ch;
		text-align: right;
		color: var(--heat-5);
	}
	.cx {
		display: inline-block;
		margin-left: 0.4rem;
		padding: 0.15em 0.5em 0.1em;
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		color: #140a04;
		font-weight: 820;
		opacity: 0;
		transform: scale(0.7);
		transition:
			opacity 0.3s ease,
			transform 0.6s var(--ease-spring);
	}
	.cx.shown {
		opacity: 1;
		transform: none;
	}
	.cn {
		grid-column: 2 / -1;
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}

	@media (max-width: 760px) {
		/* phones: the headline already carries 114,8 and 3,2×; the chart gets the room */
		.wx,
		.readout {
			display: none;
		}
		.chartbox {
			--ph: clamp(9rem, 100svh - 40rem, 14rem);
			margin-top: 1.6rem;
		}
		.nv {
			font-size: 0.95rem;
		}
		.node--white .nv {
			font-size: 1.3rem;
		}
		/* the milestones as a vertical list with a heat rail */
		.steps {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.5rem;
			padding-left: 0.8rem;
			border-left: 2px solid rgb(255 122 26 / 0.35);
		}
		/* compact rows: the name, then what we did as chips on the same line */
		.step {
			display: flex;
			flex-wrap: wrap;
			align-items: center;
			gap: 0.3rem 0.5rem;
			text-align: left;
			padding: 0;
		}
		.sn {
			font-size: var(--fs-sm);
		}
		.ss {
			display: none;
		}
		.did {
			display: contents;
		}
		.did li {
			padding: 0.15rem 0.5rem;
			font-size: var(--fs-2xs);
		}
		.code {
			grid-template-columns: minmax(0, 1fr) auto;
			padding-inline: 0;
		}
		.ch {
			grid-row: auto;
			grid-column: 1 / -1;
		}
		.cn {
			grid-column: 1 / -1;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.dot,
		.nv,
		.mult,
		.step,
		.cx,
		.spark {
			transition: none;
		}
	}
</style>
