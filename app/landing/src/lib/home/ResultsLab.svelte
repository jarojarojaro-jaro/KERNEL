<script lang="ts">
	/**
	 * Interactive results: pick a measured GPU and a model measured on it; bars, odometers, the gain,
	 * two real-time stopwatches (500 words) and a compact race replay. Race and stopwatches appear
	 * only for same-script pairs; otherwise the different-script warning takes their place.
	 */
	import { heatOf } from '$lib/cards/explorer';
	import { duel } from '$lib/cards/explorer';
	import { play, reveal, tilt } from '$lib/fx/actions';
	import HeatBar from '$lib/fx/HeatBar.svelte';
	import RaceLanes from '$lib/fx/RaceLanes.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { MODEL_INFO, variantLabel, variantOf, words500 } from '$lib/data/measurements';
	import { cardsHref, num, type Lang } from '$lib/i18n';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { copy } from '$lib/site/copy';
	import { CARDS, columns, decode, dialFor, fill, nb, raceCold, fmtRatio } from './data';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { fmtGB } from '$lib/format';
	import Duo from './Duo.svelte';
	import Segmented from './Segmented.svelte';
	import TimeDuel from './TimeDuel.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].results);
	const raceText = $derived(copy[lang].hero.race.text);

	let gpu = $state(CARDS[0].id);
	let model = $state(CARDS[0].pick.model as string);
	/** Bars and counters rest on the measured values; entering view replays them once from 0. */
	let seen = $state(false);
	let rep = $state(0);

	const card = $derived(CARDS.find((k) => k.id === gpu) ?? CARDS[0]);
	const run = $derived(card.runs.find((r) => r.model === model) ?? card.runs.find((r) => r.model === card.pick.model) ?? card.runs[0]);
	const key = $derived(`${card.id}:${run.model}`);

	function pickGpu(id: string) {
		gpu = id;
		const k = CARDS.find((x) => x.id === id);
		if (k && !k.runs.some((r) => r.model === model)) model = k.pick.model;
	}

	const gpuOptions = CARDS.map((k) => ({ id: k.id, label: k.short, sub: `${k.vramGB} GB` }));
	const modelOptions = $derived(card.runs.map((r) => ({ id: r.model as string, label: MODEL_STYLE[r.model].short, mark: r.model, sub: r.quant.replace(/\s*\(.*\)$/, '') })));

	const cols = $derived(columns(run));
	/** Bars share the page-wide dial: 0–100 t/s with the redline at 70 (longer scale for fast MoE runs). */
	const barDial = $derived(dialFor(Math.max(...cols.map((k) => decode(variantOf(run, k))))));
	const ours = $derived(variantOf(run, run.ours));
	const coldKey = $derived(raceCold(run));
	const cold = $derived(variantOf(run, coldKey));
	/** Same rule and source as the cards explorer: the sheet's total, only for same-script pairs. */
	const gain = $derived(duel(run)?.ratio ?? null);
	const w0 = $derived(words500(cold, lang));
	const w1 = $derived(words500(ours, lang));
	const src = $derived([run.src, ...cols.map((k) => variantOf(run, k)?.decode?.src ?? ''), run.conditionsSrc].filter(Boolean));
	const conditions = $derived(`${run.metric[lang]} ${run.conditions[lang]}.`);
	const lanes = $derived([
		{ id: `${key}:cold`, label: variantLabel(run, coldKey)[lang], tps: decode(cold), hot: false },
		{ id: `${key}:hot`, label: variantLabel(run, run.ours)[lang], tps: decode(ours), hot: true }
	]);
	const dial = $derived(dialFor(Math.max(...lanes.map((l) => l.tps))));
	const raceWords = $derived(raceText.split(/\s+/).filter(Boolean).length);
	/** One sentence that ties the three lengths on this page together (measured pace, 500 words, the race). */
	const lengths = $derived(
		fill(c.lengths, { t500: num(Math.round(500 * TOK_PER_WORD[lang]), lang, 0), words: raceWords, tok: num(Math.round(raceWords * TOK_PER_WORD[lang]), lang, 0) })
	);
	const summary = $derived(
		fill(c.summary, { card: card.name, model: `${MODEL_INFO[run.model].name} ${run.quant}`, cold: lanes[0].label, a: num(lanes[0].tps, lang), hot: lanes[1].label, b: num(lanes[1].tps, lang) })
	);
