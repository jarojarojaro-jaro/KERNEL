<script lang="ts">
	/**
	 * Versus: two measured cards face to face on a shared model (each card's pick when they share
	 * none). The arena is lit in both makers' colours: card A's from the left, card B's from the
	 * right, meeting and blending at a white-hot seam where the VS stands (NVIDIA green against AMD
	 * red; two cards of one maker share its colour). Identity colour only: speeds keep the heat ramp.
	 * Each fighter has its render, name, our engine's measured speed and a bar on one shared scale;
	 * the bars grow toward the seam. The verdict under the arena is a speed-up only when both runs
	 * come from the same script and conditions.
	 *
	 * State lives in the query string (?a=…&b=…&m=…), read on the client: the prerendered page is the
	 * default pair. Changing a card replays its entrance (it slides in from its side, the VS lands);
	 * transforms and opacity only, nothing under reduced motion.
	 */
	import { afterNavigate, replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import HeatBar from '$lib/fx/HeatBar.svelte';
	import Odometer from '$lib/fx/Odometer.svelte';
	import RaceLanes, { type Lane } from '$lib/fx/RaceLanes.svelte';
	import { findCard, MODEL_INFO, variantLabel, words500, type ModelKey } from '$lib/data/measurements';
	import { fmtGB, fmtSec, fmtTps } from '$lib/format';
	import { cardsHref, currentLang, num } from '$lib/i18n';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import Choice from './Choice.svelte';
	import { cardsCopy } from './copy';
	import { duel, heatOf, MEASURED, roundTo, runOf, sharedModels } from './explorer';
	import GpuArt from './GpuArt.svelte';
	import Kinetic from './Kinetic.svelte';
	import Ratio from './Ratio.svelte';
	import TimeRace from './TimeRace.svelte';
	import { Play } from './play.svelte';
	import { VENDOR, vendorOf } from './vendor';

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].compare);
	const tc = $derived(cardsCopy[lang].card);
	const meta = $derived(cardsCopy[lang].meta);

	const IDS = MEASURED.map((e) => e.id);
	let a = $state('rtx-3090');
	let b = $state('rx-7900-xtx');
	let model = $state<ModelKey>('qwen38');
	let ready = $state(false);

	const A = $derived(findCard(a)!);
	const B = $derived(findCard(b)!);
	const shared = $derived(sharedModels(A, B));
	const runA = $derived(shared.length ? runOf(A, shared.includes(model) ? model : shared[0])! : runOf(A, A.pick.model)!);
	const runB = $derived(shared.length ? runOf(B, runA.model)! : runOf(B, B.pick.model)!);
	const dA = $derived(duel(runA));
	const dB = $derived(duel(runB));
	// Race only for the same model under the same script and conditions.
	const sameScript = $derived(shared.length > 0 && runA.sameHarness && runB.sameHarness && runA.metric.en === runB.metric.en);

	// Read the pair from the query once the router is up (replaceState needs it), on first load and
	// when the page is reached again through a link with another ?a=…&b=….
	afterNavigate(() => {
		const q = new URLSearchParams(location.search);
		const qa = q.get('a');
		const qb = q.get('b');
		const qm = q.get('m') as ModelKey | null;
		if (qa && IDS.includes(qa)) a = qa;
		if (qb && IDS.includes(qb)) b = qb;
		if (a === b) b = IDS.find((id) => id !== a)!;
		if (qm && qm in MODEL_INFO) model = qm;
		ready = true;
	});

	// Keep B different from A, and keep the URL shareable.
	$effect(() => {
		if (a === b) b = IDS.find((id) => id !== a)!;
	});
	$effect(() => {
		if (shared.length && !shared.includes(model)) model = shared.includes(A.pick.model) ? A.pick.model : shared[0];
	});
	$effect(() => {
		const qs = `?a=${a}&b=${b}&m=${runA.model}`;
		if (ready && location.search !== qs) replaceState(qs, {});
	});

	const sides = $derived(
		[
			{ key: 'a', card: A, run: runA, d: dA },
			{ key: 'b', card: B, run: runB, d: dB }
		].map((s) => ({ ...s, w: s.d ? words500(s.d.ours, 'pl') : null }))
	);
	const top = $derived(Math.max(...sides.map((s) => s.d?.ours.decode?.v ?? 0)) * 1.08);
	// Both lanes run our engine, so both are hot (heat means our speed).
	const lanes = $derived<Lane[]>(
		sides
			.filter((s) => s.d)
			.map((s) => ({ id: s.card.id, label: s.card.short, sub: `${MODEL_STYLE[s.run.model].short} ${s.run.quant}`, tps: s.d!.ours.decode!.v, hot: true }))
	);
	const raceKey = $derived(`${a}-${b}-${runA.model}`);
	/** Verdict: the faster card's decode ÷ the slower one's (same model and script only). */
	const lead = $derived.by(() => {
		if (!sameScript || !dA || !dB) return null;
		const [hi, lo] = dA.ours.decode!.v >= dB.ours.decode!.v ? [sides[0], sides[1]] : [sides[1], sides[0]];
		return { hi, lo, x: hi.d!.ours.decode!.v / lo.d!.ours.decode!.v };
	});
	/** The 500-word race plays in real time when it enters the view, and again when the pair changes. */
	const race500 = new Play(() => (Math.max(0, ...sides.map((s) => s.w?.v ?? 0)) + 1.5) * 1000);
	let seenPair = '';
	$effect(() => {
		const k = raceKey;
		if (seenPair && seenPair !== k) untrack(race500.replay);
		seenPair = k;
	});
	const cardOptions = (other: string) => MEASURED.map((e) => ({ value: e.id, label: e.card.short, sub: `${e.card.vramGB}\u00a0GB`, disabled: e.id === other }));

	/** The two makers' colours: A lights the arena from the left, B from the right. */
	const vs = $derived.by(() => {
		const va = VENDOR[vendorOf(A.vendor)];
		const vb = VENDOR[vendorOf(B.vendor)];
		return `--a:${va.rgb}; --a-hi:${va.hi}; --a-deep:${va.deep}; --b:${vb.rgb}; --b-hi:${vb.hi}; --b-deep:${vb.deep}`;
	});
	const NB = '\u00a0';
