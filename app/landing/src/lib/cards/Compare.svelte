<script lang="ts">
	/**
	 * Versus: two measured cards face to face on a shared model (each card's pick when they share
	 * none), as a title-fight face-off (Versus.svelte): each card in its maker's colour field, the
	 * fields colliding on an energy seam under a heavy VS, stat bars clashing from both edges. A stat
	 * has a winner only when both runs come from the same model, script and conditions (`comparable`);
	 * otherwise the arena says there is no verdict. The fighters are picked below like a fighter
	 * select (photo chips in the makers' colours). Then the 500-word race and the token race.
	 *
	 * State lives in the query string (?a=…&b=…&m=…), read on the client: the prerendered page is the
	 * default pair. The arena plays its entrance from the first paint; changing a card replays its
	 * slam and the VS, the bars glide and the numbers roll to the new pair.
	 */
	import { afterNavigate, replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import RaceLanes, { type Lane } from '$lib/fx/RaceLanes.svelte';
	import { findCard, MODEL_INFO, words500, type ModelKey } from '$lib/data/measurements';
	import { fmtTps } from '$lib/format';
	import { cardsHref, currentLang, num } from '$lib/i18n';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import Choice from './Choice.svelte';
	import { cardsCopy } from './copy';
	import { comparable, duel, heatOf, MEASURED, roundTo, runOf, sharedModels } from './explorer';
	import GpuArt from './GpuArt.svelte';
	import Kinetic from './Kinetic.svelte';
	import { Play } from './play.svelte';
	import ProductPhoto from './ProductPhoto.svelte';
	import Ratio from './Ratio.svelte';
	import TimeRace from './TimeRace.svelte';
	import { photoOf, VENDOR, vendorOf, vendorVars } from './vendor';
	import Versus, { type VsFighter, type VsStat } from './Versus.svelte';

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
	// Winners and races only for the same model under the same script and conditions.
	const sameScript = $derived(comparable(runA, runB));

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

	const NB = '\u00a0';
	const fighters = $derived(
		sides.map(
			(s): VsFighter => ({
				id: s.card.id,
				vendor: s.card.vendor,
				name: s.card.short,
				sub: [`${s.card.vramGB}${NB}GB`, `${num(s.card.bwGBs.v, lang, 0)}${NB}GB/s`, MODEL_INFO[s.run.model].name, s.run.quant],
				photo: photoOf(s.card.id),
				vram: s.card.vramGB,
				heat: heatOf(s.d?.ratio),
				href: cardsHref(lang, `${s.card.id}/`),
				hrefLabel: t.open,
				note: s.run.sameHarness ? undefined : tc.scriptsWarn
			})
		)
	);
	const r1 = (v: number | undefined) => (v == null ? null : roundTo(v, 1));
	const stats = $derived<VsStat[]>([
		{ key: 'ours', label: t.decode, unit: 't/s', decimals: 1, a: r1(dA?.ours.decode?.v), b: r1(dB?.ours.decode?.v), better: 'hi' },
		{ key: 'words', label: t.words, unit: 's', decimals: 1, a: r1(sides[0].w?.v), b: r1(sides[1].w?.v), better: 'lo' },
		{ key: 'ttft', label: t.ttft, unit: 's', decimals: 1, a: r1(dA?.ours.ttft?.v), b: r1(dB?.ours.ttft?.v), better: 'lo' },
		{ key: 'before', label: t.before, unit: 't/s', decimals: 1, a: r1(dA?.before.decode?.v), b: r1(dB?.before.decode?.v), better: 'hi' },
		{ key: 'vram', label: t.vram, unit: 'GB', decimals: 1, a: r1(dA?.ours.vram?.v), b: r1(dB?.ours.vram?.v), better: null, aSub: `/ ${A.vramGB}${NB}GB`, bSub: `/ ${B.vramGB}${NB}GB` }
	]);
	const glow = $derived.by(() => {
		const va = VENDOR[vendorOf(A.vendor)];
		const vb = VENDOR[vendorOf(B.vendor)];
		return `--a:${va.rgb}; --b:${vb.rgb}`;
	});
</script>

<svelte:head>
	<title>{meta.compareTitle}</title>
	<meta name="description" content={meta.compareDescription} />
	<meta property="og:title" content={meta.compareTitle} />
	<meta property="og:description" content={meta.compareDescription} />
</svelte:head>

<div class="amb" style={glow} aria-hidden="true"></div>

<section class="hero wrap" aria-labelledby="cmp-title">
	<a class="back mono" href={cardsHref(lang)}><span aria-hidden="true">←</span> {tc.back}</a>
	<p class="eyebrow">{t.eyebrow}</p>
	<Kinetic id="cmp-title" lines={[t.title]} class="giga hx-h" />
	<p class="lede">{t.lede}</p>
</section>

<section class="wrap arena" aria-label="{A.name} {t.vs} {B.name}" aria-live="polite">
	<Versus a={fighters[0]} b={fighters[1]} {stats} verdict={sameScript} {lang} winLabel={t.win} missingLabel={t.missing} mode="intro">
		{#snippet foot()}
			<p class="verdict">
				{#if lead}<Ratio value={lead.x} {lang} size="md" /> <span>{t.leadLine(lead.hi.card.short, lead.lo.card.short)}</span>{:else}<span class="nv">{shared.length ? t.noVerdict : t.noRaceModels}</span>{/if}
			</p>
		{/snippet}
	</Versus>
</section>

{#snippet roster(side: 'a' | 'b', legend: string)}
	<fieldset class="roster roster-{side}">
		<legend><span class="tag">{side === 'a' ? 'A' : 'B'}</span>{legend}</legend>
		<div class="chips">
			{#each MEASURED as e (e.id)}
				{@const taken = side === 'a' ? e.id === b : e.id === a}
				{@const on = side === 'a' ? e.id === a : e.id === b}
				<label class="chip" class:on class:taken style={vendorVars(e.card.vendor)}>
					{#if side === 'a'}
						<input type="radio" name="cmp-a" value={e.id} bind:group={a} disabled={taken} />
					{:else}
						<input type="radio" name="cmp-b" value={e.id} bind:group={b} disabled={taken} />
					{/if}
					<span class="thumb" aria-hidden="true">
						{#if photoOf(e.id)}<ProductPhoto id={photoOf(e.id)!} sizes="7rem" />{:else}<GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} flat />{/if}
					</span>
					<span class="who">
						<span class="mk" class:upright={e.card.vendor !== 'nvidia' && e.card.vendor !== 'amd'}>{VENDOR[vendorOf(e.card.vendor)].name}</span>
						<span class="nm">{e.card.short}</span>
						<span class="vr mono">{e.card.vramGB}{NB}GB</span>
					</span>
				</label>
			{/each}
		</div>
	</fieldset>
{/snippet}

<section class="wrap pick" aria-labelledby="cmp-select">
	<h2 id="cmp-select" class="pick-h">{t.select}</h2>
	<div class="rosters">
		{@render roster('a', t.a)}
		{@render roster('b', t.b)}
	</div>
	{#if shared.length > 1}
		<div class="pk-m"><Choice legend={t.model} name="cmp-m" bind:value={model} options={shared.map((m) => ({ value: m, model: m, label: MODEL_STYLE[m].short }))} tight /></div>
	{/if}
	<p class="fine note">{shared.length ? t.quantNote : t.fallback}</p>
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

	/* ---------- fighter select ---------- */
	.pick {
		display: grid;
		gap: var(--sp-4);
		padding-top: clamp(2rem, 4vw, 3rem);
	}
	.pick-h {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-xl);
		font-weight: 850;
		font-style: italic;
		font-stretch: 115%;
		letter-spacing: -0.01em;
		text-transform: uppercase;
		color: var(--text-hi);
	}
	.rosters {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: var(--sp-4) clamp(1rem, 3vw, 2.5rem);
	}
	.roster {
		margin: 0;
		padding: 0;
		border: 0;
		min-width: 0;
	}
	legend {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: var(--sp-2);
		padding: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.roster-b legend {
		justify-content: flex-end;
		width: 100%;
	}
	.tag {
		display: inline-grid;
		place-items: center;
		width: 1.4rem;
		height: 1.4rem;
		border-radius: var(--r-sm);
		background: var(--text-hi);
		color: var(--bg-0);
		font-family: var(--font-display);
		font-weight: 900;
		font-style: italic;
		letter-spacing: 0;
	}
	.chips {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-2);
	}
	/* a fighter chip: the card's photo on its maker's colour; picked = lit rim and lift */
	.chip {
		--text-hi: #edeae3;
		--text-mute: #8e8a83;
		position: relative;
		display: grid;
		grid-template-columns: 5.5rem minmax(0, 1fr);
		align-items: center;
		gap: var(--sp-2);
		min-height: 4.25rem;
		padding: 0.4rem 0.75rem 0.4rem 0.4rem;
		border-radius: var(--r-lg);
		background: linear-gradient(110deg, rgb(var(--v) / 0.3), rgb(var(--v) / 0.06) 55%), linear-gradient(180deg, var(--v-deep), #070708);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.3);
		color: var(--text-hi);
		cursor: pointer;
		user-select: none;
		transition:
			transform 0.45s var(--ease-spring),
			box-shadow 0.3s,
			opacity 0.3s;
	}
	.chip:hover:not(.taken) {
		transform: translate3d(0, -2px, 0);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.7);
	}
	.chip.on {
		transform: translate3d(0, -2px, 0);
		box-shadow:
			inset 0 0 0 2px rgb(var(--v)),
			0 0 28px -6px rgb(var(--v) / 0.8);
	}
	.chip.taken {
		opacity: 0.35;
		cursor: not-allowed;
	}
	.chip:has(input:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.chip input {
		position: absolute;
		opacity: 0;
		width: 1px;
		height: 1px;
		pointer-events: none;
	}
	.thumb {
		display: block;
		filter: drop-shadow(0 0 6px rgb(var(--v) / 0.5));
	}
	.who {
		display: grid;
		min-width: 0;
		line-height: 1.1;
	}
	.mk {
		padding-right: 0.2em;
		font-family: var(--font-display);
		font-size: 0.7rem;
		font-weight: 900;
		font-style: italic;
		letter-spacing: 0.06em;
		color: var(--v-hi);
	}
	.mk.upright {
		font-style: normal;
	}
	.nm {
		font-family: var(--font-display);
		font-size: var(--fs-lg);
		font-weight: 850;
		font-stretch: 110%;
		letter-spacing: -0.02em;
	}
	.vr {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.pk-m {
		justify-self: center;
	}
	.pk-m :global(legend) {
		width: 100%;
		justify-content: center;
		text-align: center;
	}
	.note {
		justify-self: center;
		margin: 0;
		text-align: center;
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
		.chips {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 30rem) {
		.chip {
			grid-template-columns: 3.75rem minmax(0, 1fr);
			padding-right: 0.5rem;
		}
		.nm {
			font-size: var(--fs-md);
		}
	}
</style>
