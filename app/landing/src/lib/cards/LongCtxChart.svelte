<script lang="ts">
	/**
	 * Generation speed vs context depth, upstream (cold, dashed) against ours (heat). Lines draw
	 * themselves when the chart enters the viewport (stroke-dashoffset on a normalised pathLength);
	 * reduced motion shows them drawn.
	 */
	import { Play } from './play.svelte';
	import { num } from '$lib/i18n';
	import type { Num } from '$lib/data/measurements';

	let {
		depths,
		up,
		ours,
		lang,
		labels,
		title
	}: { depths: number[]; up: Num[]; ours: Num[]; lang: 'pl' | 'en'; labels: { up: string; ours: string; depth: string }; title: string } = $props();

	const uid = $props.id();
	const W = 640;
	const H = 280;
	const P = { l: 48, r: 36, t: 30, b: 44 };
	/** Points start this far right of the y axis so their labels never meet the tick labels. */
	const INSET = 40;
	const top = $derived(Math.max(...up.map((n) => n.v), ...ours.map((n) => n.v)) * 1.15);
	/** x is proportional to the context length (a linear axis: 8k sits close to 0, 64k at the end). */
	const dMax = $derived(Math.max(...depths));
	const x = (i: number) => P.l + INSET + ((W - P.l - INSET - P.r) * depths[i]) / dMax;
	const y = (v: number) => H - P.b - ((H - P.t - P.b) * v) / top;
	const path = (ns: Num[]) => ns.map((n, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(n.v).toFixed(1)}`).join(' ');
	/** Round grid step: 1, 2 or 5 × 10^n, about four lines. */
	const step = $derived.by(() => {
		const raw = top / 4;
		const p = 10 ** Math.floor(Math.log10(raw));
		return [1, 2, 5, 10].map((m) => m * p).find((s) => s >= raw)!;
	});
	const grid = $derived(Array.from({ length: Math.floor(top / step) }, (_, i) => (i + 1) * step));
	const kfmt = (d: number) => (d === 0 ? '0' : `${Math.round(d / 1024)}k`);
	/** The curves draw themselves when the chart enters the view; at rest (and on SSR) they are drawn. */
	const draw = new Play(2900);
</script>

<figure class="chart" class:play={draw.on} use:draw.view>
	<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="lc-{uid}">
		<title id="lc-{uid}">{title}: {depths.map((d, i) => `${kfmt(d)} ${num(up[i].v, lang)} → ${num(ours[i].v, lang)} t/s`).join('; ')}</title>
		<defs>
			<linearGradient id="lg-{uid}" x1="0" y1="0" x2="1" y2="0">
				<stop offset="0" style="stop-color: var(--heat-4, #ffc15a)" />
				<stop offset="1" style="stop-color: var(--heat-2, #e2401c)" />
			</linearGradient>
			<linearGradient id="fill-{uid}" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" style="stop-color: var(--heat-3, #ff7a1a)" stop-opacity="0.22" />
				<stop offset="1" style="stop-color: var(--heat-3, #ff7a1a)" stop-opacity="0" />
			</linearGradient>
		</defs>
		{#each grid as g (g)}
			<line x1={P.l} x2={W - P.r} y1={y(g)} y2={y(g)} class="grid" />
			<text x={P.l - 10} y={y(g) + 4} class="ax" text-anchor="end">{num(g, lang, 0)}</text>
		{/each}
		{#each depths as d, i (d)}
			<text x={x(i)} y={H - P.b + 24} class="ax" text-anchor="middle">{kfmt(d)}</text>
		{/each}
		<path class="area" d="{path(ours)} L{x(ours.length - 1)} {H - P.b} L{x(0)} {H - P.b} Z" fill="url(#fill-{uid})" />
		<path class="line up" d={path(up)} pathLength="1" />
		<path class="line ours" d={path(ours)} pathLength="1" stroke="url(#lg-{uid})" />
		{#each ours as n, i (i)}
			<g class="pt" style="--i:{i}">
				<circle cx={x(i)} cy={y(up[i].v)} r="3.5" class="dot up" />
				<circle cx={x(i)} cy={y(n.v)} r="4.5" class="dot ours" />
				<text x={x(i)} y={y(n.v) - 12} class="val" text-anchor="middle">{num(n.v, lang)}</text>
				<text x={x(i)} y={y(up[i].v) + 20} class="val cold" text-anchor="middle">{num(up[i].v, lang)}</text>
			</g>
		{/each}
	</svg>
	<figcaption class="legend mono">
		<span><i class="sw ours"></i>{labels.ours}</span>
		<span><i class="sw up"></i>{labels.up}</span>
		<span class="axis-l">{labels.depth}{'\u00a0'}→</span>
	</figcaption>
</figure>

<style>
	.chart {
		margin: 0;
		display: grid;
		gap: var(--sp-3);
	}
	svg {
		width: 100%;
		height: auto;
		overflow: visible;
	}
	.grid {
		stroke: var(--line);
		stroke-width: 1;
	}
	.ax {
		font-family: var(--font-mono);
		font-size: 11px;
		fill: var(--text-mute);
	}
	.line {
		fill: none;
		stroke-width: 3;
		stroke-linecap: round;
		stroke-linejoin: round;
		stroke-dasharray: 1;
		stroke-dashoffset: 0;
	}
	.line.up {
		stroke: var(--before);
		stroke-width: 2;
		stroke-dasharray: none;
	}
	.line.ours {
		filter: drop-shadow(0 0 6px rgb(var(--hot-rgb, 255 122 26) / 0.6));
	}
	.dot.up {
		fill: var(--bg-0);
		stroke: var(--before);
		stroke-width: 2;
	}
	.dot.ours {
		fill: var(--heat-5);
	}
	.val {
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 600;
		fill: var(--text-hi);
	}
	.val.cold {
		fill: var(--before);
		font-weight: 500;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2) var(--sp-5);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.axis-l {
		margin-left: auto;
		min-width: 0;
		text-align: right;
	}
	.sw {
		display: inline-block;
		width: 1.2rem;
		height: 3px;
		margin-right: 0.45rem;
		vertical-align: middle;
		border-radius: 2px;
	}
	.sw.ours {
		background: var(--heat-ramp-hot);
	}
	.sw.up {
		background: var(--before);
	}
	/* only while a play runs: at rest (and on SSR) both curves, the area and the points are drawn */
	@media (prefers-reduced-motion: no-preference) {
		.play .line {
			animation: draw 1.6s cubic-bezier(0.65, 0, 0.35, 1) both;
		}
		.play .line.up {
			stroke-dasharray: 1;
		}
		.play .line.ours {
			animation-delay: 0.35s;
		}
		.play .area {
			animation: fade-in 0.6s var(--ease-out) 1.4s both;
		}
		.play .pt {
			animation: fade-in 0.6s var(--ease-out) calc(0.5s + var(--i) * 0.35s) both;
		}
	}
	@keyframes draw {
		from {
			stroke-dashoffset: 1;
		}
	}
	@keyframes fade-in {
		from {
			opacity: 0;
		}
	}
</style>
