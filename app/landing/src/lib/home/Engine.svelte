<script lang="ts">
	/**
	 * Jak to możliwe: the page's second big scene, full-bleed and cinematic, almost no prose.
	 * (a) The stack: six layers between the model (top) and the graphics card (bottom) light up in
	 *     sequence; a token pulse then runs down through them. The layers are tabs; one heat frame
	 *     glides from tab to tab (no per-tab jumps).
	 * (b) One close-up per layer, on the right: a before/after pair measured with only that layer
	 *     switched off and on (ENGINE_LAYERS; layer 02 = the nsys step profile of HERO_RUN). A giant
	 *     counter runs from the "before" value to the exact "after" value; two lanes show the same
	 *     stretch of time before/after (finished tokens, speculation steps, kernel launches merging
	 *     for 02, per-kernel submissions closing into one replayed PM4 tape for 05); secondary pairs
	 *     count along. Close-ups cross-fade.
	 * (c) Below, the whole engine end to end ("Razem"): measured upstream → ours on one card for
	 *     LFM2.5 (RX 7900 XTX) and Qwen (RTX 3090, HERO_RUN), with the multiplier. A six-step track
	 *     lights the layers seen so far; when the cycle reaches the last layer the totals flare. The
	 *     layers' gains are separate A/B measurements, so the bars never split the total by layer.
	 * The close-ups cycle on their own while the scene is on screen (a progress line runs on the
	 * active layer). Hovering the scene or keyboard focus in it pauses the cycle; hovering or clicking
	 * a layer, or the arrow keys on the tabs, switch to it. Counters are armed below the fold (start
	 * state, so the end values never flash first) and play on entry; reduced motion: final state, no
	 * cycling.
	 */
	import { onMount } from 'svelte';
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01, easeInOutCubic } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import { ENGINE_LAYERS as E, findCard, MODEL_INFO, type ModelKey, type Num } from '$lib/data/measurements';
	import { fmtRatio } from '$lib/format';
	import { num, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { copy } from '$lib/site/copy';
	import { fill, HERO_CARD, HERO_KERNELS, HERO_RUN, HERO_V } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].engine);
	const uid = $props.id();
	const K = HERO_KERNELS;

	// ---- (a) stack ----
	const stackTl = new Autoplay(1.8, '0px 0px -20% 0px', { arm: true });
	const ICONS = [
		'M6 6h8v8H6zM8 3v3M12 3v3M8 14v3M12 14v3M3 8h3M3 12h3M14 8h3M14 12h3',
		'M3 7h5v6H3zM10 7h7v6h-7z',
		'M3 10h10M10 6l4 4-4 4M17 4v12',
		'M4 5l5 5-5 5M10 5l5 5-5 5',
		'M4 5h12v3H4zM4 9.5h12v3H4zM4 14h12v2H4z',
		'M5 3v14M10 3v14M15 3v14M3.5 7h3M8.5 12h3M13.5 6h3'
	];

	// ---- (b) close-ups ----
	/** A measured before/after pair; `d` = decimals of each side as measured. */
	interface Pair {
		up: Num;
		ours: Num;
		d: [number, number];
		unit: string;
	}
	interface Zoom {
		card: string;
		model: ModelKey;
		main: Pair & { lower: boolean };
		extra: Pair[];
		/** Lanes: per-token or per-step period in ms (before, ours); 02 draws kernel launches, 05 the PM4 tape. */
		lanes: { kind: 'kernels' | 'pm4' } | { kind: 'tokens' | 'steps'; ms: [number, number] };
	}
	const pair = (n: readonly [Num, Num], d: number, unit: string, dOurs = d): Pair => ({ up: n[0], ours: n[1], d: [d, dOurs], unit });
	const perToken = (n: readonly [Num, Num]): [number, number] => [1000 / n[0].v, 1000 / n[1].v];
	const ZOOMS: Zoom[] = [
		{
			card: E.kernels.card,
			model: E.kernels.model,
			main: { ...pair(E.kernels.tg128, 1, 't/s'), lower: false },
			extra: [],
			lanes: { kind: 'tokens', ms: perToken(E.kernels.tg128) }
		},
		{
			card: HERO_CARD.id,
			model: HERO_RUN.model,
			main: { ...pair([K.up, K.ours], 0, ''), lower: true },
			extra: [pair(K.gapMs, 2, 'ms'), pair(K.gpuMs, 1, 'ms')],
			lanes: { kind: 'kernels' }
		},
		{
			card: E.sampler.card,
			model: E.sampler.model,
			main: { ...pair(E.sampler.decode, 1, 't/s'), lower: false },
			extra: [],
			lanes: { kind: 'tokens', ms: perToken(E.sampler.decode) }
		},
		{
			card: E.draft.card,
			model: E.draft.model,
			main: { ...pair(E.draft.msStep, 1, 'ms'), lower: true },
			extra: [pair(E.draft.decode, 1, 't/s'), pair(E.draft.tokStep, 2, '')],
			lanes: { kind: 'steps', ms: [E.draft.msStep[0].v, E.draft.msStep[1].v] }
		},
		{
			card: E.pm4.card,
			model: E.pm4.model,
			main: { ...pair(E.pm4.tg128, 1, 't/s'), lower: false },
			extra: [pair(E.pm4.qwen, 1, 't/s')],
			lanes: { kind: 'pm4' }
		},
		{
			card: E.profile.card,
			model: E.profile.model,
			main: { ...pair(E.profile.tg128, 1, 't/s'), lower: false },
			extra: [pair(E.profile.decode, 1, 't/s')],
			lanes: { kind: 'tokens', ms: perToken(E.profile.tg128) }
		}
	];
	const cardName = (id: string) => findCard(id)?.name ?? '';
	/** Figures inside running text (layer 05: the soak) come from the registry too. */
	const noteOf = (i: number) => fill(c.zooms[i].note, { req: num(E.pm4.requests.v, lang, 0), faults: E.pm4.faults.v });

	/** The change as a chip: fewer/shorter is the win for `lower` metrics; big jumps read as ×. */
	const pct = (x: number) => `${Math.round(x)}${lang === 'pl' ? '\u00a0' : ''}%`;
	const chip = (p: Pair & { lower: boolean }) => {
		const r = p.ours.v / p.up.v;
		if (p.lower) return `−${pct((1 - r) * 100)}`;
		return r >= 1.5 ? fmtRatio(r, lang) : `+${pct((r - 1) * 100)}`;
	};

	const zoomTl = new Autoplay(1.9, '0px 0px -15% 0px', { arm: true });
	/** Progress of the active close-up: monotonic (no overshoot), exactly 1 at rest. */
	const f = $derived(easeInOutCubic(clamp01((zoomTl.p - 0.06) / 0.86)));
	const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
	/** A counter's value at progress k: before → after, and the exact measured "after" at rest. */
	const at = (p: Pair, k: number) => (k >= 1 ? p.ours.v : lerp(p.up.v, p.ours.v, k));
	const show = (p: Pair, k: number) => num(at(p, k), lang, p.d[1]);
	/**
	 * Width that fits every value a counter passes through (tabular figures): held while it counts so
	 * nothing beside it moves, released at rest so the gain chip (hidden until then) sits tight.
	 */
	const width = (p: Pair) => Math.max(num(p.up.v, lang, p.d[1]).length, num(p.ours.v, lang, p.d[1]).length);

	// layer 02 lanes: one token's kernel launches, zoomed into the first N upstream launches
	const N = 72;
	const G = Math.round((N * K.ours.v) / K.up.v);
	const wU = K.gpuMs[0].v / K.up.v;
	const gU = K.gapMs[0].v / K.up.v;
	const wO = K.gpuMs[1].v / K.ours.v;
	const gO = K.gapMs[1].v / K.ours.v;
	const T = N * (wU + gU);
	const sx = (ms: number) => (ms / T) * 1000;
	/** Per upstream launch i: its own rect and its share of our merged kernel (group g). */
	const kbars = Array.from({ length: N }, (_, i) => {
		const g = Math.floor((i * G) / N);
		const first = Math.ceil((g * N) / G);
		const size = Math.ceil(((g + 1) * N) / G) - first;
		const k = i - first;
		return { x0: sx(i * (wU + gU)), w0: sx(wU), x1: sx(g * (wO + gO) + (k * wO) / size), w1: sx(wO / size) };
	});

	/**
	 * Layer 05 lanes: the same kernels submitted one by one (a packet each, the gap = the per-launch
	 * submission cost) vs replayed from one PM4 tape. Our lane's total length is the upstream one
	 * scaled by the measured tg128 ratio, so the tape ends where the measurement says.
	 */
	const PM = 16;
	const pmW = 40;
	const pmStep = 1000 / PM;
	const pmStepO = pmStep * (E.pm4.tg128[0].v / E.pm4.tg128[1].v);
	const pmBars = Array.from({ length: PM }, (_, i) => ({ x0: i * pmStep, x1: i * pmStepO }));
	const pmTape = (PM - 1) * pmStepO + pmW;

	/** The same stretch of time on both lanes: our lane gets n periods, the "before" lane what fits. */
	function marks(kind: 'tokens' | 'steps', ms: [number, number]) {
		const n = kind === 'steps' ? 6 : Math.max(16, Math.ceil((1.15 * ms[0]) / ms[1]));
		const t = n * ms[1];
		const lane = (P: number) => {
			const out: { x: number; w: number }[] = [];
			if (kind === 'steps') for (let a = 0; a < t; a += P) out.push({ x: (a / t) * 1000, w: (P / t) * 1000 - 8 });
			else {
				const w = Math.min(10, ((0.4 * ms[1]) / t) * 1000);
				for (let a = P; a <= t + 1e-9; a += P) out.push({ x: (a / t) * 1000 - w, w });
			}
			return out;
		};
		return [lane(ms[0]), lane(ms[1])];
	}
	const MARKS = ZOOMS.map((z) => (z.lanes.kind === 'tokens' || z.lanes.kind === 'steps' ? marks(z.lanes.kind, z.lanes.ms) : null));

	// ---- (c) the whole engine ----
	const TOTALS = [
		{ card: E.total.card, model: E.total.model, up: E.total.tg128[0], ours: E.total.tg128[1] },
		{ card: HERO_CARD.id, model: HERO_RUN.model, up: HERO_V.a0.decode!, ours: HERO_V.a2.decode! }
	];
	const totalTl = new Autoplay(1.6, '0px 0px -10% 0px', { arm: true });
	const tk = $derived(easeInOutCubic(clamp01(totalTl.p / 0.9)));

	// ---- tabs: auto-cycle, hover, click, keys ----
	const CYCLE = 7;
	let active = $state(0);
	/** Layers seen so far in this lap (the running track in "Razem"). */
	let seenUpTo = $state(0);
	let tabs: HTMLButtonElement[] = $state([]);
	let slabsEl: HTMLDivElement | undefined = $state();
	/** The gliding frame over the active tab (client only; measured from the tab's box). */
	let frame = $state<{ x: number; y: number; w: number; h: number } | null>(null);
	let hoverTimer: ReturnType<typeof setTimeout> | undefined;
	function place() {
		const t = tabs[active];
		if (t) frame = { x: t.offsetLeft, y: t.offsetTop, w: t.offsetWidth, h: t.offsetHeight };
	}
	$effect(() => {
		void active;
		place();
	});
	onMount(() => {
		if (!slabsEl) return;
		const ro = new ResizeObserver(place);
		ro.observe(slabsEl);
		return () => ro.disconnect();
	});
	function pick(i: number) {
		clearTimeout(hoverTimer);
		if (i === active) return;
		active = i;
		seenUpTo = i === 0 ? 0 : Math.max(seenUpTo, i);
		zoomTl.replay();
	}
	const next = () => pick((active + 1) % ZOOMS.length);
	function hover(e: PointerEvent, i: number) {
		if (e.pointerType !== 'mouse') return;
		clearTimeout(hoverTimer);
		hoverTimer = setTimeout(() => pick(i), 160);
	}
	function onKey(e: KeyboardEvent) {
		const n = ZOOMS.length;
		const i = { ArrowDown: active + 1, ArrowRight: active + 1, ArrowUp: active - 1 + n, ArrowLeft: active - 1 + n, Home: 0, End: n - 1 }[e.key];
		if (i === undefined) return;
		e.preventDefault();
		pick(i % n);
		tabs[i % n]?.focus();
	}

	/** Title as two lines: the claim (bone) and the payoff (heat). */
	const titleParts = $derived(c.title.split('|'));
