<script lang="ts">
	import { MODEL_STYLE } from '$lib/modelStyle';
	/**
	 * Two measured cards side by side on a shared model (each card's pick when they share none).
	 * State lives in the query string (?a=…&b=…&m=…), read on the client: the prerendered page is the
	 * default pair. Bars share one scale and the counters roll together when the choice changes.
	 * The race runs only when both runs come from the same script and conditions.
	 */
	import { afterNavigate, replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import HeatBar from '$lib/fx/HeatBar.svelte';
	import Odometer from '$lib/fx/Odometer.svelte';
	import RaceLanes, { type Lane } from '$lib/fx/RaceLanes.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { findCard, MODEL_INFO, variantLabel, words500, type ModelKey } from '$lib/data/measurements';
	import { fmtGB, fmtSec, fmtTps } from '$lib/format';
	import { cardsHref, currentLang, num } from '$lib/i18n';
	import Choice from './Choice.svelte';
	import { cardsCopy } from './copy';
	import { duel, heatOf, MEASURED, roundTo, runOf, sharedModels } from './explorer';
	import GpuArt from './GpuArt.svelte';
	import Kinetic from './Kinetic.svelte';
	import Ratio from './Ratio.svelte';
	import TimeRace from './TimeRace.svelte';
	import { Play } from './play.svelte';

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].compare);
	const tc = $derived(cardsCopy[lang].card);
	const meta = $derived(cardsCopy[lang].meta);

	const IDS = MEASURED.map((e) => e.id);
	let a = $state('rtx-3090');
	let b = $state('rtx-5060-ti-16');
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
	/** Scoreboard: the faster card's decode ÷ the slower one's (same model and script only). */
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
</script>

<svelte:head>
	<title>{meta.compareTitle}</title>
	<meta name="description" content={meta.compareDescription} />
	<meta property="og:title" content={meta.compareTitle} />
	<meta property="og:description" content={meta.compareDescription} />
</svelte:head>

