<script module lang="ts">
	import type { PhotoId } from './vendor';

	export interface VsFighter {
		id: string;
		vendor: string;
		/** "3090", "7900 XTX" */
		name: string;
		/** small print under the name (spec, model): each part stays on one line */
		sub: string[];
		photo: PhotoId | null;
		vram: number | null;
		heat: number;
		href?: string;
		hrefLabel?: string;
		/** a caveat under the fighter (e.g. different scripts on its own before/after) */
		note?: string;
	}
	export interface VsStat {
		key: string;
		label: string;
		unit: string;
		decimals: number;
		a: number | null;
		b: number | null;
		/** which way wins; null = shown, never ranked (e.g. memory used) */
		better: 'hi' | 'lo' | null;
		/** small print after a value ("/ 24 GB") */
		aSub?: string;
		bSub?: string;
	}
</script>

<script lang="ts">
	/**
	 * VERSUS: a title-fight face-off of two cards. Each card stands in its maker's colour field (A from
	 * the left, B from the right) and the two fields collide on a diagonal seam with an energy line;
	 * the real product photos face each other (tilted toward the centre, rim-lit in the maker's
	 * colour) and a heavy metallic/ember VS stands on the seam. Below, stat bars clash: each side's
	 * bar grows from its own edge toward the centre on one scale per stat; when the two runs are
	 * comparable (same model, script and conditions) the better side of each ranked stat glows with
	 * a WIN tick and the other dims; otherwise nobody wins. Measured numbers only.
	 *
	 * Entrance (once): the cards slam in from the sides, VS punches in with a shockwave ring, the seam
	 * crackles, sparks fly, the bars race. `mode="intro"`: plays from the first paint (the arena is
	 * above the fold; the content is never hidden behind JS). `mode="view"`: if the arena is below
	 * the fold at load it plays when it scrolls into view and the numbers count up; if it is already
	 * on screen it stays as it is. Then calm: only a slow rim-light drift. Hover a card: it turns
	 * further and its rim brightens. Reduced motion: the final frame, still. Phones: A on top, B
	 * below, the VS on the seam between them.
	 */
	import type { Snippet } from 'svelte';
	import Odometer from '$lib/fx/Odometer.svelte';
	import { reducedMotion } from '$lib/fx/motion';
	import type { Lang } from '$lib/i18n';
	import GpuArt from './GpuArt.svelte';
	import ProductPhoto from './ProductPhoto.svelte';
	import { VENDOR, vendorOf } from './vendor';

	let {
		a,
		b,
		stats,
		verdict,
		lang,
		winLabel,
		missingLabel,
		mode = 'intro',
		size = 'full',
		nameTag = 'h2',
		center,
		foot
	}: {
		a: VsFighter;
		b: VsFighter;
		stats: VsStat[];
		/** the runs are comparable: rank the stats (WIN / dim) */
		verdict: boolean;
		lang: Lang;
		winLabel: string;
		missingLabel: string;
		mode?: 'intro' | 'view';
		size?: 'full' | 'teaser';
		nameTag?: 'h2' | 'h3' | 'p';
		/** under the stats, centred (teaser: title and call to action) */
		center?: Snippet;
		/** under the arena */
		foot?: Snippet;
	} = $props();

	const colours = $derived.by(() => {
		const va = VENDOR[vendorOf(a.vendor)];
		const vb = VENDOR[vendorOf(b.vendor)];
		return `--a:${va.rgb}; --a-hi:${va.hi}; --a-deep:${va.deep}; --b:${vb.rgb}; --b-hi:${vb.hi}; --b-deep:${vb.deep}`;
	});
	const rows = $derived(
		stats
			.filter((s) => s.a != null || s.b != null)
			.map((s) => {
				/* bar length: the share of the better value; for lower-is-better stats (seconds) the
				   quicker side is the full bar (best ÷ value), so the longer bar is always the stronger */
				const lo = s.better === 'lo';
				const best = lo ? Math.min(...[s.a, s.b].filter((v): v is number => v != null && v > 0)) : Math.max(s.a ?? 0, s.b ?? 0) || 1;
				const bar = (v: number | null) => (v == null || v <= 0 ? 0 : lo ? best / v : v / best);
				const ranked = verdict && s.better != null && s.a != null && s.b != null && s.a !== s.b;
				const aWins = ranked && (s.better === 'hi' ? s.a! > s.b! : s.a! < s.b!);
				return { ...s, fa: bar(s.a), fb: bar(s.b), wa: ranked && aWins, wb: ranked && !aWins };
			})
	);
	/* sparks off the VS: fixed directions so server and client render the same */
	const SPARKS = [
		[-150, -70],
		[-120, 40],
		[-60, -110],
		[-30, 95],
		[40, -120],
		[70, 105],
		[125, -50],
		[150, 60],
		[-170, -10],
		[175, -5]
	];

	/* view mode: below the fold at load → wait out of sight, then play once when it scrolls in */
	let phase = $state<'idle' | 'pre' | 'run'>('idle');
	let count = $state(0);
	function entrance(node: HTMLElement) {
		if (mode !== 'view' || reducedMotion() || typeof IntersectionObserver === 'undefined') return;
		if (node.getBoundingClientRect().top < innerHeight) return;
		phase = 'pre';
		const io = new IntersectionObserver(
			([e]) => {
				if (!e.isIntersecting) return;
				phase = 'run';
				count++;
				io.disconnect();
			},
			{ threshold: 0.3 }
		);
		io.observe(node);
		return { destroy: () => io.disconnect() };
	}