</script>

<section id="results" class="results" aria-labelledby="results-title">
	<div class="inner">
		<header class="head" use:reveal>
			<Duo text={c.title} tag="h1" id="results-title" size="scene" mode="plain" />
		</header>

		<div class="pickers" use:reveal use:play={{ threshold: 0.2, onplay: () => { rep++; seen = true; } }}>
			<div class="pk">
				<span class="pl" id="pk-gpu">{c.gpu}</span>
				<Segmented options={gpuOptions} bind:value={() => gpu, pickGpu} label={c.gpu} size="lg" />
			</div>
			<div class="pk">
				<span class="pl" id="pk-model">{c.model}</span>
				{#key card.id}
					<Segmented options={modelOptions} bind:value={model} label={c.model} />
				{/key}
			</div>
		</div>

		<div class="board">
			<div class="bars panel">
				<p class="title-row">
					<span class="card-name">{nb(card.name)}</span>
					<span class="run-name">{MODEL_INFO[run.model].name} {run.quant}{#if run.file}{' · '}{fmtGB(run.file.v, run.file.unit, lang).text}{/if}</span>
				</p>
				{#each cols as k, i (k)}
					{@const v = variantOf(run, k)}
					<HeatBar
						value={decode(v)}
						replay={rep}
						max={barDial.max}
						redline={barDial.redline}
						label={variantLabel(run, k)[lang]}
						cold={k !== run.ours}
						{lang}
						delay={i * 110}
					/>
				{/each}
				<p class="cond">
					<span>{c.conditions}: {conditions}</span>
					<SourceTip {lang} {src} note={conditions} />
				</p>
			</div>

			<div class="side">
				{#if !run.sameHarness}
					<div class="warn" role="note">
						<p class="wt">⚠ {c.diffTitle}</p>
						<p>{run.metric[lang]}</p>
						<p class="wn">{c.noRace}</p>
					</div>
				{:else}
					<div class="gain panel" use:tilt={{ max: 4 }}>
						{#if gain}
							<p class="gv speedup" class:speedup--down={gain < 1} style="--rh:{heatOf(gain)}">{fmtRatio(gain, lang)}</p>
							<p class="gl">{fill(c.gainOf, { before: variantLabel(run, run.before)[lang] })}</p>
						{/if}
						{#if w0 && w1}
							<TimeDuel
								title="{c.words}{w0.derived || w1.derived ? ` · ${c.derived}` : ''}"
								cold={{ label: lanes[0].label, s: w0.v }}
								hot={{ label: lanes[1].label, s: w1.v }}
								{lang}
								run={seen}
								runKey={key}
								done={c.done}
								gap={c.gap}
							/>
						{/if}
					</div>
				{/if}
				{#if run.note}
					<p class="note" role="note">{run.note[lang]}</p>
				{/if}
			</div>
		</div>

		{#if run.sameHarness}
			<div class="race">
				<p class="rh">{c.race}</p>
				<RaceLanes {lanes} text={raceText} {lang} runKey={key} loop={false} {summary} clock={false} max={dial.max} redline={dial.redline} />
			</div>
		{/if}

		<p class="lengths">{lengths}</p>
		<a class="more" href={cardsHref(lang, card.id)}>{c.more} <span aria-hidden="true">→</span></a>
	</div>
</section>

<style>
	.results {
		position: relative;
		isolation: isolate;
		overflow: clip;
		padding-block: clamp(2rem, 1.5rem + 2vw, 3.5rem) clamp(4rem, 3rem + 4vw, 6rem);
		background: var(--bg-0);
	}
	/* a slow-drifting heat glow behind the lab (transform only, composited) */
	.results::before {
		content: '';
		position: absolute;
		inset: -20% -10% auto;
		height: 90%;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(40% 45% at 25% 30%, rgb(226 64 28 / 0.14), transparent 70%),
			radial-gradient(35% 40% at 80% 20%, rgb(255 122 26 / 0.12), transparent 70%);
		animation: lab-drift 18s ease-in-out infinite alternate;
	}
	@keyframes lab-drift {
		to {
			transform: translate3d(4%, 6%, 0) scale(1.08);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.results::before {
			animation: none;
		}
	}
	/* panels warm up on hover; the section's numbers carry heat highlights */
	.results :global(.panel) {
		transition:
			border-color 0.3s,
			box-shadow 0.3s;
	}
	.results :global(.panel:hover) {
		border-color: rgb(255 122 26 / 0.45);
		box-shadow: 0 0 40px -18px rgb(255 122 26 / 0.6);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(2rem, 4vw, 3.5rem);
	}
	/* centred, full-width statement: this section breaks the left-headline rhythm */
	.head {
		display: grid;
		gap: var(--sp-5);
		justify-items: center;
		text-align: center;
		padding-bottom: 0;
	}
	.pickers {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: var(--sp-6);
		align-items: start;
	}
	.pk {
		display: grid;
		gap: var(--sp-2);
	}
	.pl,
	.rh {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--heat-4);
	}
	/* a short heat dash before each label */
	.pl::before,
	.rh::before {
		content: '';
		width: 1.4rem;
		height: 2px;
		border-radius: 2px;
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 8px rgb(255 122 26 / 0.6);
	}
	.board {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: var(--sp-6);
		align-items: start;
	}
	.bars {
		display: grid;
		gap: var(--sp-6);
		padding: clamp(1.25rem, 2.5vw, 2rem);
	}
	.title-row {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.3rem 1rem;
	}
	.card-name {
		font-weight: 760;
		font-stretch: 112%;
		font-size: var(--fs-xl);
		letter-spacing: -0.02em;
		color: var(--text-hi);
	}
	.run-name {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.04em;
	}
	.bars :global(.hb .val) {
		font-size: clamp(1.4rem, 1rem + 1.2vw, 2rem);
	}
	.cond {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
		font-size: var(--fs-xs);
		color: var(--text-mute);
		line-height: 1.5;
	}
	.side {
		display: grid;
		gap: var(--sp-4);
	}
	.gain {
		display: grid;
		gap: var(--sp-3);
		padding: clamp(1.25rem, 2.5vw, 2rem);
		overflow: hidden;
	}
	.gv {
		font-size: clamp(3.5rem, 2rem + 5vw, 6.5rem);
	}
	.gl {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text);
	}
	.warn {
		display: grid;
		gap: var(--sp-3);
		padding: clamp(1.25rem, 2.5vw, 2rem);
		border: 1px solid var(--warn);
		border-radius: var(--r-xl);
		background: var(--warn-soft);
		color: var(--text-hi);
		line-height: 1.5;
	}
	.wt {
		font-weight: 760;
		font-stretch: 110%;
		font-size: var(--fs-lg);
		color: var(--warn-ink);
	}
	.wn {
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.note {
		padding: var(--sp-4) var(--sp-5);
		border-left: 2px solid var(--text-hi);
		background: var(--bg-1);
		border-radius: 0 var(--r-md) var(--r-md) 0;
		color: var(--text-hi);
		font-size: var(--fs-sm);
		line-height: 1.55;
	}
	.race {
		display: grid;
		gap: var(--sp-3);
	}
	.lengths {
		max-width: 72ch;
		font-size: var(--fs-xs);
		line-height: 1.5;
		color: var(--text-mute);
	}
	.more {
		justify-self: start;
		font-weight: 650;
		font-stretch: 108%;
		font-size: var(--fs-lg);
		color: var(--text-hi);
		text-decoration: none;
		border-bottom: 1px solid var(--heat-3);
		padding-bottom: 0.2rem;
		transition:
			border-color var(--dur-2),
			color var(--dur-2);
	}
	.more:hover {
		color: var(--heat-4);
		border-color: var(--heat-4);
	}
	@media (max-width: 900px) {
		.pickers,
		.board {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