<section class="hero wrap" aria-labelledby="cmp-title">
	<a class="back mono" href={cardsHref(lang)}><span aria-hidden="true">←</span> {tc.back}</a>
	<p class="eyebrow">{t.eyebrow}</p>
	<Kinetic id="cmp-title" lines={[t.title]} class="giga hx-h" />
	<p class="lede late">{t.lede}</p>

	<div class="pickers late">
		<Choice legend={t.a} name="cmp-a" bind:value={a} options={cardOptions(b)} tight />
		<span class="vs mono" aria-hidden="true">{t.vs}</span>
		<Choice legend={t.b} name="cmp-b" bind:value={b} options={cardOptions(a)} tight />
		{#if shared.length > 1}
			<Choice legend={t.model} name="cmp-m" bind:value={model} options={shared.map((m) => ({ value: m, model: m, label: MODEL_STYLE[m].short }))} tight />
		{/if}
	</div>
	<p class="fine note late">{shared.length ? t.quantNote : t.fallback}</p>

	<div class="board hx-surface hx-ring" aria-live="polite">
		{#each sides as s (s.key)}
			<div class="sc" class:hot={lead?.hi.key === s.key}>
				<span class="sc-n hx-h">{s.card.short}</span>
				<span class="sc-v mono">{#if s.d}<Odometer value={roundTo(s.d.ours.decode!.v, 1)} decimals={1} {lang} duration={1100} />{/if}<span class="u">t/s</span></span>
				{#if s.d}<span class="sc-lab">{variantLabel(s.run, s.run.ours)[lang]}</span><span class="sc-bar" style="--f:{s.d.ours.decode!.v / top}" aria-hidden="true"></span>{/if}
			</div>
		{/each}
		<p class="sc-x hx-bt">
			{#if lead}<Ratio value={lead.x} {lang} size="md" /> <span>{t.leadLine(lead.hi.card.short, lead.lo.card.short)}</span>{:else}{shared.length ? t.noRace : t.noRaceModels}{/if}
		</p>
	</div>
</section>

<section class="wrap duel" aria-label="{A.name} {t.vs} {B.name}">
	{#each sides as s (s.key)}
		<article class="side side--{s.key}">
			<div class="art"><GpuArt label={s.card.short} vendor={s.card.vendor} vram={s.card.vramGB} heat={heatOf(s.d?.ratio)} flat /></div>
			<header>
				<h2 class="nm hx-grad">{s.card.short}</h2>
				<p class="mono sub">{s.card.vramGB}{'\u00a0'}GB · {num(s.card.bwGBs.v, lang, 0)}{'\u00a0'}GB/s · {MODEL_STYLE[s.run.model].short} {s.run.quant}</p>
			</header>
			{#if s.d}
				<HeatBar value={roundTo(s.d.before.decode!.v, 1)} max={top} label={t.before} cold {lang} />
				<dl class="facts">
					{#if s.w}
						<div>
							<dt>{t.words}</dt>
							<dd class="mono">{fmtSec(s.w.v, lang)}</dd>
						</div>
					{/if}
					{#if s.d.ours.ttft}<div><dt>{t.ttft}</dt><dd class="mono">{fmtSec(s.d.ours.ttft.v, lang)}</dd></div>{/if}
					{#if s.d.ours.vram}<div><dt>{t.vram}</dt><dd class="mono">{fmtGB(s.d.ours.vram.v, s.d.ours.vram.unit, lang).text} / {s.card.vramGB}{'\u00a0'}GB</dd></div>{/if}
				</dl>
				<p class="foot">
					<SourceTip {lang} src={[s.d.ours.decode!.src, s.d.before.decode!.src, ...(s.w ? [s.w.src] : []), s.run.conditionsSrc]} note="{s.run.conditions[lang]} · {s.run.metric[lang]}{s.d.ours.vram?.unit === 'GiB' ? ` · ${tc.gibNote}` : ''}" />
					<a href={cardsHref(lang, `${s.card.id}/`)} class="more">{t.open} →</a>
				</p>
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
		<span><SourceTip {lang} src={sides.map((s) => s.w!.src)} note={runA.metric[lang]} /></span>
	</section>
{/if}

<section class="wrap race" aria-labelledby="cmp-race">
	<h2 id="cmp-race" class="h hx-h">{t.race}</h2>
	{#if sameScript && lanes.length === 2}
		{#key raceKey}
			<RaceLanes {lanes} text={tc.raceText} {lang} loop={false} summary={lanes.map((l) => `${l.label}: ${fmtTps(l.tps, lang)} t/s`).join(', ')} />
		{/key}
		<p class="fine">{runA.metric[lang]}</p>
	{:else}
		<p class="fine">{shared.length ? t.noRace : t.noRaceModels}</p>
	{/if}
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.hero {
		display: grid;
		gap: var(--sp-5);
		justify-items: start;
		padding: calc(4.25rem + clamp(1.5rem, 5vh, 4rem)) 0 var(--sp-10);
	}
	.hero :global(h1),
	.hero .lede,
	.hero .eyebrow {
		margin: 0;
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
	.pickers {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: var(--sp-5) var(--sp-6);
		margin-top: var(--sp-4);
	}
	.vs {
		align-self: center;
		padding-top: 1.4rem;
		font-size: var(--fs-sm);
		color: var(--text-mute);
		text-transform: uppercase;
	}
	.note {
		margin: 0;
	}

	.duel {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1px;
		/* the seam between the cards is a vertical heat line */
		background: linear-gradient(180deg, rgb(226 64 28 / 0.15), var(--heat-3) 40%, rgb(226 64 28 / 0.15));
		border: 1px solid rgb(255 122 26 / 0.25);
		border-radius: var(--r-xl);
		overflow: hidden;
	}
	.side {
		position: relative;
		display: grid;
		gap: var(--sp-5);
		align-content: start;
		padding: clamp(1.25rem, 3vw, 2.5rem);
		background:
			radial-gradient(80% 50% at 50% 0%, rgb(255 122 26 / 0.09), transparent),
			radial-gradient(70% 50% at 100% 100%, rgb(226 64 28 / 0.06), transparent),
			var(--bg-0);
	}
	.art {
		max-width: 26rem;
	}
	.nm {
		margin: 0;
		font-size: clamp(2.6rem, 1.2rem + 4vw, 5rem);
		font-weight: 850;
		font-stretch: 118%;
		letter-spacing: -0.045em;
		line-height: 0.9;
		color: var(--text-hi);
		width: fit-content;
	}
	.sub {
		margin: var(--sp-2) 0 0;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		text-shadow: none;
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
		border-top: 1px solid rgb(255 122 26 / 0.16);
	}
	.facts dt {
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.facts dd {
		margin: 0;
		color: var(--text-hi);
	}
	.foot {
		margin: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
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
	/* scoreboard: the answer before the details */
	.board {
		width: 100%;
		display: grid;
		grid-template-columns: 1fr 1fr;
		align-items: end;
		gap: var(--sp-3) var(--sp-6);
		margin-top: var(--sp-4);
		padding: var(--sp-5) var(--sp-6);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
	}
	.sc {
		display: grid;
		gap: 0.3rem;
	}
	.sc-n {
		font-weight: 800;
		font-stretch: 115%;
		font-size: var(--fs-lg);
		color: var(--text);
		letter-spacing: -0.02em;
	}
	.sc-v {
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
		font-size: clamp(2.4rem, 1.2rem + 4vw, 4.5rem);
		font-weight: 600;
		line-height: 1;
		/* both are our engine's speed, so both are hot; the faster one glows more */
		color: var(--heat-5);
		filter: drop-shadow(0 0 8px rgb(255 122 26 / 0.3));
	}
	.sc-lab {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	/* the engine bar lives with its number on the board; the cards below keep the baseline */
	.sc-bar {
		position: relative;
		height: 0.5rem;
		border-radius: 99px;
		background: var(--bg-3);
		overflow: hidden;
	}
	.sc-bar::after {
		content: '';
		position: absolute;
		inset: 0 auto 0 0;
		width: calc(var(--f) * 100%);
		border-radius: inherit;
		background: linear-gradient(90deg, var(--heat-0), var(--heat-2), var(--heat-3), var(--heat-4), var(--heat-5));
		background-size: calc(100% / var(--f)) 100%;
		transform-origin: left;
	}
	@media (prefers-reduced-motion: no-preference) {
		.sc-bar::after {
			animation: sc-fill 1.1s var(--ease-out) both;
		}
	}
	@keyframes sc-fill {
		from {
			transform: scaleX(0);
		}
	}
	.sc.hot .sc-n {
		color: var(--text-hi);
	}
	.sc.hot .sc-v {
		filter: drop-shadow(0 0 18px rgb(255 122 26 / 0.6));
	}
	.sc-x {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.2rem 0.75rem;
		margin: 0;
		padding-top: var(--sp-3);
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.words {
		display: grid;
		gap: var(--sp-5);
		padding-top: var(--section-y);
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
		font-stretch: 110%;
		color: var(--text-hi);
	}
	.race .fine {
		margin: 0;
	}
	@media (max-width: 52rem) {
		.duel {
			grid-template-columns: 1fr;
		}
		.hero {
			gap: var(--sp-3);
		}
		.hero .lede {
			display: none;
		}
		/* the answer first: scoreboard right under the title, the pickers after it */
		.hero .late {
			order: 2;
		}
		.board {
			order: 1;
			margin-top: var(--sp-2);
		}
		.pickers {
			display: grid;
			width: 100%;
			gap: var(--sp-3);
			margin-top: 0;
		}
		.pickers :global(fieldset) {
			min-width: 0;
		}
		.board {
			padding: var(--sp-4);
		}
		.side .art {
			display: none;
		}
		.vs {
			display: none;
		}
	}
</style>
