<script lang="ts">
	/**
	 * Versus: two measured cards face to face on a shared model (each card's pick when they share
	 * none), as a full-bleed title-fight face-off (Versus.svelte) with a round-by-round scoreboard
	 * (a stat only when both cards have it). A stat has a winner only when both runs come from the
	 * same model, script and conditions (`comparable`); otherwise the board says there is no verdict.
	 * The fighters are picked below like a fighter select (portrait tiles in the makers' colours,
	 * corner A over corner B; the selection hint is for screen readers only). Then the 500-word race
	 * and the token race.
	 *
	 * State lives in the query string (?a=…&b=…&m=…), read on the client: the prerendered page is the
	 * default pair. The arena plays its entrance from the first paint; changing a card replays its
	 * slam and the VS, the bars glide and the numbers roll to the new pair.
	 */
	import { afterNavigate, replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import RaceLanes, { type Lane } from '$lib/fx/RaceLanes.svelte';
	import { findCard, MODEL_INFO, words500, type ModelKey } from '$lib/data/measurements';
	import { fmtTps, ratioDigits } from '$lib/format';
	import { cardsHref, currentLang } from '$lib/i18n';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import Choice from './Choice.svelte';
	import { cardsCopy } from './copy';
	import { comparable, duel, heatOf, LINEUP, MEASURED, roundTo, runOf, sharedModels } from './explorer';
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
				line: LINEUP[s.card.vendor as keyof typeof LINEUP],
				sub: [`${s.card.vramGB}${NB}GB`, MODEL_INFO[s.run.model].name, s.run.quant],
				photo: photoOf(s.card.id),
				vram: s.card.vramGB,
				heat: heatOf(s.d?.ratio),
				href: cardsHref(lang, `${s.card.id}/`),
				hrefLabel: t.open,
				note: s.run.sameHarness ? undefined : tc.scriptsWarn
			})
		)
	);
	const r = (v: number | null | undefined, digits = 1) => (v == null ? null : roundTo(v, digits));
	const xDigits = $derived(ratioDigits(Math.min(dA?.ratio ?? 9, dB?.ratio ?? 9)));
	/* measured numbers only; Versus shows a row only when both cards have it */
	const stats = $derived<VsStat[]>([
		{ key: 'ours', label: t.decode, unit: 't/s', decimals: 1, a: r(dA?.ours.decode?.v), b: r(dB?.ours.decode?.v), better: 'hi' },
		{ key: 'before', label: t.before, unit: 't/s', decimals: 1, a: r(dA?.before.decode?.v), b: r(dB?.before.decode?.v), better: 'hi' },
		{ key: 'ratio', label: t.ratio, unit: '×', decimals: xDigits, a: r(dA?.ratio, xDigits), b: r(dB?.ratio, xDigits), better: 'hi' },
		{ key: 'words', label: t.words, unit: 's', decimals: 1, a: r(sides[0].w?.v), b: r(sides[1].w?.v), better: 'lo' },
		{ key: 'ttft', label: t.ttft, unit: 's', decimals: 1, a: r(dA?.ours.ttft?.v), b: r(dB?.ours.ttft?.v), better: 'lo' },
		{ key: 'vram', label: t.vram, unit: 'GB', decimals: 1, a: r(dA?.ours.vram?.v), b: r(dB?.ours.vram?.v), better: null, aSub: `/ ${A.vramGB}${NB}GB`, bSub: `/ ${B.vramGB}${NB}GB` }
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
</section>

<section class="arena" aria-label="{A.name} {t.vs} {B.name}" aria-live="polite">
	<Versus
		a={fighters[0]}
		b={fighters[1]}
		{stats}
		verdict={sameScript}
		{lang}
		winLabel={t.win}
		boardTag={sameScript ? t.verdict : t.noVerdictTag}
		boardNote={sameScript ? undefined : shared.length ? t.noVerdict : t.noVerdictModels}
		mode="intro"
	>
		{#snippet foot()}
			{#if lead}
				<p class="verdict wrap"><Ratio value={lead.x} {lang} size="md" /> <span>{t.leadLine(lead.hi.card.short, lead.lo.card.short)}</span></p>
			{/if}
		{/snippet}
	</Versus>
</section>

{#snippet roster(side: 'a' | 'b', legend: string)}
	<fieldset class="roster roster-{side}" aria-describedby="cmp-hint">
		<legend><span class="tag">{side === 'a' ? 'A' : 'B'}</span>{legend}</legend>
		<div class="tiles">
			{#each MEASURED as e (e.id)}
				{@const taken = side === 'a' ? e.id === b : e.id === a}
				{@const on = side === 'a' ? e.id === a : e.id === b}
				<label class="tile" class:on class:taken style={vendorVars(e.card.vendor)}>
					{#if side === 'a'}
						<input type="radio" name="cmp-a" value={e.id} bind:group={a} disabled={taken} />
					{:else}
						<input type="radio" name="cmp-b" value={e.id} bind:group={b} disabled={taken} />
					{/if}
					<span class="t-ph" aria-hidden="true">
						{#if photoOf(e.id)}<ProductPhoto id={photoOf(e.id)!} sizes="(max-width: 40rem) 40vw, 14rem" />{:else}<GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} flat />{/if}
					</span>
					<span class="who">
						<span class="mk" class:upright={e.card.vendor !== 'nvidia' && e.card.vendor !== 'amd'}>{VENDOR[vendorOf(e.card.vendor)].name}</span>
						<span class="nm">{e.card.short}</span>
						<span class="vr mono">{e.card.vramGB}{NB}GB</span>
					</span>
					{#if on}<span class="t-tag" aria-hidden="true">{side === 'a' ? 'A' : 'B'}</span>{/if}
					{#if taken}<span class="t-tag t-tag--other" aria-hidden="true">{side === 'a' ? 'B' : 'A'}</span>{/if}
				</label>
			{/each}
		</div>
	</fieldset>
{/snippet}

<section class="wrap pick" aria-labelledby="cmp-select">
	<h2 id="cmp-select" class="pick-h">{t.select}</h2>
	<p id="cmp-hint" class="sr-only">{t.pickHint}</p>
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
	/* a tight head, so the face-off below fits the first screen */
	.hero {
		display: grid;
		gap: var(--sp-1);
		justify-items: start;
		padding: calc(4.25rem + clamp(0.5rem, 1.5svh, 1.25rem)) 0 clamp(0.75rem, 2svh, 1.25rem);
	}
	.hero :global(h1),
	.hero .eyebrow {
		margin: 0;
	}
	.hero :global(h1) {
		font-size: clamp(2rem, 1rem + 3.2vw, 4rem);
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
		margin-top: var(--sp-4);
		text-align: center;
		font-size: var(--fs-sm);
		color: var(--text);
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
	/* the two corners, A over B, each a strip of big portrait tiles (A from the left, B from the right) */
	.rosters {
		display: grid;
		gap: var(--sp-4);
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
	.tiles {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(9rem, 14.5rem);
		gap: var(--sp-3);
		padding: 0.4rem 0.2rem 0.6rem;
		overflow-x: auto;
		scroll-snap-type: x proximity;
		scrollbar-width: thin;
	}
	.roster-b .tiles {
		justify-content: safe end;
	}
	/* a fighter tile: the card in its maker's light, the name below; picked = lit rim, the card steps
	   forward, the corner letter pops in */
	.tile {
		--text-hi: #edeae3;
		--text-mute: #8e8a83;
		--turn: -7deg;
		position: relative;
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto;
		aspect-ratio: 10 / 11;
		padding: 0.6rem 0.8rem 0.75rem;
		border-radius: var(--r-lg);
		background:
			radial-gradient(80% 60% at 50% 0%, rgb(var(--v) / 0.45), transparent 70%),
			linear-gradient(180deg, var(--v-deep), #070708 85%);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.28);
		color: var(--text-hi);
		cursor: pointer;
		user-select: none;
		scroll-snap-align: start;
		overflow: hidden;
		transition:
			transform 0.45s var(--ease-spring),
			box-shadow 0.3s,
			opacity 0.3s;
	}
	.roster-b .tile {
		--turn: 7deg;
	}
	/* a beam from above, brighter when picked */
	.tile::before {
		content: '';
		position: absolute;
		inset: -10% 25% 30%;
		background: linear-gradient(180deg, rgb(var(--v) / 0.5), transparent 85%);
		clip-path: polygon(40% 0, 60% 0, 100% 100%, 0 100%);
		opacity: 0.35;
		transition: opacity 0.4s;
		pointer-events: none;
	}
	.t-ph {
		position: relative;
		display: grid;
		place-items: center;
		min-height: 0;
		transform: rotate(var(--turn)) scale(0.92);
		transition: transform 0.55s var(--ease-spring);
		filter: drop-shadow(0 0 1px rgb(var(--v) / 0.9)) drop-shadow(0 6px 14px rgb(0 0 0 / 0.6));
	}
	.tile:hover:not(.taken) {
		transform: translate3d(0, -3px, 0);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.7);
	}
	.tile:hover:not(.taken) .t-ph {
		transform: rotate(var(--turn)) scale(1);
	}
	.tile.on {
		transform: translate3d(0, -4px, 0);
		box-shadow:
			inset 0 0 0 2px rgb(var(--v)),
			0 0 34px -6px rgb(var(--v) / 0.85);
	}
	.tile.on::before {
		opacity: 1;
	}
	.tile.on .t-ph {
		transform: rotate(calc(var(--turn) * 0.4)) scale(1.08) translate3d(0, -3%, 0);
	}
	.tile.taken {
		opacity: 0.32;
		cursor: not-allowed;
	}
	.tile:has(input:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.tile input {
		position: absolute;
		opacity: 0;
		width: 1px;
		height: 1px;
		pointer-events: none;
	}
	.t-tag {
		position: absolute;
		top: 0.5rem;
		left: 0.5rem;
		display: grid;
		place-items: center;
		width: 1.7rem;
		height: 1.7rem;
		border-radius: var(--r-sm);
		background: #fff3d6;
		color: #1a1205;
		font-family: var(--font-display);
		font-weight: 900;
		font-style: italic;
		box-shadow: 0 0 18px rgb(var(--v) / 0.9);
	}
	.roster-b .t-tag {
		left: auto;
		right: 0.5rem;
	}
	.t-tag--other {
		background: rgb(255 255 255 / 0.12);
		color: var(--text-hi);
		box-shadow: none;
	}
	.who {
		position: relative;
		display: grid;
		min-width: 0;
		line-height: 1.05;
	}
	.mk {
		padding-right: 0.2em;
		font-family: var(--font-display);
		font-size: 0.75rem;
		font-weight: 900;
		font-style: italic;
		letter-spacing: 0.06em;
		color: var(--v-hi);
		text-shadow: 0 0 12px rgb(var(--v) / 0.7);
	}
	.mk.upright {
		font-style: normal;
	}
	.nm {
		padding-right: 0.08em;
		font-family: var(--font-display);
		font-size: clamp(1.25rem, 0.8rem + 1.2vw, 1.9rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 118%;
		letter-spacing: -0.035em;
		white-space: nowrap;
	}
	.vr {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	@media (prefers-reduced-motion: no-preference) {
		.t-tag:not(.t-tag--other) {
			animation: tag-pop 0.45s cubic-bezier(0.3, 1.6, 0.5, 1);
		}
	}
	@keyframes tag-pop {
		from {
			opacity: 0;
			transform: scale(0.3) rotate(-12deg);
		}
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

	/* phones: the corners scroll sideways, a tile and a bit of the next one in view */
	@media (max-width: 40rem) {
		.tiles {
			grid-auto-columns: 8.75rem;
			gap: var(--sp-2);
			margin-inline: calc(-1 * var(--gutter));
			padding-inline: var(--gutter);
			scroll-padding-inline: var(--gutter);
		}
		.roster-b .tiles {
			justify-content: start;
		}
		.tile {
			padding: 0.5rem 0.6rem 0.6rem;
		}
	}
</style>