</script>

<section id="engine" class="engine heat-top" aria-labelledby="engine-title">
	<div class="atmo" aria-hidden="true"></div>
	<div class="inner">
		<h2 id="engine-title" class="statement"><span class="t1">{titleParts[0]}</span> <span class="t2"><span class="ul">{titleParts[1] ?? ''}</span></span></h2>

		<div class="grid">
			<!-- (a) the stack: model → card, lit layer by layer; every layer is a tab -->
			<div class="stack" use:stackTl.view>
				<p class="cap cap--model"><span class="ci" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="M10 2l7 4v8l-7 4-7-4V6zM3 6l7 4 7-4M10 10v8" /></svg></span>{c.model}</p>
				<div class="pulse" class:run={stackTl.p >= 1} aria-hidden="true"></div>
				<div class="slabs" role="tablist" aria-label={c.pick} aria-orientation="vertical" tabindex="-1" onkeydown={onKey} bind:this={slabsEl}>
					{#if frame}<span class="frame" style="transform: translate3d({frame.x}px, {frame.y}px, 0); width: {frame.w}px; height: {frame.h}px" aria-hidden="true"></span>{/if}
					{#each c.layers as [name, sub], i (i)}
						<button
							bind:this={tabs[i]}
							type="button"
							role="tab"
							id="{uid}-tab-{i}"
							aria-controls="{uid}-panel-{i}"
							aria-selected={i === active}
							tabindex={i === active ? 0 : -1}
							class="slab"
							class:in={stackTl.p >= (i + 1) / 7}
							class:on={i === active}
							class:framed={!!frame}
							style="--i:{i}"
							onclick={() => pick(i)}
							onpointerenter={(e) => hover(e, i)}
							onpointerleave={() => clearTimeout(hoverTimer)}
						>
							<span class="si" aria-hidden="true"><svg viewBox="0 0 20 20"><path d={ICONS[i]} /></svg></span>
							<span class="sn">{name}</span>
							<span class="ss">{sub}</span>
							<span class="sk" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
							{#if i === active && zoomTl.inView}<i class="prog" style="--cycle:{CYCLE}s" onanimationend={next} aria-hidden="true"></i>{/if}
						</button>
					{/each}
				</div>
				<p class="cap cap--card"><span class="ci" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="M2 6h16v9H2zM5 15v2M8 15v2M11 15v2M14 15v2M6 9h4v3H6z" /></svg></span>{c.card}</p>
			</div>

			<!-- (b) one close-up per layer, stacked in one cell (the tallest sets the height), cross-faded -->
			<div class="zooms" use:zoomTl.view>
				{#each ZOOMS as z, i (i)}
					{@const on = i === active}
					{@const k = on ? f : 1}
					{@const zc = c.zooms[i]}
					<div class="close" class:on id="{uid}-panel-{i}" role="tabpanel" aria-labelledby="{uid}-tab-{i}" inert={!on}>
						<p class="zh">
							<span class="zk">{String(i + 1).padStart(2, '0')} · {c.zoom}</span>
							<span class="zm"><ModelMark model={z.model} size="0.7em" /> {MODEL_INFO[z.model].name}{' · '}{cardName(z.card)}</span>
							<Replay {lang} onclick={zoomTl.replay} disabled={on && zoomTl.playing} />
						</p>
						<p class="giant" aria-hidden="true">
							<span class="g-up">{num(z.main.up.v, lang, z.main.d[0])}</span>
							<span class="g-ar">→</span>
							<span class="g-ours" style:min-width={k < 1 ? `${width(z.main)}ch` : null}>{show(z.main, k)}</span>
							<span class="g-cut" class:shown={k >= 1}>{chip(z.main)}</span>
						</p>
						<p class="g-cap">{zc.metric}</p>

						<div class="lanes" aria-hidden="true">
							{#each [0, 1] as lane (lane)}
								<div class="lane" class:ours={lane === 1}>
									<span class="ln">{zc.lanes[lane]}</span>
									<svg class="track" viewBox="0 0 1000 40" preserveAspectRatio="none" style={MARKS[i] ? `clip-path: inset(0 ${((1 - k) * 100).toFixed(2)}% 0 0)` : undefined}>
										{#if MARKS[i]}
											{#each MARKS[i]![lane] as m, j (j)}<rect x={m.x} y="4" width={m.w} height="32" rx="2" />{/each}
										{:else if z.lanes.kind === 'pm4'}
											{#if lane === 1}<rect class="tape" x="0" y="1" width={pmTape} height="38" rx="5" style="opacity:{k}" />{/if}
											{#each pmBars as b, j (j)}<rect x={lane === 0 ? b.x0 : lerp(b.x0, b.x1, k)} y="6" width={pmW} height="28" rx="3" />{/each}
										{:else}
											{#each kbars as b, j (j)}
												{#if lane === 0}
													<rect x={b.x0} y="4" width={b.w0} height="32" rx="1" />
												{:else}
													<rect x={lerp(b.x0, b.x1, k)} y="4" width={lerp(b.w0, b.w1, k) + (k > 0.98 ? 0.6 : 0)} height="32" rx="1" />
												{/if}
											{/each}
										{/if}
									</svg>
								</div>
							{/each}
							<p class="lcap">{zc.lane}</p>
						</div>

						{#if z.extra.length}
							<dl class="pair">
								{#each z.extra as p, j (j)}
									<div><dt>{zc.extra[j]}</dt><dd><span class="pu">{num(p.up.v, lang, p.d[0])}</span> → <b style:min-width={k < 1 ? `${width(p)}ch` : null}>{show(p, k)}</b>{#if p.unit}&nbsp;{p.unit}{/if}</dd></div>
								{/each}
							</dl>
						{/if}
						<p class="znote">{noteOf(i)}</p>
						<p class="sr-only">
							{c.layers[i][0]}, {zc.metric}: {zc.lanes[0]} {num(z.main.up.v, lang, z.main.d[0])}{z.main.unit ? ` ${z.main.unit}` : ''}, {zc.lanes[1]} {num(z.main.ours.v, lang, z.main.d[1])}{z.main.unit ? ` ${z.main.unit}` : ''} ({chip(z.main)}).
							{#each z.extra as p, j (j)}{zc.extra[j]}: {num(p.up.v, lang, p.d[0])} → {num(p.ours.v, lang, p.d[1])}{p.unit ? ` ${p.unit}` : ''}. {/each}
						</p>
					</div>
				{/each}
			</div>
		</div>

		<!-- (c) the whole engine, end to end: the result that sticks -->
		<div class="whole" class:landed={seenUpTo === ZOOMS.length - 1} use:totalTl.view>
			<div class="wh">
				<p class="wt">{c.total}</p>
				<ol class="track6" aria-hidden="true">
					{#each ZOOMS as _, i (i)}<li class:lit={i <= seenUpTo} class:now={i === active}>{String(i + 1).padStart(2, '0')}</li>{/each}
				</ol>
			</div>
			{#each TOTALS as t, i (i)}
				{@const r = t.ours.v / t.up.v}
				<div class="trow" style="--u:{t.up.v / t.ours.v}; --k:{tk}">
					<p class="tm"><ModelMark model={t.model} size="0.75em" /> <b>{MODEL_INFO[t.model].name}</b> · {cardName(t.card)}</p>
					<div class="tbar" aria-hidden="true">
						<span class="tb-ours"></span>
						<span class="tb-up"></span>
					</div>
					<p class="tv">
						<span class="pu">{num(t.up.v, lang, 1)}</span> → <b>{num(tk >= 1 ? t.ours.v : lerp(t.up.v, t.ours.v, tk), lang, 1)}</b>&nbsp;t/s
						<span class="tx" class:shown={tk >= 1}>{fmtRatio(r, lang)}</span>
					</p>
					<p class="tn">{c.totalRows[i]}</p>
				</div>
			{/each}
			<p class="wnote">{c.totalNote}</p>
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
		color: var(--text-hi);
	}
	/* heat in the underline, not the letters (gradient headlines are for the hero and the finale) */
	.ul {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 45%, var(--heat-4)) no-repeat 0 92% / 100% 0.07em;
		-webkit-box-decoration-break: clone;
		box-decoration-break: clone;
		padding-bottom: 0.06em;
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
		position: relative;
		display: grid;
		gap: 0.5rem;
	}
	.slabs:focus {
		outline: none;
	}
	/* every layer is a tab: dim until the stack lights it, hot when its close-up is shown */
	.slab {
		position: relative;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		grid-template-areas: 'icon name key' 'icon sub key';
		align-items: center;
		column-gap: 1rem;
		width: 100%;
		padding: 0.85rem 1.1rem;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: linear-gradient(180deg, rgb(255 255 255 / 0.04), rgb(255 255 255 / 0.01)), var(--bg-1);
		box-shadow: 0 12px 26px -16px rgb(0 0 0 / 0.9);
		font: inherit;
		color: inherit;
		text-align: left;
		cursor: pointer;
		overflow: hidden;
		filter: brightness(0.55);
		transition:
			filter 0.5s var(--ease-out),
			border-color 0.35s ease,
			background-color 0.35s ease;
	}
	.slab.in {
		filter: none;
		border-color: rgb(255 122 26 / 0.22);
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
	.slab:hover {
		border-color: rgb(255 122 26 / 0.45);
		background-color: var(--bg-2);
	}
	/* before hydration (no gliding frame yet) the active tab carries its own frame */
	.slab.on:not(.framed) {
		border-color: var(--heat-3);
		box-shadow:
			0 0 0 1px rgb(255 122 26 / 0.45),
			0 0 44px -6px rgb(255 122 26 / 0.8);
	}
	/* one heat frame glides from tab to tab: position and size ease, nothing jumps */
	.frame {
		position: absolute;
		top: 0;
		left: 0;
		z-index: 1;
		border: 1px solid var(--heat-3);
		border-radius: var(--r-md);
		background: linear-gradient(90deg, rgb(255 122 26 / 0.16), transparent 72%);
		box-shadow:
			0 0 0 1px rgb(255 122 26 / 0.35),
			0 0 44px -6px rgb(255 122 26 / 0.75);
		pointer-events: none;
		transition:
			transform 0.6s var(--ease-out),
			width 0.6s var(--ease-out),
			height 0.6s var(--ease-out);
	}
	.slab:focus-visible {
		outline: 2px solid var(--heat-4);
		outline-offset: 3px;
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
		transition:
			background-color 0.45s ease,
			color 0.45s ease;
	}
	.slab.on .si {
		background: var(--heat-3);
		color: #1a0b03;
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
	.sn,
	.sk {
		transition: color 0.45s ease;
	}
	.sk {
		grid-area: key;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.slab.on .sk {
		color: var(--heat-4);
	}
	/* the auto-cycle timer: a heat line under the active layer; hover or keyboard focus holds it */
	.prog {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 2px;
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 8px rgb(255 122 26 / 0.8);
		transform-origin: 0 50%;
		animation: prog var(--cycle) linear forwards;
	}
	.grid:hover .prog,
	.grid:has(:focus-visible) .prog {
		animation-play-state: paused;
	}
	@keyframes prog {
		from {
			transform: scaleX(0);
		}
		to {
			transform: scaleX(1);
		}
	}

	/* ---- (b) close-ups: stacked in one grid cell, the active one fades in ---- */
	.zooms {
		display: grid;
		min-width: 0;
	}
	.close {
		grid-area: 1 / 1;
		position: relative;
		display: grid;
		align-content: start;
		gap: 0.6rem;
		min-width: 0;
		padding: clamp(1.1rem, 0.6rem + 2vw, 2.2rem);
		border: 1px solid rgb(255 122 26 / 0.28);
		border-radius: 18px;
		background:
			radial-gradient(70% 60% at 85% 0%, rgb(255 122 26 / 0.14), transparent 70%),
			linear-gradient(180deg, rgb(255 255 255 / 0.03), transparent 40%),
			#0c0a09;
		box-shadow:
			0 30px 60px -30px rgb(0 0 0 / 0.9),
			0 0 60px -30px rgb(255 122 26 / 0.6);
		visibility: hidden;
		opacity: 0;
		transform: translate3d(0, -0.4rem, 0) scale(0.985);
		transition:
			opacity 0.45s ease,
			transform 0.6s var(--ease-out),
			visibility 0s linear 0.45s;
	}
	/* cross-fade: the incoming close-up rises in while the outgoing one fades over it */
	.close.on {
		visibility: visible;
		opacity: 1;
		transform: none;
		transition:
			opacity 0.55s ease 0.06s,
			transform 0.7s var(--ease-out) 0.06s,
			visibility 0s;
	}
	.zh {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.8rem;
	}
	.zk {
		padding: 0.15rem 0.5rem;
		border: 1px solid var(--heat-3);
		border-radius: 3px;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--heat-4);
		white-space: nowrap;
	}
	.zm {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		margin-right: auto;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.giant {
		margin: 0.5rem 0 0;
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0 0.22em;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(3.2rem, 1.4rem + 5.2vw, 7.4rem);
		font-weight: 800;
		line-height: 0.95;
		letter-spacing: -0.045em;
		white-space: nowrap;
	}
	/* "before" small and cold, ours huge and white-hot */
	.g-up {
		font-size: 0.42em;
		font-weight: 650;
		color: var(--before);
		letter-spacing: -0.02em;
	}
	.g-ar {
		font-size: 0.32em;
		color: var(--text-mute);
	}
	.g-ours {
		display: inline-block;
		color: var(--heat-5);
		text-shadow:
			0 0 18px rgb(255 193 90 / 0.45),
			0 0 48px rgb(255 122 26 / 0.45);
	}
	/* the gain lands when the counter does (it never counts through "−0 %") */
	.g-cut {
		align-self: center;
		padding: 0.32em 0.65em 0.26em;
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		color: #140a04;
		font-size: 0.22em;
		font-weight: 800;
		letter-spacing: -0.01em;
		line-height: 1;
		box-shadow: 0 0 22px rgb(255 122 26 / 0.55);
		opacity: 0;
		transform: scale(0.6);
		transition:
			opacity 0.25s,
			transform 0.5s var(--ease-spring);
	}
	.g-cut.shown {
		opacity: 1;
		transform: none;
	}
	.g-cap {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text);
	}
	/* the same stretch of time, before vs ours */
	.lanes {
		display: grid;
		gap: 0.45rem;
		margin-top: 0.7rem;
		padding: 0.8rem 0.9rem 0.6rem;
		border-radius: 12px;
		background: rgb(255 255 255 / 0.025);
		box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.06);
	}
	.lane {
		display: grid;
		grid-template-columns: 8.5rem minmax(0, 1fr);
		align-items: center;
		gap: 0.8rem;
	}
	.ln {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--before);
	}
	.ours .ln {
		color: var(--heat-4);
	}
	.track {
		display: block;
		width: 100%;
		height: clamp(1.8rem, 1.4rem + 1vw, 2.5rem);
		background: radial-gradient(circle, rgb(125 135 148 / 0.45) 1px, transparent 1.4px) 0 50% / 7px 7px;
	}
	.track rect {
		fill: rgb(125 135 148 / 0.75);
	}
	.ours .track rect {
		fill: var(--heat-4);
	}
	.ours .track {
		filter: drop-shadow(0 0 6px rgb(255 122 26 / 0.6));
	}
	/* layer 05: the replayed PM4 tape the packets close into */
	.ours .track rect.tape {
		fill: rgb(255 122 26 / 0.14);
		stroke: var(--heat-3);
		stroke-width: 1.5;
		vector-effect: non-scaling-stroke;
	}
	.lcap {
		margin: 0.15rem 0 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.pair {
		margin: 0.6rem 0 0;
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
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(1.3rem, 1rem + 0.9vw, 1.9rem);
		font-weight: 700;
		color: var(--text);
		white-space: nowrap;
	}
	.pu {
		color: var(--before);
	}
	.pair b {
		display: inline-block;
		color: var(--heat-4);
	}
	.znote {
		margin: 0.4rem 0 0;
		max-width: 62ch;
		font-size: var(--fs-sm);
		line-height: 1.5;
		color: var(--text-mute);
	}

	/* ---- (c) the whole engine ---- */
	.whole {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1.2rem clamp(1.5rem, 4vw, 4rem);
		padding: clamp(1.2rem, 0.6rem + 2vw, 2rem);
		border-radius: 18px;
		background:
			radial-gradient(60% 120% at 100% 50%, rgb(255 122 26 / 0.12), transparent 70%),
			rgb(255 255 255 / 0.02);
		box-shadow: inset 0 0 0 1px rgb(255 122 26 / 0.22);
	}
	.wh {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.6rem 1.5rem;
	}
	.wt {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.3rem, 1rem + 1vw, 2rem);
		font-weight: 800;
		letter-spacing: -0.02em;
		color: var(--text-hi);
	}
	/* the running track: layers seen in this lap light up toward the total */
	.track6 {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		gap: 0.3rem;
	}
	.track6 li {
		min-width: 2.4rem;
		padding: 0.3rem 0.45rem 0.25rem;
		border-radius: 4px;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-align: center;
		color: var(--text-mute);
		background: rgb(255 255 255 / 0.05);
		transition:
			background-color 0.5s ease,
			color 0.5s ease,
			box-shadow 0.5s ease;
	}
	.track6 li.lit {
		color: #1a0b03;
		background: var(--heat-3);
	}
	.track6 li.now {
		background: var(--heat-4);
		box-shadow: 0 0 16px rgb(255 122 26 / 0.7);
	}
	.trow {
		display: grid;
		gap: 0.5rem;
		align-content: start;
		min-width: 0;
	}
	.tm {
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.tm b {
		font-weight: 600;
		color: var(--text-hi);
	}
	/* ours as the full bar, upstream as the cold part of it */
	.tbar {
		position: relative;
		height: 0.9rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.05);
		overflow: hidden;
	}
	.tb-ours,
	.tb-up {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		transform-origin: 0 50%;
	}
	.tb-ours {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 18px rgb(255 122 26 / 0.6);
		transform: scaleX(calc(var(--u) + (1 - var(--u)) * var(--k)));
	}
	.tb-up {
		background: linear-gradient(90deg, #2a3038, var(--before));
		transform: scaleX(var(--u));
	}
	.tv {
		margin: 0;
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0.2rem 0.4rem;
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: clamp(1.3rem, 1rem + 1vw, 2rem);
		font-weight: 750;
		color: var(--text);
		white-space: nowrap;
	}
	.tv b {
		color: var(--heat-5);
		text-shadow: 0 0 18px rgb(255 122 26 / 0.5);
	}
	.tx {
		margin-left: 0.4rem;
		padding: 0.2em 0.55em 0.15em;
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		color: #140a04;
		font-size: 0.8em;
		font-weight: 820;
		box-shadow: 0 0 22px rgb(255 122 26 / 0.5);
		opacity: 0;
		transform: scale(0.7);
		transition:
			opacity 0.3s ease,
			transform 0.6s var(--ease-spring);
	}
	.tx.shown {
		opacity: 1;
		transform: none;
	}
	/* the lap reached the last layer: the totals flare once */
	@media (prefers-reduced-motion: no-preference) {
		.whole.landed .tx {
			animation: land 1.2s var(--ease-out);
		}
	}
	@keyframes land {
		25% {
			box-shadow:
				0 0 0 3px rgb(255 243 214 / 0.6),
				0 0 46px rgb(255 122 26 / 0.95);
			transform: scale(1.12);
		}
	}
	.tn {
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.wnote {
		grid-column: 1 / -1;
		margin: 0;
		max-width: 80ch;
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}

	@media (max-width: 1000px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.whole {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	/* phones: the six layers as a 2 × 3 grid of compact tabs above the close-up */
	@media (max-width: 640px) {
		.pulse,
		.cap {
			display: none;
		}
		.slabs {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
			gap: 0.4rem;
		}
		.slab {
			grid-template-areas: 'icon name' 'icon key';
			grid-template-columns: auto minmax(0, 1fr);
			column-gap: 0.6rem;
			padding: 0.55rem 0.65rem;
		}
		.si {
			width: 1.9rem;
			height: 1.9rem;
		}
		.sn {
			font-size: var(--fs-xs);
			line-height: 1.2;
		}
		.ss {
			display: none;
		}
		.lane {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.2rem;
		}
		.zk {
			margin-right: auto;
		}
		.zm {
			order: 3;
			flex-basis: 100%;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.slab,
		.close,
		.g-cut,
		.frame,
		.tx {
			transition: none;
		}
		.slab.in {
			animation: none;
		}
	}
</style>
