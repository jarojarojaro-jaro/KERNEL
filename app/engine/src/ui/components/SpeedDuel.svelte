<script lang="ts">
	/**
	 * Two tachometers on one scale: the typical app (official llama.cpp, steel) and Enigma (ember), with
	 * the measured lab numbers from `DUEL`. The needles sweep once from zero when the screen opens
	 * (a one-off transition, never a loop); with reduced motion they start at their values.
	 */
	import { onMount } from 'svelte';
	import { num } from '../lib/i18n';
	import { DUEL } from '../lib/showcase';
	import { store } from '../lib/store.svelte';

	const t = $derived(store.t.welcome.duel);
	const lang = $derived(store.lang);
	const ratio = DUEL.ours / DUEL.typical;
	let on = $state(false);
	onMount(() => {
		const id = requestAnimationFrame(() => (on = true));
		return () => cancelAnimationFrame(id);
	});

	const R = 62;
	const C = 80;
	/** angle in degrees on the 270° dial for a value (−135° … +135°, 0° pointing up) */
	const ang = (v: number) => -135 + (270 * Math.min(v, DUEL.scale)) / DUEL.scale;
	const pt = (a: number, r: number) => {
		const rad = ((a - 90) * Math.PI) / 180;
		return `${(C + r * Math.cos(rad)).toFixed(2)} ${(C + r * Math.sin(rad)).toFixed(2)}`;
	};
	const arc = (from: number, to: number, r: number) => `M ${pt(from, r)} A ${r} ${r} 0 ${to - from > 180 ? 1 : 0} 1 ${pt(to, r)}`;
	const ticks = Array.from({ length: 8 }, (_, i) => i * 20);
	const dials = [
		{ key: 'typical', v: DUEL.typical, label: () => t.typical, sub: () => t.typicalSub },
		{ key: 'ours', v: DUEL.ours, label: () => t.ours, sub: () => t.oursSub }
	] as const;
</script>

<figure class="duel panel panel--heat" class:on>
	<figcaption class="head">
		<span class="eyebrow">{t.title}</span>
		<span class="badge badge--measured">{t.measured}</span>
	</figcaption>
	<p class="sr-only">{t.sr(num(DUEL.typical, lang, 1), num(DUEL.ours, lang, 1), `${num(ratio, lang, 1)}×`)}</p>
	<div class="dials" aria-hidden="true">
		{#each dials as d (d.key)}
			<div class="dial {d.key}">
				<svg viewBox="0 0 160 140">
					<defs>
						<linearGradient id="duel-heat" x1="0" y1="1" x2="1" y2="0">
							<stop offset="0" stop-color="#e2401c" />
							<stop offset=".55" stop-color="#ff7a1a" />
							<stop offset="1" stop-color="#ffc15a" />
						</linearGradient>
					</defs>
					<path d={arc(-135, 135, R)} class="track" />
					{#each ticks as v (v)}
						<path d={`M ${pt(ang(v), R - 9)} L ${pt(ang(v), R - 3)}`} class="tick" />
						<text x={pt(ang(v), R - 18).split(' ')[0]} y={Number(pt(ang(v), R - 18).split(' ')[1]) + 3} class="tl">{v}</text>
					{/each}
					<path d={arc(-135, ang(d.v), R)} class="val" pathLength="100" />
					<g class="needle" style="--a:{ang(d.v)}deg">
						<line x1={C} y1={C} x2={C} y2={C - R + 12} />
					</g>
					<circle cx={C} cy={C} r="5" class="hub" />
				</svg>
				<p class="read num"><span class="v">{num(d.v, lang, 1)}</span> <span class="u">t/s</span></p>
				<p class="lbl">{d.label()}</p>
				<p class="sub">{d.sub()}</p>
			</div>
		{/each}
		<p class="x num"><span class="xv">{num(ratio, lang, 1)}×</span><span class="xl">{t.faster}</span></p>
	</div>
	<p class="note num">{t.note}</p>
</figure>

<style>
	.duel {
		display: grid;
		gap: var(--sp-5);
		margin: 0;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--sp-3);
	}
	.head .badge {
		margin: 0;
	}
	.dials {
		position: relative;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-4);
	}
	.dial {
		display: grid;
		justify-items: center;
		text-align: center;
	}
	svg {
		width: 100%;
		max-width: 13rem;
		overflow: visible;
	}
	.track {
		fill: none;
		stroke: var(--bg-3);
		stroke-width: 7;
		stroke-linecap: round;
	}
	.tick {
		stroke: var(--line-strong);
		stroke-width: 1.4;
	}
	.tl {
		fill: var(--text-mute);
		font-family: var(--font-mono);
		font-size: 7px;
		text-anchor: middle;
	}
	.val {
		fill: none;
		stroke-width: 7;
		stroke-linecap: round;
		stroke-dasharray: 100;
		stroke-dashoffset: 100;
		transition: stroke-dashoffset 1.4s var(--ease-out);
	}
	.typical .val {
		stroke: var(--before);
	}
	.ours .val {
		stroke: url(#duel-heat);
		filter: drop-shadow(0 0 6px rgb(255 122 26 / 0.55));
	}
	.on .val {
		stroke-dashoffset: 0;
	}
	.needle {
		transform-origin: 80px 80px;
		transform: rotate(-135deg);
		transition: transform 1.4s var(--ease-spring);
	}
	.on .needle {
		transform: rotate(var(--a));
	}
	.needle line {
		stroke-width: 3;
		stroke-linecap: round;
	}
	.typical .needle line {
		stroke: var(--before);
	}
	.ours .needle line {
		stroke: var(--heat-3);
	}
	.hub {
		fill: var(--text-hi);
	}
	.read {
		margin: -1.6rem 0 0;
	}
	.v {
		font-size: clamp(1.6rem, 1.1rem + 1.6vw, 2.4rem);
		font-weight: 560;
		letter-spacing: -0.04em;
		color: var(--text-hi);
	}
	.ours .v {
		color: var(--accent-ink);
	}
	.typical .v {
		color: var(--before);
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.lbl {
		margin-top: var(--sp-2);
		color: var(--text-hi);
		font-weight: 680;
	}
	.sub {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.x {
		grid-column: 1 / -1;
		display: flex;
		align-items: baseline;
		justify-content: center;
		gap: 0.7rem;
		margin: var(--sp-2) 0 0;
		padding-top: var(--sp-4);
		border-top: 1px solid var(--line);
	}
	.xv {
		font-size: clamp(2.2rem, 1.4rem + 2.6vw, 3.4rem);
		font-weight: 600;
		line-height: 1;
		letter-spacing: -0.05em;
		background: var(--heat-large);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.xl {
		font-size: var(--fs-xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.note {
		margin: 0;
		font-size: var(--fs-2xs);
		line-height: 1.6;
		color: var(--text-mute);
	}
	@media (prefers-reduced-motion: reduce) {
		.val,
		.needle {
			transition: none;
		}
	}
</style>