</script>

{#snippet fighter(f: VsFighter, side: 'a' | 'b')}
	<div class="ft ft-{side}">
		<p class="ft-wm" class:upright={f.vendor === 'intel' || f.vendor === 'apple'}>{VENDOR[vendorOf(f.vendor)].name}</p>
		<div class="ft-stage" aria-hidden="true">
			<span class="rim"></span>
			<span class="floor"></span>
			<div class="ft-tilt">
				{#if f.photo}
					<ProductPhoto id={f.photo} sizes={size === 'teaser' ? '(max-width: 40rem) 70vw, 22rem' : '(max-width: 40rem) 78vw, 30rem'} eager={mode === 'intro'}>
						{#snippet fallback()}<GpuArt label={f.name} vendor={f.vendor} vram={f.vram} heat={f.heat} flat />{/snippet}
					</ProductPhoto>
				{:else}
					<GpuArt label={f.name} vendor={f.vendor} vram={f.vram} heat={f.heat} flat />
				{/if}
			</div>
		</div>
		<svelte:element this={nameTag} class="ft-nm">{f.name}</svelte:element>
		<p class="ft-sub mono">{#each f.sub as part, i (i)}{#if i}{' · '}{/if}<span class="part">{part}</span>{/each}</p>
		{#if f.href || f.note}
			<p class="ft-foot">
				{#if f.href}<a href={f.href} class="ft-more">{f.hrefLabel} <span aria-hidden="true">→</span></a>{/if}
				{#if f.note}<span class="ft-note mono">{f.note}</span>{/if}
			</p>
		{/if}
	</div>
{/snippet}

<div class="vs vs--{size} {phase}" class:run={phase === 'run' || mode === 'intro'} style={colours} use:entrance>
	<div class="face">
		<span class="field field-a" aria-hidden="true"></span>
		<span class="field field-b" aria-hidden="true"></span>
		<svg class="seam seam-v" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
			<polyline class="s-glow" points="57,0 54,13 58,22 51,36 55,45 48,57 52,66 45,79 49,88 43,100" />
			<polyline class="s-core" points="57,0 54,13 58,22 51,36 55,45 48,57 52,66 45,79 49,88 43,100" />
		</svg>
		<svg class="seam seam-h" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
			<polyline class="s-glow" points="0,44 12,47 21,43 34,50 45,46 57,53 67,49 79,56 88,52 100,56" />
			<polyline class="s-core" points="0,44 12,47 21,43 34,50 45,46 57,53 67,49 79,56 88,52 100,56" />
		</svg>

		{#key a.id}{@render fighter(a, 'a')}{/key}

		<div class="core" aria-hidden="true">
			{#key `${a.id}-${b.id}`}
				<span class="ring"></span>
				<span class="sparks">{#each SPARKS as [x, y], i (i)}<i style="--dx:{x}px; --dy:{y}px; --d:{i * 18}ms"></i>{/each}</span>
				<span class="mark">VS</span>
			{/key}
		</div>

		{#key b.id}{@render fighter(b, 'b')}{/key}
	</div>

	{#if rows.length}
		<dl class="stats">
			{#each rows as r, i (r.key)}
				<div class="row" class:wa={r.wa} class:wb={r.wb} style="--fa:{r.fa.toFixed(4)}; --fb:{r.fb.toFixed(4)}; --i:{i}">
					<dt class="lbl">{r.label}</dt>
					<dd class="sv sv-a">
						{#if r.a != null}
							<span class="num fig"><Odometer value={r.a} decimals={r.decimals} {lang} duration={1100} replay={count} /></span><span class="u">{r.unit}{#if r.aSub}&nbsp;{r.aSub}{/if}</span>
						{:else}<span class="miss">{missingLabel}</span>{/if}
						{#if r.wa}<span class="win">✓ {winLabel}</span>{/if}
					</dd>
					<dd class="trk trk-a" aria-hidden="true"><i></i></dd>
					<dd class="trk trk-b" aria-hidden="true"><i></i></dd>
					<dd class="sv sv-b">
						{#if r.wb}<span class="win">✓ {winLabel}</span>{/if}
						{#if r.b != null}
							<span class="num fig"><Odometer value={r.b} decimals={r.decimals} {lang} duration={1100} replay={count} /></span><span class="u">{r.unit}{#if r.bSub}&nbsp;{r.bSub}{/if}</span>
						{:else}<span class="miss">{missingLabel}</span>{/if}
					</dd>
				</div>
			{/each}
		</dl>
	{/if}

	{#if center}<div class="center">{@render center()}</div>{/if}
</div>
{#if foot}{@render foot()}{/if}

<style>
	/* ================= the arena: always dark, the makers' colours colliding ================= */
	.vs {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		color-scheme: dark;
		position: relative;
		display: grid;
		border-radius: var(--r-xl);
		color: var(--text);
		background:
			linear-gradient(180deg, transparent 55%, rgb(0 0 0 / 0.55)),
			linear-gradient(90deg, var(--a-deep), #070708 50%, var(--b-deep));
		box-shadow:
			inset 0 0 0 1px rgb(255 255 255 / 0.08),
			inset 2px 0 0 rgb(var(--a) / 0.7),
			inset -2px 0 0 rgb(var(--b) / 0.7),
			0 50px 90px -60px #000;
		overflow: hidden;
		isolation: isolate;
	}

	/* the face-off: A | VS | B */
	.face {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: center;
		gap: 0 clamp(0.5rem, 2vw, 2rem);
		padding: clamp(1.25rem, 3vw, 2.5rem) clamp(1rem, 3vw, 2.75rem) clamp(1rem, 2vw, 1.75rem);
		isolation: isolate;
	}
	/* each maker's field, cut on the diagonal where they collide; strongest at the outer edge and
	   again at the collision, where the light piles up */
	.field {
		position: absolute;
		z-index: -2;
		inset: 0;
		pointer-events: none;
	}
	.field-a {
		background:
			radial-gradient(70% 90% at 0% 45%, rgb(var(--a) / 0.62), transparent 70%),
			linear-gradient(90deg, rgb(var(--a) / 0.3), rgb(var(--a) / 0.08) 38%, rgb(var(--a) / 0.34) 56%);
		clip-path: polygon(0 0, 57% 0, 43% 100%, 0 100%);
	}
	.field-b {
		background:
			radial-gradient(70% 90% at 100% 45%, rgb(var(--b) / 0.62), transparent 70%),
			linear-gradient(270deg, rgb(var(--b) / 0.3), rgb(var(--b) / 0.08) 38%, rgb(var(--b) / 0.34) 56%);
		clip-path: polygon(57% 0, 100% 0, 100% 100%, 43% 100%);
	}
	/* the energy line on the seam */
	.seam {
		position: absolute;
		z-index: -1;
		inset: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
		overflow: visible;
	}
	.seam-h {
		display: none;
	}
	.seam polyline {
		fill: none;
		vector-effect: non-scaling-stroke;
		stroke-linejoin: round;
	}
	.s-glow {
		stroke: rgb(255 214 150 / 0.28);
		stroke-width: 14;
	}
	.s-core {
		stroke: #fff3d6;
		stroke-width: 2.5;
	}

	/* ---------- a fighter ---------- */
	.ft {
		--c: var(--a);
		--c-hi: var(--a-hi);
		--ry: 14deg;
		position: relative;
		display: grid;
		justify-items: start;
		align-content: start;
		gap: 0.25rem;
		min-width: 0;
	}
	.ft-b {
		--c: var(--b);
		--c-hi: var(--b-hi);
		--ry: -14deg;
		justify-items: end;
		text-align: right;
	}
	.ft-wm {
		margin: 0;
		padding: 0.04em 0.25em 0.1em 0.04em;
		font-family: var(--font-display);
		font-size: clamp(1rem, 0.6rem + 1.2vw, 1.75rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 118%;
		letter-spacing: 0.02em;
		line-height: 1;
		color: var(--c-hi);
		text-shadow: 0 0 20px rgb(var(--c) / 0.75);
	}
	.ft-wm.upright {
		font-style: normal;
	}
	/* one box per fighter whatever its picture (3:2 photo or the SVG render), so names line up */
	.ft-stage {
		position: relative;
		display: grid;
		place-items: center;
		width: min(100%, 30rem);
		aspect-ratio: 3 / 2;
		margin-block: var(--sp-2) var(--sp-3);
		perspective: 900px;
		user-select: none;
	}
	/* the rim light behind the card: drifts slowly, brightens on hover */
	.rim {
		position: absolute;
		inset: -12% -8%;
		background: radial-gradient(45% 50% at 50% 50%, rgb(var(--c) / 0.55), rgb(var(--c) / 0.12) 60%, transparent 75%);
		opacity: 0.75;
		transition: opacity 0.5s var(--ease-out);
	}
	.floor {
		position: absolute;
		left: 10%;
		right: 10%;
		bottom: -4%;
		height: 22%;
		border-radius: 50%;
		background: radial-gradient(closest-side, rgb(var(--c) / 0.5), rgb(0 0 0 / 0.45) 55%, transparent);
		transform: scaleY(0.55);
	}
	/* the card turned toward the centre, its silhouette rimmed in the maker's colour */
	.ft-tilt {
		position: relative;
		width: 100%;
		transform: rotateY(var(--ry));
		transform-origin: 50% 60%;
		transition: transform 0.7s var(--ease-spring);
		filter: drop-shadow(0 0 1.5px rgb(var(--c) / 0.9)) drop-shadow(0 0 16px rgb(var(--c) / 0.45));
		will-change: transform;
	}
	.ft:hover .ft-tilt {
		transform: rotateY(calc(var(--ry) * 1.8)) translate3d(0, -3%, 0) scale(1.04);
	}
	.ft:hover .rim {
		opacity: 1;
	}
	.ft-nm {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2rem, 0.9rem + 3.6vw, 4.75rem);
		font-weight: 900;
		font-stretch: 118%;
		letter-spacing: -0.045em;
		line-height: 0.95;
		color: var(--text-hi);
		white-space: nowrap;
		text-shadow: 0 2px 0 rgb(0 0 0 / 0.5);
	}
	.ft-sub {
		margin: 0;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.ft-sub .part {
		white-space: nowrap;
	}
	.ft-foot {
		margin: var(--sp-2) 0 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
	}
	.ft-b .ft-foot {
		justify-content: flex-end;
	}
	.ft-more {
		font-size: var(--fs-sm);
		font-weight: 650;
		color: var(--text-hi);
		text-decoration-color: rgb(var(--c));
	}
	.ft-more:hover {
		color: var(--c-hi);
	}
	.ft-note {
		font-size: var(--fs-2xs);
		color: var(--text);
		padding: 0.2rem 0.5rem;
		border: 1px dashed rgb(255 255 255 / 0.2);
		border-radius: var(--r-sm);
	}

	/* ---------- the VS on the seam ---------- */
	.core {
		position: relative;
		display: grid;
		place-items: center;
		align-self: center;
		pointer-events: none;
	}
	.mark {
		display: block;
		padding: 0.08em 0.24em 0.12em 0.14em;
		font-family: var(--font-display);
		font-size: clamp(4rem, 2rem + 6.5vw, 10.5rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 125%;
		letter-spacing: -0.06em;
		line-height: 0.82;
		/* metal on top, ember below */
		background: linear-gradient(176deg, #ffffff 8%, #e6e3dd 30%, #8e8b87 47%, #fff3d6 52%, #ffc15a 64%, #ff7a1a 80%, #e2401c 96%);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		-webkit-text-stroke: 1px rgb(255 255 255 / 0.35);
		filter: drop-shadow(0 0 26px rgb(255 160 80 / 0.45)) drop-shadow(0 6px 0 rgb(0 0 0 / 0.6));
	}
	.ring {
		position: absolute;
		width: 9rem;
		aspect-ratio: 1;
		border-radius: 50%;
		border: 3px solid rgb(255 243 214 / 0.9);
		box-shadow: 0 0 30px 4px rgb(255 160 80 / 0.5), inset 0 0 24px rgb(255 160 80 / 0.4);
		opacity: 0;
	}
	.sparks {
		position: absolute;
		inset: 50% auto auto 50%;
	}
	.sparks i {
		position: absolute;
		width: 6px;
		height: 6px;
		margin: -3px;
		border-radius: 50%;
		background: #fff3d6;
		box-shadow: 0 0 10px 2px rgb(255 160 80 / 0.8);
		opacity: 0;
	}

	/* ---------- the clash of numbers ---------- */
	.stats {
		margin: 0;
		display: grid;
		gap: var(--sp-3);
		padding: var(--sp-4) clamp(1rem, 3vw, 2.75rem) clamp(1.25rem, 2.5vw, 2rem);
		background: linear-gradient(90deg, rgb(var(--a) / 0.08), transparent 40% 60%, rgb(var(--b) / 0.08));
		border-top: 1px solid rgb(255 255 255 / 0.08);
	}
	.row {
		display: grid;
		grid-template-columns: minmax(8.5rem, auto) minmax(0, 1fr) minmax(0, 1fr) minmax(8.5rem, auto);
		grid-template-areas: '. lbl lbl .' 'va ta tb vb';
		align-items: center;
		column-gap: var(--sp-3);
		row-gap: 0.3rem;
	}
	/* the stat's name sits above the clash point */
	.lbl {
		grid-area: lbl;
		justify-self: center;
		padding: 0.2rem 0.65rem;
		border-radius: var(--r-pill);
		background: #0b0b0d;
		box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.14);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text);
		white-space: nowrap;
	}
	.sv {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.1rem 0.4rem;
		min-width: 0;
		transition: opacity 0.4s;
	}
	.sv-a {
		grid-area: va;
	}
	.sv-b {
		grid-area: vb;
		justify-content: flex-end;
		text-align: right;
	}
	.num {
		font-size: clamp(1.4rem, 0.9rem + 1.3vw, 2.25rem);
		font-weight: 720;
		line-height: 1;
		color: var(--text-hi);
	}
	.row:first-child .num {
		font-size: clamp(1.9rem, 1rem + 2.4vw, 3.5rem);
	}
	.u {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.miss {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.win {
		align-self: center;
		padding: 0.15rem 0.45rem;
		border-radius: var(--r-sm);
		background: #fff3d6;
		color: #1a1205;
		font-family: var(--font-display);
		font-size: 0.7rem;
		font-weight: 900;
		font-style: italic;
		letter-spacing: 0.06em;
		box-shadow: 0 0 18px rgb(255 193 90 / 0.7);
	}
	.trk {
		margin: 0;
		position: relative;
		height: 0.7rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.06);
		overflow: hidden;
		transition: opacity 0.4s;
	}
	.trk-a {
		grid-area: ta;
	}
	.trk-b {
		grid-area: tb;
	}
	/* each bar grows from its own edge toward the clash point */
	.trk i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		transition: transform 0.9s var(--ease-spring);
	}
	.trk-a i {
		background: linear-gradient(90deg, rgb(var(--a) / 0.55), rgb(var(--a)) 70%, var(--a-hi) 94%, #fff3d6);
		transform: scaleX(var(--fa));
		transform-origin: 0 50%;
	}
	.trk-b i {
		background: linear-gradient(270deg, rgb(var(--b) / 0.55), rgb(var(--b)) 70%, var(--b-hi) 94%, #fff3d6);
		transform: scaleX(var(--fb));
		transform-origin: 100% 50%;
	}
	.row.wa .trk-a,
	.row.wb .trk-b {
		box-shadow: 0 0 18px rgb(255 214 150 / 0.45);
	}
	.row.wa .sv-a .num,
	.row.wb .sv-b .num {
		text-shadow: 0 0 22px rgb(255 214 150 / 0.55);
	}
	/* the loser of a ranked stat steps back */
	.row.wa :is(.sv-b, .trk-b),
	.row.wb :is(.sv-a, .trk-a) {
		opacity: 0.42;
	}

	.center {
		display: grid;
		justify-items: center;
		gap: var(--sp-3);
		padding: 0 clamp(1rem, 3vw, 2.75rem) clamp(1.5rem, 3vw, 2.5rem);
		text-align: center;
	}

	/* ================= the entrance (once), then calm ================= */
	@media (prefers-reduced-motion: no-preference) {
		/* waiting out of sight (view mode): the start frame */
		.pre .ft-a {
			opacity: 0;
			transform: translate3d(-60%, 0, 0);
		}
		.pre .ft-b {
			opacity: 0;
			transform: translate3d(60%, 0, 0);
		}
		.pre .mark {
			opacity: 0;
		}
		.pre .trk i {
			transform: scaleX(0);
		}
		.pre .seam {
			opacity: 0;
		}

		.run .ft-a {
			animation: slam-a 0.42s cubic-bezier(0.3, 1.5, 0.55, 1) backwards;
		}
		.run .ft-b {
			animation: slam-b 0.42s cubic-bezier(0.3, 1.5, 0.55, 1) backwards;
		}
		.run .mark {
			animation: punch 0.4s cubic-bezier(0.3, 1.6, 0.5, 1) 0.3s backwards;
		}
		.run .ring {
			animation: wave 0.7s var(--ease-out) 0.36s backwards;
		}
		.run .sparks i {
			animation: spark 0.65s var(--ease-out) calc(0.36s + var(--d)) backwards;
		}
		.run .seam {
			animation: crackle 0.55s linear 0.32s backwards;
		}
		.run .trk-a i {
			animation: bar-a 0.9s var(--ease-out) calc(0.5s + var(--i) * 0.08s) backwards;
		}
		.run .trk-b i {
			animation: bar-b 0.9s var(--ease-out) calc(0.5s + var(--i) * 0.08s) backwards;
		}
		.run .win {
			animation: win 0.45s cubic-bezier(0.3, 1.6, 0.5, 1) calc(1.15s + var(--i) * 0.08s) backwards;
		}
		/* idle: the rim light drifts slowly (no pulsing) */
		.rim {
			animation: drift 11s var(--ease-in-out) infinite alternate;
		}
		.ft-b .rim {
			animation-delay: -5.5s;
		}
	}
	@keyframes slam-a {
		from {
			opacity: 0;
			transform: translate3d(-60%, 0, 0);
		}
	}
	@keyframes slam-b {
		from {
			opacity: 0;
			transform: translate3d(60%, 0, 0);
		}
	}
	@keyframes punch {
		from {
			opacity: 0;
			transform: scale(2.6) rotate(-8deg);
		}
	}
	@keyframes wave {
		from {
			opacity: 1;
			transform: scale(0.3);
		}
		to {
			opacity: 0;
			transform: scale(2.6);
		}
	}
	@keyframes spark {
		from {
			opacity: 1;
			transform: translate3d(0, 0, 0) scale(1);
		}
		to {
			opacity: 0;
			transform: translate3d(var(--dx), var(--dy), 0) scale(0.3);
		}
	}
	@keyframes crackle {
		0% {
			opacity: 0;
		}
		12% {
			opacity: 1;
		}
		24% {
			opacity: 0.2;
		}
		38% {
			opacity: 1;
		}
		52% {
			opacity: 0.45;
		}
		70% {
			opacity: 1;
		}
	}
	@keyframes bar-a {
		from {
			transform: scaleX(0);
		}
	}
	@keyframes bar-b {
		from {
			transform: scaleX(0);
		}
	}
	@keyframes win {
		from {
			opacity: 0;
			transform: scale(0.4);
		}
	}
	@keyframes drift {
		from {
			transform: translate3d(-4%, 2%, 0) scale(0.97);
		}
		to {
			transform: translate3d(4%, -2%, 0) scale(1.03);
		}
	}

	/* ================= teaser: one screen ================= */
	.vs--teaser .ft-stage {
		width: min(100%, 22rem);
	}
	.vs--teaser .mark {
		font-size: clamp(3.5rem, 1.8rem + 5vw, 8rem);
	}
	.vs--teaser .ft-nm {
		font-size: clamp(1.75rem, 0.9rem + 2.6vw, 3.5rem);
	}

	/* ================= narrow: A on top, B below, the VS on the seam between ================= */
	@media (max-width: 56rem) {
		.face {
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: auto auto auto;
			justify-items: stretch;
			gap: 0;
			padding: var(--sp-4) clamp(1rem, 3vw, 2rem) var(--sp-3);
		}
		.field-a {
			background:
				radial-gradient(90% 70% at 30% 0%, rgb(var(--a) / 0.6), transparent 70%),
				linear-gradient(180deg, rgb(var(--a) / 0.25), rgb(var(--a) / 0.08) 30%, rgb(var(--a) / 0.32) 50%);
			clip-path: polygon(0 0, 100% 0, 100% 56%, 0 44%);
		}
		.field-b {
			background:
				radial-gradient(90% 70% at 70% 100%, rgb(var(--b) / 0.6), transparent 70%),
				linear-gradient(0deg, rgb(var(--b) / 0.25), rgb(var(--b) / 0.08) 30%, rgb(var(--b) / 0.32) 50%);
			clip-path: polygon(0 44%, 100% 56%, 100% 100%, 0 100%);
		}
		.seam-v {
			display: none;
		}
		.seam-h {
			display: block;
		}
		/* each fighter: its photo on the outer side, its name toward the middle */
		.ft {
			grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
			grid-template-areas: 'wm stage' 'nm stage' 'sub stage' 'foot stage';
			align-items: end;
			column-gap: var(--sp-3);
		}
		.ft-b {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr);
			grid-template-areas: 'stage wm' 'stage nm' 'stage sub' 'stage foot';
		}
		.ft-wm {
			grid-area: wm;
			font-size: 1rem;
		}
		/* a gentler turn, and room at the outer edge, so the card never leaves the arena */
		.ft-stage {
			grid-area: stage;
			width: 92%;
			margin: 0;
			align-self: center;
			justify-self: center;
		}
		.ft-a {
			--ry: 8deg;
		}
		.ft-b {
			--ry: -8deg;
		}
		.ft-nm,
		.vs--teaser .ft-nm {
			grid-area: nm;
			font-size: clamp(1.45rem, 0.4rem + 5vw, 3rem);
		}
		.ft-sub {
			grid-area: sub;
		}
		.ft-foot {
			grid-area: foot;
		}
		.core {
			margin-block: calc(-1 * var(--sp-2));
			z-index: 1;
		}
		.mark,
		.vs--teaser .mark {
			font-size: clamp(4rem, 2rem + 6vw, 6rem);
		}
		.ring {
			width: 6rem;
		}
	}
	/* phones: each stat's two numbers side by side, the bars meeting under them */
	@media (max-width: 40rem) {
		.stats {
			padding: var(--sp-3) var(--sp-4) var(--sp-4);
			gap: var(--sp-4);
		}
		.row {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
			grid-template-areas: 'lbl lbl' 'va vb' 'ta tb';
			column-gap: var(--sp-2);
		}
		.num,
		.row:first-child .num {
			font-size: clamp(1.25rem, 0.5rem + 4.4vw, 1.75rem);
		}
		.trk {
			height: 0.55rem;
		}
	}
</style>