</script>

<svelte:head>
	<title>{meta.compareTitle}</title>
	<meta name="description" content={meta.compareDescription} />
	<meta property="og:title" content={meta.compareTitle} />
	<meta property="og:description" content={meta.compareDescription} />
</svelte:head>

<div class="amb" style={vs} aria-hidden="true"></div>

<section class="hero wrap" aria-labelledby="cmp-title">
	<a class="back mono" href={cardsHref(lang)}><span aria-hidden="true">←</span> {tc.back}</a>
	<p class="eyebrow">{t.eyebrow}</p>
	<Kinetic id="cmp-title" lines={[t.title]} class="giga hx-h" />
	<p class="lede">{t.lede}</p>
</section>

<section class="wrap arena-w" style={vs} aria-label="{A.name} {t.vs} {B.name}">
	<div class="arena" aria-live="polite">
		<span class="blade" aria-hidden="true"></span>
		{#each sides as s (s.key)}
			<div class="fighter f-{s.key}" class:win={lead?.hi.key === s.key}>
				{#key s.card.id}
					<div class="f-in">
						<p class="f-wm" class:upright={s.card.vendor !== 'nvidia' && s.card.vendor !== 'amd'}>{VENDOR[vendorOf(s.card.vendor)].name}</p>
						<div class="f-art" aria-hidden="true"><GpuArt label={s.card.short} vendor={s.card.vendor} vram={s.card.vramGB} heat={heatOf(s.d?.ratio)} live flat /></div>
						<h2 class="f-nm">{s.card.short}</h2>
						<p class="f-sub mono">{s.card.vramGB}{NB}GB · {num(s.card.bwGBs.v, lang, 0)}{NB}GB/s · {MODEL_STYLE[s.run.model].short} {s.run.quant}</p>
					</div>
				{/key}
				{#if s.d}
					<div class="f-score">
						<p class="f-v fig"><Odometer value={roundTo(s.d.ours.decode!.v, 1)} decimals={1} {lang} duration={1100} /><span class="u">t/s</span></p>
						<p class="f-lab">{variantLabel(s.run, s.run.ours)[lang]}</p>
						<span class="f-bar" style="--f:{(s.d.ours.decode!.v / top).toFixed(4)}" aria-hidden="true"><i></i></span>
					</div>
				{/if}
			</div>
		{/each}
		<div class="core" aria-hidden="true">
			{#key `${a}-${b}`}<span class="vs">VS</span>{/key}
		</div>
	</div>
	<p class="verdict">
		{#if lead}<Ratio value={lead.x} {lang} size="md" /> <span>{t.leadLine(lead.hi.card.short, lead.lo.card.short)}</span>{:else}<span class="nv">{shared.length ? t.noRace : t.noRaceModels}</span>{/if}
	</p>
</section>

<section class="wrap pick" style={vs} aria-label="{t.a}, {t.b}">
	<div class="pk pk-a"><Choice legend={t.a} name="cmp-a" bind:value={a} options={cardOptions(b)} tight /></div>
	{#if shared.length > 1}
		<div class="pk pk-m"><Choice legend={t.model} name="cmp-m" bind:value={model} options={shared.map((m) => ({ value: m, model: m, label: MODEL_STYLE[m].short }))} tight /></div>
	{/if}
	<div class="pk pk-b"><Choice legend={t.b} name="cmp-b" bind:value={b} options={cardOptions(a)} tight /></div>
	<p class="fine note">{shared.length ? t.quantNote : t.fallback}</p>
</section>

<section class="wrap duel" style={vs} aria-label="{A.name} {t.vs} {B.name}">
	{#each sides as s (s.key)}
		<article class="side side--{s.key}">
			<header>
				<p class="s-wm mono">{VENDOR[vendorOf(s.card.vendor)].name}</p>
				<h2 class="nm">{s.card.short}</h2>
			</header>
			{#if s.d}
				<HeatBar value={roundTo(s.d.before.decode!.v, 1)} max={top} label={t.before} cold {lang} />
				<dl class="facts">
					{#if s.w}
						<div>
							<dt>{t.words}</dt>
							<dd class="fig">{fmtSec(s.w.v, lang)}</dd>
						</div>
					{/if}
					{#if s.d.ours.ttft}<div><dt>{t.ttft}</dt><dd class="fig">{fmtSec(s.d.ours.ttft.v, lang)}</dd></div>{/if}
					{#if s.d.ours.vram}<div><dt>{t.vram}</dt><dd class="fig">{fmtGB(s.d.ours.vram.v, s.d.ours.vram.unit, lang).text} / {s.card.vramGB}{NB}GB</dd></div>{/if}
				</dl>
				<p class="foot"><a href={cardsHref(lang, `${s.card.id}/`)} class="more">{t.open} →</a></p>
				{#if !s.run.sameHarness}<p class="warn mono">{tc.scriptsWarn}</p>{/if}
			{/if}
		</article>
	{/each}
</section>

{#if sameScript && sides[0].w && sides[1].w}
	<section class="wrap words" aria-labelledby="cmp-words" use:race500.view>
		<h2 id="cmp-words" class="h hx-h">{t.words}</h2>
		<TimeRace
			lanes={sides.map((s) => ({ label: s.card.short, seconds: s.w!.v, hot: true }))}
			run={race500.on}
			runKey="{raceKey}-{race500.n}"
			{lang}
			labels={{ done: tc.wordsDone, saved: tc.wordsSaved }}
		/>
		<p class="fine">{runA.metric[lang]}</p>
	</section>
{/if}

<section class="wrap race" aria-labelledby="cmp-race">
	<h2 id="cmp-race" class="h hx-h">{t.race}</h2>
	{#if sameScript && lanes.length === 2}
		{#key raceKey}
			<RaceLanes {lanes} text={tc.raceText} {lang} loop={false} tacho="none" summary={lanes.map((l) => `${l.label}: ${fmtTps(l.tps, lang)} t/s`).join(', ')} />
		{/key}
		<p class="fine">{runA.metric[lang]}</p>
	{:else}
		<p class="fine">{shared.length ? t.noRace : t.noRaceModels}</p>
	{/if}
</section>

<style>
	/* the explorer's embers become the two makers' light: A from the left, B from the right */
	.amb {
		position: fixed;
		inset: 0;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(40vmax 34vmax at 0% 35%, rgb(var(--a) / 0.13), transparent 70%),
			radial-gradient(40vmax 34vmax at 100% 65%, rgb(var(--b) / 0.13), transparent 70%);
		will-change: transform;
	}
	:global(.explorer:has(.amb))::before {
		display: none;
	}
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.mono {
		font-family: var(--font-mono);
	}
	.hero {
		display: grid;
		gap: var(--sp-3);
		justify-items: start;
		padding: calc(4.25rem + clamp(1rem, 3vh, 2.25rem)) 0 clamp(1.25rem, 2.5vw, 2rem);
	}
	.hero :global(h1),
	.hero .lede,
	.hero .eyebrow {
		margin: 0;
	}
	.hero :global(h1) {
		font-size: var(--fs-display);
	}
	.back {
		display: inline-flex;
		gap: 0.5rem;
		align-items: center;
		min-height: 2.75rem;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		text-decoration: none;
	}
	.back:hover {
		color: var(--text-hi);
	}

	/* ---------- the arena: A's colour from the left, B's from the right, blended at the seam ---------- */
	.arena {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		color-scheme: dark;
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(3.5rem, 9vw, 9rem);
		padding: clamp(1.25rem, 3.5vw, 3rem) clamp(1rem, 3.5vw, 3rem) clamp(1.5rem, 3.5vw, 3rem);
		border-radius: var(--r-xl);
		color: var(--text);
		background:
			radial-gradient(22% 60% at 50% 46%, rgb(255 243 214 / 0.16), transparent 70%),
			radial-gradient(40% 70% at 50% 50%, color-mix(in oklab, rgb(var(--a) / 0.32), rgb(var(--b) / 0.32)), transparent 75%),
			radial-gradient(60% 95% at 0% 40%, rgb(var(--a) / 0.6), transparent 70%),
			radial-gradient(60% 95% at 100% 40%, rgb(var(--b) / 0.6), transparent 70%),
			linear-gradient(90deg, rgb(var(--a) / 0.34), rgb(var(--a) / 0.1) 36%, transparent 58%),
			linear-gradient(270deg, rgb(var(--b) / 0.34), rgb(var(--b) / 0.1) 36%, transparent 58%),
			linear-gradient(90deg, var(--a-deep), #070708 50%, var(--b-deep));
		box-shadow:
			inset 0 0 0 1px rgb(255 255 255 / 0.08),
			inset 1px 0 0 rgb(var(--a) / 0.6),
			inset -1px 0 0 rgb(var(--b) / 0.6),
			0 50px 90px -60px #000;
		overflow: hidden;
		isolation: isolate;
	}
	/* each maker's diagonal accent in its own outer corner */
	.arena::before,
	.arena::after {
		content: '';
		position: absolute;
		z-index: -1;
		top: -30%;
		width: 34%;
		height: 80%;
		pointer-events: none;
	}
	.arena::before {
		left: -8%;
		background: linear-gradient(65deg, transparent 0 52%, rgb(var(--a) / 0.4) 52% 55%, transparent 55% 60%, rgb(var(--a) / 0.18) 60% 61.5%, transparent 61.5%);
	}
	.arena::after {
		right: -8%;
		background: linear-gradient(115deg, transparent 0 38.5%, rgb(var(--b) / 0.18) 38.5% 40%, transparent 40% 45%, rgb(var(--b) / 0.4) 45% 48%, transparent 48%);
	}
	/* the seam: a slanted blade, A's colour on its left edge, white-hot core, B's on its right */
	.blade {
		position: absolute;
		z-index: -1;
		top: -15%;
		bottom: -15%;
		left: 50%;
		width: clamp(5px, 0.6vw, 9px);
		background: linear-gradient(90deg, rgb(var(--a)), #fff3d6 50%, rgb(var(--b)));
		box-shadow:
			-10px 0 40px 2px rgb(var(--a) / 0.55),
			10px 0 40px 2px rgb(var(--b) / 0.55),
			0 0 70px 10px rgb(255 243 214 / 0.18);
		transform: translateX(-50%) rotate(10deg);
		pointer-events: none;
	}
	.fighter {
		position: relative;
		display: grid;
		align-content: start;
		gap: var(--sp-4);
		min-width: 0;
	}
	.f-b {
		text-align: right;
	}
	.f-in {
		display: grid;
		gap: 0.3rem;
		min-width: 0;
	}
	.f-b .f-in {
		justify-items: end;
	}
	.f-wm {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1rem, 0.7rem + 1vw, 1.6rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 115%;
		letter-spacing: 0.02em;
		line-height: 1;
		color: var(--a-hi);
		text-shadow: 0 0 18px rgb(var(--a) / 0.7);
	}
	.f-b .f-wm {
		color: var(--b-hi);
		text-shadow: 0 0 18px rgb(var(--b) / 0.7);
	}
	.f-wm.upright {
		font-style: normal;
	}
	.f-art {
		width: min(100%, 22rem);
		margin-block: var(--sp-2);
		user-select: none;
	}
	.f-a .f-art :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--a) / 0.4), transparent);
	}
	.f-b .f-art :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--b) / 0.4), transparent);
	}
	.f-nm {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.1rem, 1rem + 4vw, 5rem);
		font-weight: 900;
		font-stretch: 115%;
		letter-spacing: -0.045em;
		line-height: 0.9;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.f-sub {
		margin: var(--sp-1) 0 0;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.f-score {
		display: grid;
		gap: 0.35rem;
	}
	.f-b .f-score {
		justify-items: end;
	}
	.f-v {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
		font-size: clamp(2rem, 1rem + 3.6vw, 4.25rem);
		line-height: 1;
		/* our engine's speed on both sides: hot; the faster one glows more */
		color: var(--heat-5);
		filter: drop-shadow(0 0 8px rgb(255 122 26 / 0.3));
	}
	.win .f-v {
		filter: drop-shadow(0 0 18px rgb(255 122 26 / 0.65));
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.f-lab {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	/* the bars grow toward the seam, on one shared scale */
	.f-bar {
		position: relative;
		display: block;
		width: 100%;
		height: 0.55rem;
		border-radius: 99px;
		background: rgb(255 255 255 / 0.07);
		overflow: hidden;
	}
	.f-bar i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3), var(--heat-4), var(--heat-5));
		box-shadow: 0 0 14px rgb(255 122 26 / 0.6);
		transform: scaleX(var(--f));
		transform-origin: left;
		transition: transform 0.9s var(--ease-spring);
	}
	.f-b .f-bar i {
		background: linear-gradient(270deg, var(--heat-2), var(--heat-3), var(--heat-4), var(--heat-5));
		transform-origin: right;
	}

	/* the VS at the seam */
	.core {
		position: absolute;
		left: 50%;
		top: clamp(5.5rem, 13vw, 11rem);
		transform: translate(-50%, -50%);
		pointer-events: none;
	}
	.vs {
		display: block;
		font-family: var(--font-display);
		font-size: clamp(3.4rem, 1.5rem + 7vw, 9.5rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 125%;
		letter-spacing: -0.05em;
		line-height: 0.8;
		padding: 0 0.1em;
		background: linear-gradient(90deg, var(--a-hi) 18%, #fff3d6 50%, var(--b-hi) 82%);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 20px rgb(255 243 214 / 0.35)) drop-shadow(0 6px 0 rgb(0 0 0 / 0.55));
	}

	/* entrances: each fighter from its side, the VS lands on a spring */
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .f-a .f-in {
			animation: from-left 0.9s var(--ease-spring) backwards;
		}
		:global(html.js) .f-b .f-in {
			animation: from-right 0.9s var(--ease-spring) backwards;
		}
		:global(html.js) .vs {
			animation: vs-land 0.75s var(--ease-spring) 0.15s backwards;
		}
		:global(html.js) .blade {
			animation: blade-in 0.9s var(--ease-out) backwards;
		}
		:global(html.js) .f-bar i {
			animation: bar-in 1.1s var(--ease-out) 0.2s backwards;
		}
	}
	@keyframes from-left {
		from {
			opacity: 0;
			transform: translate3d(-18%, 0, 0);
		}
	}
	@keyframes from-right {
		from {
			opacity: 0;
			transform: translate3d(18%, 0, 0);
		}
	}
	@keyframes vs-land {
		from {
			opacity: 0;
			transform: scale(1.9) rotate(-6deg);
		}
	}
	@keyframes blade-in {
		from {
			opacity: 0;
			transform: translateX(-50%) rotate(10deg) scaleY(0.2);
		}
	}
	@keyframes bar-in {
		from {
			transform: scaleX(0);
		}
	}

	.verdict {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: center;
		gap: 0.2rem 0.75rem;
		margin: var(--sp-4) auto 0;
		max-width: 52rem;
		text-align: center;
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.nv {
		color: var(--text-mute);
	}

	/* ---------- pickers: A on the left in A's colour, B on the right in B's ---------- */
	.pick {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: end;
		gap: var(--sp-4) var(--sp-6);
		padding-top: clamp(1.5rem, 3vw, 2.5rem);
	}
	.pk-a {
		grid-column: 1;
	}
	.pk-m {
		grid-column: 2;
		justify-self: center;
	}
	.pk-m :global(legend) {
		width: 100%;
		text-align: center;
	}
	.pk-b {
		grid-column: 3;
		justify-self: end;
	}
	.pk-b :global(legend) {
		text-align: right;
		width: 100%;
	}
	.pk-b :global(.caps) {
		justify-content: flex-end;
	}
	.pk-a :global(.cap.on) {
		border-color: rgb(var(--a));
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.1) inset,
			0 2px 0 #000,
			0 0 0 1px rgb(var(--a) / 0.4),
			0 10px 30px -12px rgb(var(--a) / 0.7);
	}
	.pk-a :global(.cap.on::before) {
		background: rgb(var(--a));
	}
	.pk-b :global(.cap.on) {
		border-color: rgb(var(--b));
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.1) inset,
			0 2px 0 #000,
			0 0 0 1px rgb(var(--b) / 0.4),
			0 10px 30px -12px rgb(var(--b) / 0.7);
	}
	.pk-b :global(.cap.on::before) {
		background: rgb(var(--b));
	}
	.note {
		grid-column: 1 / -1;
		justify-self: center;
		margin: 0;
		text-align: center;
	}

	/* ---------- details: each side washed in its maker's colour from its outer edge ---------- */
	.duel {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1px;
		margin-top: clamp(2rem, 4vw, 3rem);
		background: linear-gradient(180deg, transparent, #fff3d6 30%, #fff3d6 70%, transparent);
		border-radius: var(--r-xl);
		box-shadow: inset 1px 0 0 rgb(var(--a) / 0.5), inset -1px 0 0 rgb(var(--b) / 0.5), inset 0 0 0 1px var(--line);
		overflow: hidden;
	}
	.side {
		position: relative;
		display: grid;
		gap: var(--sp-5);
		align-content: start;
		padding: clamp(1.25rem, 3vw, 2.5rem);
		background: var(--bg-0);
	}
	.side--a {
		background:
			radial-gradient(70% 60% at 0% 0%, rgb(var(--a) / 0.16), transparent 70%),
			var(--bg-0);
	}
	.side--b {
		text-align: right;
		background:
			radial-gradient(70% 60% at 100% 0%, rgb(var(--b) / 0.16), transparent 70%),
			var(--bg-0);
	}
	.s-wm {
		margin: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.nm {
		margin: 0.2rem 0 0;
		font-family: var(--font-display);
		font-size: clamp(1.8rem, 1rem + 2.4vw, 3rem);
		font-weight: 850;
		font-stretch: 112%;
		letter-spacing: -0.04em;
		line-height: 0.95;
		color: var(--text-hi);
	}
	.facts {
		margin: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.facts div {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--sp-4);
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
	}
	.side--a .facts div {
		border-image: linear-gradient(90deg, rgb(var(--a) / 0.45), var(--line) 60%) 1;
	}
	.side--b .facts div {
		border-image: linear-gradient(270deg, rgb(var(--b) / 0.45), var(--line) 60%) 1;
	}
	.facts dt {
		color: var(--text-mute);
		font-size: var(--fs-sm);
		text-align: left;
	}
	.facts dd {
		margin: 0;
		color: var(--text-hi);
	}
	.foot {
		margin: 0;
	}
	.more {
		color: var(--text-hi);
		font-weight: 600;
		font-size: var(--fs-sm);
		text-decoration-color: var(--heat-3);
		transition: color var(--dur-2);
	}
	.more:hover {
		color: var(--hx-ink);
	}
	.warn {
		margin: 0;
		font-size: var(--fs-2xs);
		color: var(--text-hi);
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-sm);
		padding: 0.3rem 0.6rem;
		justify-self: start;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}
	.side--b .warn {
		justify-self: end;
	}
	.words {
		display: grid;
		gap: var(--sp-5);
		padding-top: var(--section-y);
	}
	.words .fine {
		margin: 0;
	}
	.race {
		display: grid;
		gap: var(--sp-5);
		padding: var(--section-y) 0;
	}
	.h {
		margin: 0;
		font-size: var(--fs-2xl);
		font-weight: 750;
		font-stretch: 108%;
		color: var(--text-hi);
	}
	.race .fine {
		margin: 0;
	}

	@media (max-width: 52rem) {
		.hero .lede {
			display: none;
		}
		.arena {
			gap: var(--sp-8);
		}
		.pick {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
			gap: var(--sp-4);
		}
		.pk-a,
		.pk-b {
			grid-row: 1;
		}
		.pk-b {
			grid-column: 2;
			justify-self: stretch;
		}
		.pk-m {
			grid-row: 2;
			grid-column: 1 / -1;
		}
		.duel {
			grid-template-columns: 1fr 1fr;
		}
	}
	@media (max-width: 40rem) {
		.arena {
			gap: var(--sp-4);
			padding: var(--sp-4) var(--sp-3) var(--sp-5);
		}
		.f-sub {
			display: none;
		}
		.f-art {
			margin-block: var(--sp-1);
		}
		.f-wm {
			font-size: 0.85rem;
		}
		.f-nm {
			font-size: clamp(1.2rem, 0.2rem + 5.4vw, 2.1rem);
		}
		.f-v {
			font-size: clamp(1.55rem, 0.6rem + 5vw, 2.2rem);
			gap: 0.25rem;
		}
		.f-lab {
			font-size: var(--fs-2xs);
		}
		.core {
			top: 4.6rem;
		}
		.vs {
			font-size: 2.6rem;
		}
		.pick :global(.tight .caps) {
			grid-template-columns: minmax(0, 1fr);
		}
		.duel {
			grid-template-columns: minmax(0, 1fr);
		}
		.side--b {
			text-align: left;
		}
		.side--b .warn {
			justify-self: start;
		}
		.side--b .facts div {
			border-image: linear-gradient(90deg, rgb(var(--b) / 0.45), var(--line) 60%) 1;
		}
		.side--b {
			background:
				radial-gradient(70% 60% at 0% 0%, rgb(var(--b) / 0.16), transparent 70%),
				var(--bg-0);
		}
	}
</style>
