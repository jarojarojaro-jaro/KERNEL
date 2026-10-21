<script module lang="ts">
	import type { PhotoId } from './vendor';

	export interface VsFighter {
		id: string;
		vendor: string;
		/** "3090", "7900 XTX" */
		name: string;
		/** the maker's consumer line next to the wordmark ("GeForce RTX") */
		line?: string;
		/** small print on the name plate (memory, model, quant): each part stays on one line */
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
	 * VERSUS: a title-fight face-off of two cards, full-bleed and one screen tall. Each card stands in
	 * its maker's colour field under volumetric beams, on a lit floor with its reflection; the real
	 * product photos face each other and clash at the seam, where the two fields meet in a crackling
	 * energy split under a metallic, bevelled VS emblem with an ember core. Below, a round-by-round
	 * scoreboard: each stat's bars race from both edges toward the stat's name in the middle. A row
	 * shows only when both cards have the measurement. When the runs are comparable (same model,
	 * script and conditions) the better side of a ranked stat gets the WIN and the other steps back;
	 * otherwise nobody wins: both values glow in their maker's colour and the board says why.
	 *
	 * Entrance (once): the cards slam in with speed streaks, the arena shakes a pixel or two, the VS
	 * punches in with a flash and a shockwave, the seam crackles, the bars race and the numbers count
	 * up. `mode="intro"`: plays from the first paint (content never hidden behind JS). `mode="view"`:
	 * below the fold at load → plays when it scrolls in; already on screen → stays as it is. Then
	 * calm: the rim light drifts, the beams sway, now and then a faint spark. Offscreen everything
	 * pauses. Hover a card: it turns further and its rim brightens. Reduced motion: the final frame.
	 * Phones: A on top, B below, the VS on the seam between them.
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
		boardTag,
		boardNote,
		mode = 'intro',
		size = 'full',
		nameTag = 'h2',
		center,
		foot
	}: {
		a: VsFighter;
		b: VsFighter;
		stats: VsStat[];
		/** the runs are comparable: rank the stats (WIN / step back) */
		verdict: boolean;
		lang: Lang;
		winLabel: string;
		/** the scoreboard's head: "Verdict" or "No verdict" */
		boardTag: string;
		/** why (e.g. different scripts) */
		boardNote?: string;
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
	/* a row only when both cards have the measurement: one number against nothing says nothing */
	const rows = $derived(
		stats
			.filter((s): s is VsStat & { a: number; b: number } => s.a != null && s.b != null && s.a > 0 && s.b > 0)
			.map((s) => {
				/* bar length: the share of the better value; for lower-is-better stats (seconds) the
				   quicker side is the full bar (best ÷ value), so the longer bar is always the stronger */
				const lo = s.better === 'lo';
				const best = lo ? Math.min(s.a, s.b) : Math.max(s.a, s.b);
				const bar = (v: number) => (lo ? best / v : v / best);
				const ranked = verdict && s.better != null && s.a !== s.b;
				const aWins = ranked && (s.better === 'hi' ? s.a > s.b : s.a < s.b);
				return { ...s, fa: bar(s.a), fb: bar(s.b), wa: ranked && aWins, wb: ranked && !aWins };
			})
	);
	/* the impact burst off the VS, and the rare idle sparks on the seam: fixed, so SSR = client */
	const SPARKS = [
		[-170, -60],
		[-130, 50],
		[-70, -115],
		[-35, 100],
		[45, -125],
		[80, 110],
		[135, -45],
		[165, 70],
		[-190, 5],
		[195, -10],
		[-95, -20],
		[105, 25]
	];
	const IDLE = [
		[0, 8, 30],
		[1, 11, 62],
		[2, 13, 80]
	];

	/* view mode: below the fold at load → wait out of sight, then play once when it scrolls in.
	   intro mode: the CSS entrance runs from the first paint; the numbers count up when the bars race.
	   Both: every animation pauses while the arena is offscreen. */
	let phase = $state<'idle' | 'pre' | 'run'>('idle');
	let count = $state(0);
	let off = $state(false);
	function arena(node: HTMLElement) {
		if (typeof IntersectionObserver === 'undefined') return;
		const still = reducedMotion();
		let waiting = false;
		let timer: ReturnType<typeof setTimeout> | undefined;
		if (!still && mode === 'view' && node.getBoundingClientRect().top >= innerHeight) {
			phase = 'pre';
			waiting = true;
		}
		if (!still && mode === 'intro') {
			/* count up with the bars (≈0.75 s in), unless hydration came after that */
			const t = Number(node.querySelector('.ft')?.getAnimations?.()[0]?.currentTime ?? 9999);
			if (t < 600) timer = setTimeout(() => count++, 700 - t);
		}
		const io = new IntersectionObserver(
			([e]) => {
				off = !e.isIntersecting;
				if (waiting && e.intersectionRatio >= 0.3) {
					waiting = false;
					phase = 'run';
					count++;
				}
			},
			{ threshold: [0, 0.3] }
		);
		io.observe(node);
		return {
			destroy() {
				io.disconnect();
				clearTimeout(timer);
			}
		};
	}
</script>

{#snippet photo(f: VsFighter, eager: boolean)}
	{#if f.photo}
		<ProductPhoto id={f.photo} sizes={size === 'teaser' ? '(max-width: 40rem) 60vw, 26rem' : '(max-width: 40rem) 60vw, 30rem'} {eager}>
			{#snippet fallback()}<GpuArt label={f.name} vendor={f.vendor} vram={f.vram} heat={f.heat} flat />{/snippet}
		</ProductPhoto>
	{:else}
		<GpuArt label={f.name} vendor={f.vendor} vram={f.vram} heat={f.heat} flat />
	{/if}
{/snippet}

{#snippet fighter(f: VsFighter, side: 'a' | 'b')}
	<div class="ft ft-{side}">
		<div class="ft-stage" aria-hidden="true">
			<span class="rim"></span>
			<span class="streaks"><i></i><i></i><i></i><i></i><i></i></span>
			<div class="ft-tilt">
				<div class="ft-ph">{@render photo(f, mode === 'intro')}</div>
				<div class="ft-refl">{@render photo(f, false)}</div>
			</div>
		</div>
		<div class="plate">
			<p class="ft-wm">
				<span class="wm" class:upright={f.vendor === 'intel' || f.vendor === 'apple'}>{VENDOR[vendorOf(f.vendor)].name}</span>
				{#if f.line}<span class="ln mono">{f.line}</span>{/if}
			</p>
			<svelte:element this={nameTag} class="ft-nm">{f.name}</svelte:element>
			<p class="ft-sub mono">{#each f.sub as part, i (i)}{#if i}<span class="dot" aria-hidden="true">{' · '}</span>{/if}<span class="part">{part}</span>{/each}</p>
			{#if f.href || f.note}
				<p class="ft-foot">
					{#if f.href}<a href={f.href} class="ft-more">{f.hrefLabel} <span aria-hidden="true">→</span></a>{/if}
					{#if f.note}<span class="ft-note mono">{f.note}</span>{/if}
				</p>
			{/if}
		</div>
	</div>
{/snippet}

<div class="vs vs--{size}" class:pre={phase === 'pre'} class:run={phase === 'run' || mode === 'intro'} class:off class:ranked={verdict} style={colours} use:arena>
	<div class="face">
		<div class="fx" aria-hidden="true">
			<span class="field field-a"></span>
			<span class="field field-b"></span>
			<span class="beams beams-a"><i></i><i></i><i></i></span>
			<span class="beams beams-b"><i></i><i></i><i></i></span>
			<span class="floor"><span class="grid"></span></span>
			<svg class="seam seam-v" viewBox="0 0 100 100" preserveAspectRatio="none">
				<polyline class="s-glow" points="57,0 54,12 58,21 51,34 55,44 49,55 53,64 46,77 50,87 43,100" />
				<polyline class="s-arc" points="57,0 55.5,11 59,20.5 52.5,35 56,44.5 50,54 54,65 47,76.5 51,88 43,100" />
				<polyline class="s-core" points="57,0 54,12 58,21 51,34 55,44 49,55 53,64 46,77 50,87 43,100" />
			</svg>
			<svg class="seam seam-h" viewBox="0 0 100 100" preserveAspectRatio="none">
				<polyline class="s-glow" points="0,45 12,48 21,44 34,51 45,47 57,54 67,50 79,56 88,52 100,56" />
				<polyline class="s-arc" points="0,45 12,49 21,43 34,52 45,46 57,55 67,49 79,57 88,51 100,56" />
				<polyline class="s-core" points="0,45 12,48 21,44 34,51 45,47 57,54 67,50 79,56 88,52 100,56" />
			</svg>
			<span class="drips">{#each IDLE as [k, s, y] (k)}<i style="--s:{s}s; --y:{y}%; --k:{k}"></i>{/each}</span>
		</div>

		{#key a.id}{@render fighter(a, 'a')}{/key}

		<div class="core" aria-hidden="true">
			{#key `${a.id}-${b.id}`}
				<div class="emb">
					<span class="e-core"></span>
					<span class="ring"></span>
					<span class="ring r2"></span>
					<span class="e-plate"><span class="e-in"></span></span>
					<span class="e-txt e-ext">VS</span>
					<span class="e-txt e-face">VS</span>
					<span class="sparks">{#each SPARKS as [x, y], i (i)}<i style="--dx:{x}px; --dy:{y}px; --ang:{Math.atan2(y, x).toFixed(3)}rad; --d:{(i % 6) * 22}ms"></i>{/each}</span>
				</div>
			{/key}
		</div>

		{#key b.id}{@render fighter(b, 'b')}{/key}
		<span class="flash" aria-hidden="true"></span>
	</div>

	{#if rows.length}
		<div class="board">
			<p class="bh"><span class="bh-tag">{boardTag}</span>{#if boardNote}<span class="bh-note">{boardNote}</span>{/if}</p>
			<dl class="stats">
				{#each rows as r, i (r.key)}
					<div class="row" class:wa={r.wa} class:wb={r.wb} style="--fa:{r.fa.toFixed(4)}; --fb:{r.fb.toFixed(4)}; --i:{i}">
						<dt class="lbl"><span class="rn" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>{r.label}</dt>
						<dd class="sv sv-a">
							{#if r.wa}<span class="win">{winLabel}</span>{/if}
							<span class="num fig"><Odometer value={r.a} decimals={r.decimals} {lang} duration={1100} replay={count} /></span><span class="u" class:x={r.unit === '×'}>{r.unit}</span>{#if r.aSub}<span class="sub">{r.aSub}</span>{/if}
						</dd>
						<dd class="trk trk-a" aria-hidden="true"><i></i></dd>
						<dd class="trk trk-b" aria-hidden="true"><i></i></dd>
						<dd class="sv sv-b">
							<span class="num fig"><Odometer value={r.b} decimals={r.decimals} {lang} duration={1100} replay={count} /></span><span class="u" class:x={r.unit === '×'}>{r.unit}</span>{#if r.bSub}<span class="sub">{r.bSub}</span>{/if}
							{#if r.wb}<span class="win">{winLabel}</span>{/if}
						</dd>
					</div>
				{/each}
			</dl>
		</div>
	{/if}

	{#if center}<div class="center">{@render center()}</div>{/if}
</div>
{#if foot}{@render foot()}{/if}

<style>
	/* ================= the arena: always dark, full-bleed, the makers' colours colliding ================= */
	.vs {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		--pad-x: max(var(--gutter), (100% - 88rem) / 2);
		--stage-h: clamp(9.5rem, 30svh, 17rem);
		color-scheme: dark;
		position: relative;
		display: grid;
		color: var(--text);
		background:
			linear-gradient(180deg, transparent 50%, rgb(0 0 0 / 0.6)),
			linear-gradient(90deg, var(--a-deep), #060607 50%, var(--b-deep));
		overflow: hidden;
		isolation: isolate;
	}
	/* hairlines top and bottom in the makers' colours, white-hot where they meet */
	.vs::before,
	.vs::after {
		content: '';
		position: absolute;
		z-index: 3;
		left: 0;
		right: 0;
		height: 1px;
		background: linear-gradient(90deg, rgb(var(--a) / 0.1), rgb(var(--a) / 0.9) 30%, #fff3d6 50%, rgb(var(--b) / 0.9) 70%, rgb(var(--b) / 0.1));
		pointer-events: none;
	}
	.vs::before {
		top: 0;
	}
	.vs::after {
		bottom: 0;
	}

	/* the face-off: A | VS | B */
	.face {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: end;
		padding: clamp(1rem, 2.6svh, 2rem) var(--pad-x) clamp(0.75rem, 1.6svh, 1.25rem);
		isolation: isolate;
	}
	.fx {
		position: absolute;
		z-index: -1;
		inset: 0;
		pointer-events: none;
	}
	.fx > * {
		position: absolute;
	}
	/* each maker's field, cut on the diagonal where they collide; strongest at the outer edge and
	   again at the collision, where the light piles up */
	.field {
		inset: 0;
	}
	.field-a {
		background:
			radial-gradient(60% 80% at 0% 40%, rgb(var(--a) / 0.6), transparent 70%),
			radial-gradient(30% 60% at 52% 50%, rgb(var(--a) / 0.45), transparent 70%),
			linear-gradient(90deg, rgb(var(--a) / 0.24), rgb(var(--a) / 0.05) 36%, rgb(var(--a) / 0.3) 56%);
		clip-path: polygon(0 0, 57% 0, 43% 100%, 0 100%);
	}
	.field-b {
		background:
			radial-gradient(60% 80% at 100% 40%, rgb(var(--b) / 0.6), transparent 70%),
			radial-gradient(30% 60% at 48% 50%, rgb(var(--b) / 0.45), transparent 70%),
			linear-gradient(270deg, rgb(var(--b) / 0.24), rgb(var(--b) / 0.05) 36%, rgb(var(--b) / 0.3) 56%);
		clip-path: polygon(57% 0, 100% 0, 100% 100%, 43% 100%);
	}
	/* volumetric beams from the rig above, in the maker's colour, soft at the sides */
	.beams {
		inset: 0 50% 0 0;
	}
	.beams-b {
		inset: 0 0 0 50%;
	}
	.beams i {
		position: absolute;
		top: -8%;
		left: var(--x);
		width: var(--w);
		height: 112%;
		background: linear-gradient(180deg, rgb(var(--c) / 0.5), rgb(var(--c) / 0.16) 55%, transparent 92%);
		clip-path: polygon(42% 0, 58% 0, 100% 100%, 0 100%);
		-webkit-mask-image: linear-gradient(90deg, transparent, #000 40% 60%, transparent);
		mask-image: linear-gradient(90deg, transparent, #000 40% 60%, transparent);
		mix-blend-mode: screen;
		transform-origin: 50% 0;
		transform: rotate(var(--r));
		opacity: 0.55;
	}
	.beams-a i {
		--c: var(--a);
	}
	.beams-b i {
		--c: var(--b);
	}
	.beams-a i:nth-child(1) {
		--x: 8%;
		--w: 26%;
		--r: -10deg;
	}
	.beams-a i:nth-child(2) {
		--x: 38%;
		--w: 30%;
		--r: 6deg;
	}
	.beams-a i:nth-child(3) {
		--x: 66%;
		--w: 22%;
		--r: 14deg;
		opacity: 0.4;
	}
	.beams-b i:nth-child(1) {
		--x: 66%;
		--w: 26%;
		--r: 10deg;
	}
	.beams-b i:nth-child(2) {
		--x: 32%;
		--w: 30%;
		--r: -6deg;
	}
	.beams-b i:nth-child(3) {
		--x: 12%;
		--w: 22%;
		--r: -14deg;
		opacity: 0.4;
	}
	/* the lit floor: a horizon line hot at the seam, a perspective grid fading into the dark */
	.floor {
		left: 0;
		right: 0;
		bottom: 0;
		/* the horizon at the cards' feet */
		top: calc(clamp(1rem, 2.6svh, 2rem) + var(--stage-h) * 0.84);
		background:
			linear-gradient(90deg, rgb(var(--a) / 0), rgb(var(--a) / 0.75) 24%, #fff3d6 50%, rgb(var(--b) / 0.75) 76%, rgb(var(--b) / 0)) top / 100% 1px no-repeat,
			radial-gradient(40% 70% at 25% 0%, rgb(var(--a) / 0.32), transparent 70%),
			radial-gradient(40% 70% at 75% 0%, rgb(var(--b) / 0.32), transparent 70%),
			linear-gradient(180deg, rgb(0 0 0 / 0.15), rgb(0 0 0 / 0.55));
		overflow: hidden;
	}
	.grid {
		position: absolute;
		inset: 0 -40% -60%;
		background:
			repeating-linear-gradient(90deg, rgb(255 255 255 / 0.07) 0 1px, transparent 1px 3.5rem),
			repeating-linear-gradient(180deg, rgb(255 255 255 / 0.06) 0 1px, transparent 1px 2.25rem);
		transform: perspective(26rem) rotateX(64deg);
		transform-origin: 50% 0;
		-webkit-mask-image: linear-gradient(180deg, #000, transparent 70%);
		mask-image: linear-gradient(180deg, #000, transparent 70%);
	}
	/* the energy split on the seam: glow, a white-hot core and side arcs */
	.seam {
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.seam-h {
		display: none;
	}
	.seam polyline {
		fill: none;
		vector-effect: non-scaling-stroke;
		stroke-linejoin: round;
		stroke-linecap: round;
	}
	.s-glow {
		stroke: rgb(255 190 120 / 0.3);
		stroke-width: 16;
	}
	.s-arc {
		stroke: rgb(255 226 180 / 0.75);
		stroke-width: 1.25;
	}
	.s-core {
		stroke: #fff6e2;
		stroke-width: 2.5;
	}
	/* an occasional faint spark sliding down the seam (idle) */
	.drips i {
		position: absolute;
		left: calc(57% - var(--y) * 0.14);
		top: var(--y);
		width: 5px;
		height: 5px;
		margin: -2.5px;
		border-radius: 50%;
		background: #fff3d6;
		box-shadow: 0 0 8px 2px rgb(255 170 90 / 0.8);
		opacity: 0;
	}
	/* the impact flash: over the cards for a blink */
	.flash {
		position: absolute;
		z-index: 2;
		inset: 0;
		background: radial-gradient(38% 60% at 50% 45%, rgb(255 246 226 / 0.95), rgb(255 170 90 / 0.35) 45%, transparent 75%);
		mix-blend-mode: screen;
		pointer-events: none;
		opacity: 0;
	}

	/* ---------- a fighter ---------- */
	.ft {
		--c: var(--a);
		--c-hi: var(--a-hi);
		--ry: 18deg;
		--rz: -2deg;
		--in: 1;
		position: relative;
		display: grid;
		grid-template-areas: 'stage' 'plate';
		min-width: 0;
	}
	.ft-b {
		--c: var(--b);
		--c-hi: var(--b-hi);
		--ry: -18deg;
		--rz: 2deg;
		--in: -1;
	}
	/* one box per fighter whatever its picture (3:2 photo or the SVG render); toward the seam, so the
	   two cards meet at the VS */
	.ft-stage {
		grid-area: stage;
		position: relative;
		z-index: 1;
		display: grid;
		place-items: center;
		height: var(--stage-h);
		aspect-ratio: 3 / 2;
		max-width: 108%;
		justify-self: end;
		margin-right: clamp(-5rem, -4vw, -1.5rem);
		perspective: 900px;
		user-select: none;
	}
	.ft-b .ft-stage {
		justify-self: start;
		margin-right: 0;
		margin-left: clamp(-5rem, -4vw, -1.5rem);
	}
	/* the rim light behind the card: drifts slowly, brightens on hover */
	.rim {
		position: absolute;
		inset: -18% -10%;
		background: radial-gradient(45% 50% at 50% 50%, rgb(var(--c) / 0.6), rgb(var(--c) / 0.14) 60%, transparent 75%);
		opacity: 0.75;
		transition: opacity 0.5s var(--ease-out);
	}
	/* speed streaks behind the card while it slams in (motion blur, transforms only) */
	.streaks {
		position: absolute;
		inset: 10% -30%;
		opacity: 0;
	}
	.streaks i {
		position: absolute;
		left: 0;
		right: 0;
		height: 2px;
		border-radius: 2px;
		background: linear-gradient(90deg, transparent, rgb(var(--c) / 0.9) 60%, #fff3d6);
	}
	.ft-b .streaks i {
		background: linear-gradient(270deg, transparent, rgb(var(--c) / 0.9) 60%, #fff3d6);
	}
	.streaks i:nth-child(1) {
		top: 8%;
	}
	.streaks i:nth-child(2) {
		top: 30%;
		height: 3px;
	}
	.streaks i:nth-child(3) {
		top: 52%;
	}
	.streaks i:nth-child(4) {
		top: 70%;
		height: 3px;
	}
	.streaks i:nth-child(5) {
		top: 90%;
	}
	/* the card turned toward the centre, its silhouette rimmed in the maker's colour */
	.ft-tilt {
		position: relative;
		width: 100%;
		transform: rotateY(var(--ry)) rotateZ(var(--rz));
		transform-origin: 50% 60%;
		transition: transform 0.7s var(--ease-spring);
		will-change: transform;
	}
	.ft-ph {
		filter: drop-shadow(0 0 1.5px rgb(var(--c) / 0.95)) drop-shadow(0 0 18px rgb(var(--c) / 0.5));
	}
	/* the reflection on the floor */
	.ft-refl {
		position: absolute;
		top: 92%;
		left: 0;
		width: 100%;
		transform: scaleY(-1);
		opacity: 0.32;
		-webkit-mask-image: linear-gradient(180deg, transparent 62%, #000);
		mask-image: linear-gradient(180deg, transparent 62%, #000);
		pointer-events: none;
	}
	.ft:hover .ft-tilt {
		transform: rotateY(calc(var(--ry) * 1.7)) rotateZ(var(--rz)) translate3d(0, -3%, 0) scale(1.04);
	}
	.ft:hover .rim {
		opacity: 1;
	}

	/* the name plate: a fight-poster billing, on the outer side, over the floor */
	.plate {
		grid-area: plate;
		position: relative;
		z-index: 2;
		display: grid;
		justify-items: start;
		gap: 0.15rem;
		margin-top: calc(var(--stage-h) * -0.2);
		min-width: 0;
	}
	.ft-b .plate {
		justify-items: end;
		text-align: right;
	}
	.ft-wm {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
	}
	.ft-b .ft-wm {
		flex-direction: row-reverse;
	}
	.wm {
		padding: 0.04em 0.25em 0.1em 0.04em;
		font-family: var(--font-display);
		font-size: clamp(0.95rem, 0.6rem + 0.9vw, 1.5rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 118%;
		letter-spacing: 0.02em;
		line-height: 1;
		color: var(--c-hi);
		text-shadow: 0 0 18px rgb(var(--c) / 0.8);
	}
	.wm.upright {
		font-style: normal;
	}
	.ln {
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text);
	}
	.ft-nm {
		margin: 0;
		/* room for the italic overhang inside the clipped background */
		padding-right: 0.25em;
		font-family: var(--font-display);
		font-size: clamp(2.25rem, 0.8rem + 4.2vw, 5.25rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 122%;
		letter-spacing: -0.05em;
		line-height: 0.88;
		white-space: nowrap;
		/* polished metal with a hot edge */
		background: linear-gradient(180deg, #ffffff 15%, #d9d6cf 52%, #8f8b85 54%, #e9e6df 88%);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 3px 0 rgb(0 0 0 / 0.55)) drop-shadow(0 0 18px rgb(var(--c) / 0.4));
	}
	.ft-b .ft-nm {
		margin-right: -0.25em;
	}
	/* the bill: memory · model · quant, on a strip in the maker's colour */
	.ft-sub {
		margin: 0.35rem 0 0;
		padding: 0.3rem 0.7rem 0.3rem 0.6rem;
		font-size: var(--fs-2xs);
		color: var(--text-hi);
		background: linear-gradient(90deg, rgb(var(--c) / 0.35), rgb(0 0 0 / 0.55) 70%);
		box-shadow: inset 3px 0 0 rgb(var(--c));
		clip-path: polygon(0 0, 100% 0, calc(100% - 0.5rem) 100%, 0 100%);
	}
	.ft-b .ft-sub {
		padding: 0.3rem 0.6rem 0.3rem 0.7rem;
		background: linear-gradient(270deg, rgb(var(--c) / 0.35), rgb(0 0 0 / 0.55) 70%);
		box-shadow: inset -3px 0 0 rgb(var(--c));
		clip-path: polygon(0 0, 100% 0, 100% 100%, 0.5rem 100%);
	}
	.ft-sub .part {
		white-space: nowrap;
	}
	.ft-sub .dot {
		color: rgb(var(--c));
	}
	.ft-foot {
		margin: var(--sp-1) 0 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
	}
	.ft-b .ft-foot {
		justify-content: flex-end;
	}
	.ft-more {
		display: inline-block;
		padding-block: 0.45rem;
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

	/* ---------- the VS emblem on the seam: bevelled metal plate, ember core, extruded letters ---------- */
	.core {
		position: relative;
		z-index: 3;
		display: grid;
		place-items: center;
		align-self: center;
		margin-top: calc(var(--stage-h) * -0.15);
		pointer-events: none;
	}
	.emb {
		--e: clamp(6.5rem, 3.5rem + 5.5vw, 9.5rem);
		position: relative;
		display: grid;
		place-items: center;
		width: var(--e);
		aspect-ratio: 1.12;
	}
	.emb > * {
		grid-area: 1 / 1;
	}
	/* the glow and the shockwaves sit around the plate without sizing it */
	.e-core {
		position: absolute;
		left: -60%;
		top: 50%;
		width: 220%;
		margin-top: -110%;
		aspect-ratio: 1;
		border-radius: 50%;
		background: radial-gradient(closest-side, rgb(255 150 60 / 0.55), rgb(226 64 28 / 0.22) 45%, transparent);
	}
	.e-plate {
		position: relative;
		width: 100%;
		height: 100%;
		clip-path: polygon(24% 0, 76% 0, 100% 50%, 76% 100%, 24% 100%, 0 50%);
		/* the bevel: brushed metal around the rim */
		background: conic-gradient(from 210deg, #f6f3ec, #7a7671 12%, #e2ded7 24%, #3d3b39 38%, #cfcbc4 52%, #5e5b57 66%, #fbf8f1 80%, #8a8681 90%, #f6f3ec);
		filter: drop-shadow(0 10px 18px rgb(0 0 0 / 0.6));
	}
	.e-in {
		position: absolute;
		inset: 5px;
		clip-path: polygon(24% 0, 76% 0, 100% 50%, 76% 100%, 24% 100%, 0 50%);
		/* gunmetal face, the ember burning through from inside */
		background:
			radial-gradient(55% 45% at 50% 62%, rgb(255 140 50 / 0.85), rgb(226 64 28 / 0.4) 50%, transparent 80%),
			linear-gradient(180deg, #34312d, #121110 60%, #1d1a17);
		box-shadow: inset 0 2px 0 rgb(255 255 255 / 0.25);
	}
	.e-txt {
		padding: 0.06em 0.2em 0.1em 0.1em;
		font-family: var(--font-display);
		font-size: calc(var(--e) * 0.7);
		font-weight: 900;
		font-style: italic;
		font-stretch: 125%;
		letter-spacing: -0.06em;
		line-height: 0.82;
	}
	/* the extrusion: the same letters, dark, stepped down and to the right */
	.e-ext {
		color: #3b1606;
		text-shadow:
			1px 1px 0 #4d1d08,
			2px 2px 0 #3f1807,
			3px 3px 0 #331305,
			4px 4px 0 #270e04,
			5px 5px 0 #1c0a03,
			6px 7px 0 #120602,
			0 12px 26px rgb(0 0 0 / 0.8);
	}
	/* the face: chrome on top, ember below, a bright bevel edge */
	.e-face {
		background: linear-gradient(176deg, #ffffff 6%, #ebe8e2 28%, #8e8b87 46%, #fff3d6 51%, #ffc15a 63%, #ff7a1a 80%, #e2401c 96%);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		-webkit-text-stroke: 1px rgb(255 255 255 / 0.55);
		filter: drop-shadow(0 0 22px rgb(255 150 70 / 0.5));
	}
	.ring {
		position: absolute;
		left: -15%;
		top: 50%;
		width: 130%;
		margin-top: -65%;
		aspect-ratio: 1;
		border-radius: 50%;
		border: 3px solid rgb(255 243 214 / 0.95);
		box-shadow: 0 0 30px 4px rgb(255 160 80 / 0.55), inset 0 0 24px rgb(255 160 80 / 0.45);
		opacity: 0;
	}
	.sparks {
		position: relative;
		width: 0;
		height: 0;
	}
	.sparks i {
		position: absolute;
		width: 7px;
		height: 3px;
		margin: -1.5px -3.5px;
		border-radius: 2px;
		background: #fff3d6;
		box-shadow: 0 0 10px 2px rgb(255 160 80 / 0.85);
		opacity: 0;
	}

	/* ---------- the scoreboard: round by round, the bars racing toward the middle ---------- */
	.board {
		display: grid;
		gap: clamp(0.4rem, 1svh, 0.75rem);
		padding: clamp(0.6rem, 1.4svh, 1rem) var(--pad-x) clamp(0.9rem, 2svh, 1.5rem);
		background: linear-gradient(90deg, rgb(var(--a) / 0.1), rgb(0 0 0 / 0.35) 40% 60%, rgb(var(--b) / 0.1));
	}
	.bh {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: center;
		gap: 0.25rem 0.75rem;
		text-align: center;
	}
	.bh-tag {
		padding: 0.2rem 0.7rem 0.25rem;
		font-family: var(--font-display);
		font-size: var(--fs-xs);
		font-weight: 900;
		font-style: italic;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-hi);
		background: linear-gradient(90deg, rgb(var(--a) / 0.5), rgb(0 0 0 / 0.6) 50%, rgb(var(--b) / 0.5));
		box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.18);
		clip-path: polygon(0.4rem 0, 100% 0, calc(100% - 0.4rem) 100%, 0 100%);
	}
	.ranked .bh-tag {
		color: #1a1205;
		background: linear-gradient(90deg, #ffc15a, #fff3d6, #ffc15a);
	}
	.bh-note {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.stats {
		margin: 0;
		display: grid;
		gap: clamp(0.3rem, 0.9svh, 0.6rem);
	}
	.row {
		display: grid;
		grid-template-columns: minmax(10.5rem, 0.45fr) minmax(0, 1fr) 16.5rem minmax(0, 1fr) minmax(10.5rem, 0.45fr);
		grid-template-areas: 'va ta lbl tb vb';
		align-items: center;
		column-gap: var(--sp-3);
	}
	/* the stat's name sits on the clash point */
	.lbl {
		grid-area: lbl;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		min-width: 0;
		padding: 0.3rem 0.8rem;
		border-radius: var(--r-pill);
		background: #0b0b0d;
		box-shadow:
			inset 0 0 0 1px rgb(255 255 255 / 0.14),
			-6px 0 16px -8px rgb(var(--a) / 0.9),
			6px 0 16px -8px rgb(var(--b) / 0.9);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.rn {
		color: #ffc15a;
		font-weight: 700;
	}
	.sv {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 0.35rem;
		min-width: 0;
		transition: opacity 0.4s;
	}
	.sv-a {
		--c: var(--a);
		--c-hi: var(--a-hi);
		grid-area: va;
	}
	.sv-b {
		--c: var(--b);
		--c-hi: var(--b-hi);
		grid-area: vb;
		justify-content: flex-end;
		text-align: right;
	}
	/* no verdict: both values glow in their maker's colour */
	.num {
		font-size: clamp(1.35rem, 0.8rem + 1.2vw, 2.1rem);
		font-weight: 760;
		line-height: 1.05;
		color: var(--text-hi);
		/* a drop-shadow, not a text-shadow: the odometer's drums would clip a text glow into boxes */
		filter: drop-shadow(0 0 10px rgb(var(--c) / 0.7));
	}
	.row:first-child .num {
		font-size: clamp(1.7rem, 0.9rem + 1.9vw, 2.9rem);
	}
	.u {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--c-hi);
	}
	.u.x {
		margin-left: -0.3rem;
		font-family: var(--font-display);
		font-size: 1.1em;
		font-weight: 800;
		color: var(--text-hi);
	}
	.sub {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.win {
		align-self: center;
		padding: 0.12rem 0.45rem;
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
		height: 0.55rem;
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
	/* each bar slides out of its own edge toward the clash point, a hot tip on its nose */
	.trk i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		transition: transform 0.9s var(--ease-spring);
	}
	.trk i::after {
		content: '';
		position: absolute;
		top: -2px;
		bottom: -2px;
		width: 0.9rem;
		border-radius: 50%;
		background: radial-gradient(closest-side, #fff, rgb(255 243 214 / 0.7) 40%, transparent);
	}
	.trk-a i {
		background: linear-gradient(90deg, rgb(var(--a) / 0.25), rgb(var(--a)) 65%, var(--a-hi) 92%, #fff3d6);
		box-shadow: 0 0 14px rgb(var(--a) / 0.6);
		transform: translate3d(calc((var(--fa) - 1) * 100%), 0, 0);
	}
	.trk-a i::after {
		right: -0.3rem;
	}
	.trk-b i {
		background: linear-gradient(270deg, rgb(var(--b) / 0.25), rgb(var(--b)) 65%, var(--b-hi) 92%, #fff3d6);
		box-shadow: 0 0 14px rgb(var(--b) / 0.6);
		transform: translate3d(calc((1 - var(--fb)) * 100%), 0, 0);
	}
	.trk-b i::after {
		left: -0.3rem;
	}
	/* a verdict: the winner's number goes gold, the other side steps back */
	.row.wa .sv-a .num,
	.row.wb .sv-b .num {
		filter: drop-shadow(0 0 12px rgb(255 214 150 / 0.75));
	}
	.row.wa .trk-a,
	.row.wb .trk-b {
		box-shadow: 0 0 18px rgb(255 214 150 / 0.45);
	}
	.row.wa :is(.sv-b, .trk-b),
	.row.wb :is(.sv-a, .trk-a) {
		opacity: 0.4;
	}

	/* title and lede on the left, the call to action on the right: one short band */
	.center {
		display: grid;
		grid-template-columns: auto auto;
		justify-content: center;
		align-items: center;
		gap: 0.15rem clamp(1.5rem, 4vw, 3.5rem);
		padding: clamp(0.75rem, 2svh, 1.5rem) var(--pad-x) clamp(1rem, 2.6svh, 2rem);
	}
	.center > :global(:last-child) {
		grid-column: 2;
		grid-row: 1 / span 2;
	}

	/* ================= the entrance (once), then calm ================= */
	@media (prefers-reduced-motion: no-preference) {
		/* waiting out of sight (view mode): the start frame */
		.pre .ft-a {
			opacity: 0;
			transform: translate3d(-70%, 0, 0);
		}
		.pre .ft-b {
			opacity: 0;
			transform: translate3d(70%, 0, 0);
		}
		.pre :is(.emb, .seam, .num, .win) {
			opacity: 0;
		}
		.pre .trk-a i {
			transform: translate3d(-101%, 0, 0);
		}
		.pre .trk-b i {
			transform: translate3d(101%, 0, 0);
		}

		.run .ft-a {
			animation: slam-a 0.46s cubic-bezier(0.2, 0.9, 0.3, 1.15) backwards;
		}
		.run .ft-b {
			animation: slam-b 0.46s cubic-bezier(0.2, 0.9, 0.3, 1.15) 0.04s backwards;
		}
		.run .ft-tilt {
			animation: smear 0.5s var(--ease-out) backwards;
		}
		.run .ft-b .ft-tilt {
			animation-delay: 0.04s;
		}
		.run .streaks {
			animation: streak 0.55s var(--ease-out) backwards;
		}
		.run .face {
			animation: shake 0.3s linear 0.42s;
		}
		.run .flash {
			animation: flash 0.5s var(--ease-out) 0.4s;
		}
		.run .emb :is(.e-plate, .e-txt) {
			animation: punch 0.42s cubic-bezier(0.3, 1.6, 0.5, 1) 0.34s backwards;
		}
		.run .e-core {
			animation: core-in 0.9s var(--ease-out) 0.38s backwards;
		}
		.run .ring {
			animation: wave 0.75s var(--ease-out) 0.42s backwards;
		}
		.run .ring.r2 {
			animation-delay: 0.52s;
			animation-duration: 0.9s;
		}
		.run .sparks i {
			animation: spark 0.7s var(--ease-out) calc(0.42s + var(--d)) backwards;
		}
		.run .seam {
			animation: crackle 0.7s linear 0.34s backwards;
		}
		.run .seam-v,
		.run .seam-h {
			transform-origin: 50% 0;
		}
		.run .trk-a i {
			animation: bar-a 1s var(--ease-out) calc(0.72s + var(--i) * 0.09s) backwards;
		}
		.run .trk-b i {
			animation: bar-b 1s var(--ease-out) calc(0.72s + var(--i) * 0.09s) backwards;
		}
		.run .num {
			animation: rise 0.3s var(--ease-out) 0.68s backwards;
		}
		.run .win {
			animation: win 0.45s cubic-bezier(0.3, 1.6, 0.5, 1) calc(1.7s + var(--i) * 0.09s) backwards;
		}
		/* idle: slow drift and sway, a rare faint spark, a calm ember */
		.rim {
			animation: drift 11s var(--ease-in-out) infinite alternate;
		}
		.ft-b .rim {
			animation-delay: -5.5s;
		}
		.beams i {
			animation: sway 14s var(--ease-in-out) infinite alternate;
		}
		.beams i:nth-child(2) {
			animation-delay: -4s;
			animation-duration: 17s;
		}
		.beams i:nth-child(3) {
			animation-delay: -9s;
			animation-duration: 12s;
		}
		.e-core {
			animation: ember 6s var(--ease-in-out) 1.4s infinite alternate;
		}
		.s-core,
		.s-arc {
			animation: flicker 7s linear 1.5s infinite;
		}
		.s-arc:nth-child(odd) {
			animation-delay: 4.2s;
		}
		.drips i {
			animation: drip var(--s) linear calc(2s + var(--k) * 2.7s) infinite;
		}
		/* offscreen: everything holds still */
		.off :is(*, *::before, *::after) {
			animation-play-state: paused !important;
		}
	}
	@keyframes slam-a {
		0% {
			opacity: 0;
			transform: translate3d(-75%, 0, 0);
		}
		20% {
			opacity: 1;
		}
		72% {
			transform: translate3d(2.5%, 0, 0);
		}
	}
	@keyframes slam-b {
		0% {
			opacity: 0;
			transform: translate3d(75%, 0, 0);
		}
		20% {
			opacity: 1;
		}
		72% {
			transform: translate3d(-2.5%, 0, 0);
		}
	}
	/* the card stretched along its path while it flies (reads as motion blur) */
	@keyframes smear {
		0% {
			transform: rotateY(var(--ry)) rotateZ(var(--rz)) skewX(calc(var(--in) * -14deg)) scaleX(1.25);
		}
		60% {
			transform: rotateY(var(--ry)) rotateZ(var(--rz)) skewX(calc(var(--in) * 4deg)) scaleX(0.97);
		}
	}
	@keyframes streak {
		0% {
			opacity: 0.9;
			transform: translate3d(calc(var(--in) * -30%), 0, 0) scaleX(1.4);
		}
		60% {
			opacity: 0.7;
		}
		100% {
			opacity: 0;
			transform: translate3d(calc(var(--in) * 10%), 0, 0) scaleX(0.4);
		}
	}
	@keyframes shake {
		0% {
			transform: translate3d(2px, -1px, 0);
		}
		25% {
			transform: translate3d(-2px, 1px, 0);
		}
		50% {
			transform: translate3d(1px, 1px, 0);
		}
		75% {
			transform: translate3d(-1px, -1px, 0);
		}
	}
	@keyframes flash {
		0% {
			opacity: 0;
		}
		18% {
			opacity: 0.85;
		}
		100% {
			opacity: 0;
		}
	}
	@keyframes punch {
		from {
			opacity: 0;
			transform: scale(2.8) rotate(-10deg);
		}
	}
	@keyframes core-in {
		from {
			opacity: 0;
			transform: scale(0.4);
		}
		30% {
			opacity: 1;
			transform: scale(1.35);
		}
	}
	@keyframes wave {
		0% {
			opacity: 0;
			transform: scale(0.3);
		}
		1% {
			opacity: 1;
			transform: scale(0.3);
		}
		100% {
			opacity: 0;
			transform: scale(3);
		}
	}
	@keyframes spark {
		0% {
			opacity: 0;
		}
		1% {
			opacity: 1;
			transform: translate3d(0, 0, 0) rotate(var(--ang)) scale(1.4);
		}
		to {
			opacity: 0;
			transform: translate3d(var(--dx), var(--dy), 0) rotate(var(--ang)) scale(0.3);
		}
	}
	@keyframes crackle {
		0% {
			opacity: 0;
			transform: scaleY(0);
		}
		10% {
			opacity: 1;
		}
		20% {
			opacity: 0.15;
		}
		32% {
			opacity: 1;
			transform: scaleY(1);
		}
		46% {
			opacity: 0.35;
		}
		60% {
			opacity: 1;
		}
		72% {
			opacity: 0.6;
		}
	}
	@keyframes bar-a {
		from {
			transform: translate3d(-101%, 0, 0);
		}
	}
	@keyframes bar-b {
		from {
			transform: translate3d(101%, 0, 0);
		}
	}
	@keyframes rise {
		from {
			opacity: 0;
			transform: translate3d(0, 0.3em, 0);
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
	@keyframes sway {
		from {
			transform: rotate(calc(var(--r) - 2.5deg));
		}
		to {
			transform: rotate(calc(var(--r) + 2.5deg));
		}
	}
	@keyframes ember {
		from {
			opacity: 0.8;
		}
		to {
			opacity: 1;
		}
	}
	@keyframes flicker {
		0%,
		90%,
		100% {
			opacity: 1;
		}
		91% {
			opacity: 0.35;
		}
		92.5% {
			opacity: 1;
		}
		93.5% {
			opacity: 0.5;
		}
	}
	@keyframes drip {
		0% {
			opacity: 0;
			transform: translate3d(0, 0, 0);
		}
		2% {
			opacity: 0.85;
		}
		9% {
			opacity: 0;
			transform: translate3d(calc(var(--k) * 6px - 6px), 3.5rem, 0);
		}
		100% {
			opacity: 0;
		}
	}

	/* ================= teaser: a little smaller ================= */
	.vs--teaser {
		--stage-h: clamp(9rem, 27svh, 15rem);
	}
	.vs--teaser .ft-nm {
		font-size: clamp(2rem, 0.8rem + 3.4vw, 4.25rem);
	}

	/* ================= narrow: A on top, B below, the VS on the seam between ================= */
	@media (max-width: 56rem) {
		.vs {
			--stage-h: clamp(6.5rem, 28vw, 11rem);
		}
		.face {
			grid-template-columns: minmax(0, 1fr);
			align-items: center;
			padding: var(--sp-4) var(--gutter) var(--sp-3);
		}
		.field-a {
			background:
				radial-gradient(90% 70% at 20% 0%, rgb(var(--a) / 0.6), transparent 70%),
				linear-gradient(180deg, rgb(var(--a) / 0.24), rgb(var(--a) / 0.06) 30%, rgb(var(--a) / 0.32) 50%);
			clip-path: polygon(0 0, 100% 0, 100% 56%, 0 45%);
		}
		.field-b {
			background:
				radial-gradient(90% 70% at 80% 100%, rgb(var(--b) / 0.6), transparent 70%),
				linear-gradient(0deg, rgb(var(--b) / 0.24), rgb(var(--b) / 0.06) 30%, rgb(var(--b) / 0.32) 50%);
			clip-path: polygon(0 45%, 100% 56%, 100% 100%, 0 100%);
		}
		.beams-a {
			inset: 0 0 50% 0;
		}
		.beams-b {
			inset: 50% 0 0 0;
		}
		.floor {
			display: none;
		}
		.seam-v {
			display: none;
		}
		.seam-h {
			display: block;
		}
		.drips {
			display: none;
		}
		/* each fighter: its photo on the outer side, its plate toward the middle */
		.ft {
			grid-template-columns: minmax(0, 1fr) auto;
			grid-template-areas: 'plate stage';
			align-items: center;
			column-gap: var(--sp-2);
			--ry: 10deg;
			--rz: -1deg;
		}
		.ft-b {
			grid-template-columns: auto minmax(0, 1fr);
			grid-template-areas: 'stage plate';
			--ry: -10deg;
			--rz: 1deg;
		}
		.ft-stage,
		.ft-b .ft-stage {
			margin: 0;
			max-width: 48vw;
			justify-self: center;
		}
		.ft-refl {
			display: none;
		}
		.plate {
			margin: 0;
		}
		.ft-a .plate {
			justify-items: start;
		}
		.ft-nm,
		.vs--teaser .ft-nm {
			font-size: clamp(1.6rem, 0.4rem + 6vw, 3rem);
		}
		.ft-wm {
			flex-wrap: wrap;
			gap: 0 0.5rem;
		}
		.core {
			margin-block: calc(-1 * var(--sp-3));
		}
		.emb {
			--e: clamp(5rem, 3rem + 8vw, 7rem);
		}
		.row {
			grid-template-columns: minmax(6.5rem, auto) minmax(0, 1fr) 13rem minmax(0, 1fr) minmax(6.5rem, auto);
		}
		.lbl {
			min-width: 0;
		}
	}
	/* phones: each stat's name on top, the two numbers side by side, the bars meeting under them */
	@media (max-width: 40rem) {
		.center {
			grid-template-columns: minmax(0, 1fr);
			justify-items: center;
			text-align: center;
			gap: var(--sp-2);
		}
		.center > :global(:last-child) {
			grid-column: auto;
			grid-row: auto;
		}
		.board {
			padding: var(--sp-3) var(--gutter) var(--sp-4);
		}
		.stats {
			gap: var(--sp-3);
		}
		.row {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
			grid-template-areas: 'lbl lbl' 'va vb' 'ta tb';
			column-gap: 0.3rem;
			row-gap: 0.25rem;
		}
		.lbl {
			justify-self: center;
			padding: 0.2rem 0.65rem;
		}
		.num,
		.row:first-child .num {
			font-size: clamp(1.3rem, 0.5rem + 4.6vw, 1.8rem);
		}
		.trk {
			height: 0.5rem;
		}
		.ft-sub {
			font-size: 0.66rem;
			white-space: normal;
		}
	}
</style>
