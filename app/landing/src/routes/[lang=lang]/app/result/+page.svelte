<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { currentLang, num } from '$lib/i18n';
	import { M, KLD_EXCEPTIONS, MD5, SHEET, type Measurement } from '$lib/data/measurements';
	import { TOK_PER_WORD, answerSeconds } from '$lib/estimator';
	import { T } from '$lib/desktop/i18n';
	import { proto } from '$lib/desktop/state.svelte';
	import { reportEntry } from '$lib/desktop/demo';
	import ScreenHead from '$lib/desktop/ScreenHead.svelte';
	import Src from '$lib/desktop/Src.svelte';
	import Icon from '$lib/desktop/Icon.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const r = $derived(t.result);

	const before = M.qwenUpstreamVulkanPlain;
	const l1 = M.qwenUpstreamVulkanMtp;
	const l3 = M.qwenOursMtp;
	const scale = l3.value * 1.08;
	const MD5_SRC = 'KERNEL/qwen-opt/STATUS-NEXT.md:15';
	const Q = SHEET.correctness.quality;
	const kld = (v: number) => num(v, lang, 5);

	type Bar = { key: 'before' | 'l1' | 'l2' | 'l3'; m: Measurement | null; tone: string; tag?: 'same' | 'other' };
	const bars: Bar[] = [
		{ key: 'before', m: before, tone: 'before' },
		{ key: 'l1', m: l1, tone: 'l1', tag: 'same' },
		{ key: 'l2', m: null, tone: 'l2' },
		{ key: 'l3', m: l3, tone: 'l3', tag: 'other' }
	];

	const f1 = (v: number) => num(v, lang, 1);
	const words = (tps: number, l: 'pl' | 'en') => tps / TOK_PER_WORD[l];
	const wps = (tps: number, l: 'pl' | 'en') => {
		const v = Math.round(words(tps, l) * 10) / 10;
		return t.common.wordsPerSec(f1(v), v);
	};
	const gain = (a: Measurement, b: Measurement) =>
		`+${f1(b.value - a.value)} t/s · ×${num(b.value / a.value, lang, 2)}`;

	let view = $state<'result' | 'nochange'>('result');
	const WORD_LANGS = ['pl', 'en'] as const;

	const sameHarness = (a: Measurement, b: Measurement) => a.harness === b.harness;

	function downloadReport() {
		const data = {
			product: BRAND.name,
			generated: new Date().toISOString(),
			prototype: true,
			note: r.reportNote,
			measurements: [before, l1, l3, M.bacoAsleep, M.bacoAwake].map((m) => reportEntry(m, lang)),
			layers: {
				L0: { contribution_tps: 0, illustration: [M.bacoAsleep.id, M.bacoAwake.id] },
				L1: { from: before.id, to: l1.id, sameHarness: sameHarness(before, l1) },
				L2: null,
				L3: { from: l1.id, to: l3.id, sameHarness: sameHarness(l1, l3) }
			},
			confidenceInterval: null,
			greedyMd5: { ...MD5, source: MD5_SRC, meaning: 'regression check against our own stored reference, not identity with upstream' },
			qualityVsUpstream: { kld3060: Q, md5DiffSource: SHEET.correctness.md5Diff },
			kldExceptions: KLD_EXCEPTIONS.map((k) => ({ what: k.what[lang], result: k.result[lang], source: k.source }))
		};
		const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `${BRAND.ascii}-${r.reportFile}.json`;
		document.body.append(a);
		a.click();
		a.remove();
		setTimeout(() => URL.revokeObjectURL(url), 1000);
	}
</script>

<svelte:head>
	<title>{t.shell.title(r.title)}</title>
</svelte:head>

<ScreenHead overline={r.overline} title={r.title} lead={r.lead}>
	{#snippet actions()}
		<button type="button" class="btn btn--secondary" onclick={downloadReport} aria-describedby="report-hint">
			<Icon name="download" size={16} />{r.report}
		</button>
		<button
			type="button"
			class="btn btn--ghost"
			onclick={() => (proto.optimisationUndone = !proto.optimisationUndone)}
		>
			<Icon name={proto.optimisationUndone ? 'refresh' : 'undo'} size={16} />{proto.optimisationUndone ? r.redo : r.undo}
		</button>
	{/snippet}
</ScreenHead>
<p id="report-hint" class="small mute report-hint">{r.reportHint}</p>

<div role="status" class="undo-status">
	{#if proto.optimisationUndone}
		<p class="notice notice--warn"><span class="notice__icon" aria-hidden="true">↺</span><span>{r.undone}</span></p>
	{/if}
</div>

<div class="states">
	<span class="overline" id="states-l">{r.statesTitle}</span>
	<div class="segmented" role="radiogroup" aria-labelledby="states-l">
		<label><input type="radio" name="view" value="result" bind:group={view} /><span>{r.states.result}</span></label>
		<label><input type="radio" name="view" value="nochange" bind:group={view} /><span>{r.states.nochange}</span></label>
	</div>
</div>

{#if view === 'nochange'}
	<section class="card nochange" aria-labelledby="nc-h">
		<span class="badge badge--soon">{r.states.nochange}</span>
		<h2 id="nc-h" class="h2">{r.nochangeTitle}</h2>
		<p>{r.nochangeBody}</p>
		<p class="small mute">{r.nochangeNote}</p>
	</section>
{:else}
	<div class="grid">
		<section class="card bars-card" aria-labelledby="bars-h">
			<h2 id="bars-h" class="h3">{r.barsTitle}</h2>
			<ol class="bars" class:dim={proto.optimisationUndone}>
				{#each bars as b (b.key)}
					<li class="row tone-{b.tone}">
						<div class="row-top">
							<span class="row-label">{r.bars[b.key]}</span>
							{#if b.tag === 'same'}<span class="badge badge--measured badge--plain">{r.sameHarness}</span>{/if}
							{#if b.tag === 'other'}<span class="badge badge--estimate badge--plain">{r.otherHarness}</span>{/if}
							{#if b.m}
								<span class="row-val num">{f1(b.m.value)}<span class="u"> t/s</span></span>
							{:else}
								<span class="badge badge--soon">{t.common.soon}</span>
							{/if}
						</div>
						{#if b.m}
							<div class="bar bar--tall" aria-hidden="true"><i style="--v: {b.m.value / scale}"></i></div>
							<p class="row-sub small">
								{wps(b.m.value, 'pl')} ({r.wordsPl}) · {wps(b.m.value, 'en')} ({r.wordsEn})
							</p>
							<Src m={b.m} />
						{:else}
							<div class="bar bar--tall empty" aria-hidden="true"></div>
							<p class="row-sub small mute">{r.l2Empty}</p>
						{/if}
					</li>
				{/each}
			</ol>
			<p class="notice notice--warn"><span class="notice__icon" aria-hidden="true">!</span><span>{r.harnessWarn(f1(before.value), f1(l1.value), f1(l3.value))}</span></p>
			<p class="small mute">{r.noCompetitor}</p>
		</section>

		<aside class="side">
			<section class="card" aria-labelledby="words-h">
				<h2 id="words-h" class="h3">{r.wordsTitle}</h2>
				{#each WORD_LANGS as l (l)}
					<div class="lang-row">
						<p class="overline">{l === 'pl' ? r.wordsPl : r.wordsEn}</p>
						<p class="big num">
							{f1(words(before.value, l))} <span class="arrow" aria-hidden="true">→</span><span class="sr-only">→</span>
							<span class="after">{f1(words(l3.value, l))}</span>
							<span class="u">{t.common.words(Math.round(words(l3.value, l) * 10) / 10)}/s</span>
						</p>
						<p class="small">{r.answer(f1(answerSeconds(500, before.value, l)), f1(answerSeconds(500, l3.value, l)))}</p>
					</div>
				{/each}
				<Src
					m={[before, l3]}
					src={r.tokNote(num(TOK_PER_WORD.pl, lang, 2), num(TOK_PER_WORD.en, lang, 2), f1(before.value), f1(l3.value))}
				/>
			</section>

			<section class="ci" aria-labelledby="ci-h">
				<h2 id="ci-h" class="overline">{r.ciLabel}</h2>
				<p class="ci-val">{r.ciValue}</p>
				<span class="badge badge--soon">{t.common.soon}</span>
			</section>
		</aside>
	</div>

	<section class="block" aria-labelledby="layers-h">
		<h2 id="layers-h" class="overline">{r.layersTitle}</h2>
		<div class="table-wrap">
			<table class="table">
				<caption>{r.layersCaption}</caption>
				<thead>
					<tr>
						<th scope="col">{r.lCol.layer}</th>
						<th scope="col">{r.lCol.what}</th>
						<th scope="col" class="num">{r.lCol.gain}</th>
						<th scope="col">{t.common.source}</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<th scope="row">{r.layers.l0.name}</th>
						<td>{r.layers.l0.what(f1(M.bacoAsleep.value), num(M.bacoAwake.value, lang, 0))}</td>
						<td class="num">{r.gainNone}</td>
						<td class="src">{M.bacoAsleep.source}</td>
					</tr>
					<tr>
						<th scope="row">{r.layers.l1.name}</th>
						<td>{r.layers.l1.what()}</td>
						<td class="num">{gain(before, l1)}</td>
						<td class="src">{before.source}; {l1.source}</td>
					</tr>
					<tr>
						<th scope="row">{r.layers.l2.name}</th>
						<td>{r.layers.l2.what()}</td>
						<td class="num"><span class="badge badge--soon">{r.gainSoon}</span></td>
						<td class="src">—</td>
					</tr>
					<tr>
						<th scope="row">{r.layers.l3.name}</th>
						<td>{r.layers.l3.what()}</td>
						<td class="num">{gain(l1, l3)}<br /><span class="mute small">{r.vsPrev}</span></td>
						<td class="src">{l1.source}; {l3.source}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>
{/if}

<section class="card quality" aria-labelledby="q-h">
	<div class="q-head">
		<h2 id="q-h" class="h3">{r.qualityTitle}</h2>
		<span class="badge badge--ok">{r.qualityBadge}</span>
	</div>
	<p>{r.qualityBody(kld(Q.saluki.ours.v), kld(Q.saluki.noise.v), kld(Q.bonsai.ours.v), kld(Q.bonsai.noise.v))}</p>
	<Src src={[SHEET.correctness.md5Diff, Q.saluki.ours.src]} />
	<p class="small">{r.md5Regression(MD5.qwenPlain, MD5.qwenMtp, MD5.lfm)}</p>
	<p class="notice notice--info"><span class="notice__icon" aria-hidden="true">i</span><span>{r.mtpNote}</span></p>
	<Src src={MD5_SRC} />

	<details class="disclosure">
		<summary>{r.details}</summary>
		<div class="disclosure__body details">
			<p class="small">{r.kldIntro}</p>
			<ul class="kld">
				{#each KLD_EXCEPTIONS as k (k.source)}
					<li>
						<strong>{k.what[lang]}</strong>
						<span class="num small">{k.result[lang]}</span>
						<span class="source">{k.source}</span>
					</li>
				{/each}
			</ul>

			<h3 class="h3 raw-h">{r.rawTitle}</h3>
			<div class="table-wrap">
				<table class="table">
					<caption>{r.rawCaption}</caption>
					<thead>
						<tr>
							<th scope="col">{r.rawCol.what}</th>
							<th scope="col" class="num">{r.rawCol.value}</th>
							<th scope="col">{r.rawCol.harness}</th>
							<th scope="col">{r.rawCol.build}</th>
							<th scope="col">{r.rawCol.source}</th>
						</tr>
					</thead>
					<tbody>
						{#each [before, l1, l3, M.bacoAsleep, M.bacoAwake] as m (m.id)}
							<tr>
								<th scope="row">{m.model} {m.quant}<br /><span class="mute small">{m.config[lang]}</span></th>
								<td class="num">{num(m.value, lang, 1)} {m.unit}</td>
								<td>{m.harness}<br /><span class="mute small">{m.method[lang]}</span></td>
								<td>{m.build}<br /><span class="mute small">{m.backend}</span></td>
								<td class="src">{m.source}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</details>
</section>

<style>
	.report-hint {
		margin: calc(-1 * var(--sp-4)) 0 var(--sp-4);
	}
	.undo-status:empty {
		display: none;
	}
	.undo-status {
		margin-bottom: var(--sp-4);
	}
	.states {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3);
		margin-bottom: var(--sp-5);
	}
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1.7fr) minmax(16rem, 1fr);
		gap: var(--sp-4);
		align-items: start;
	}
	.bars-card {
		display: grid;
		gap: var(--sp-5);
	}
	.bars {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-5);
	}
	.bars.dim .row:not(.tone-before) {
		opacity: 0.45;
	}
	.row {
		display: grid;
		gap: var(--sp-2);
	}
	.row-top {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--sp-2) var(--sp-3);
	}
	.row-label {
		color: var(--text-hi);
		font-weight: var(--fw-medium);
		font-size: var(--fs-sm);
	}
	.row-val {
		margin-left: auto;
		font-size: var(--fs-xl);
		color: var(--text-hi);
		letter-spacing: -0.02em;
	}
	.row-top > .badge--soon {
		margin-left: auto;
	}
	.tone-l3 .row-val {
		color: var(--accent-ink);
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		letter-spacing: 0;
	}
	.tone-before .bar > i {
		--bar-c: var(--before);
	}
	.tone-l1 .bar > i {
		--bar-c: linear-gradient(90deg, var(--heat-1), var(--heat-2));
	}
	.tone-l3 .bar > i {
		box-shadow: 0 0 18px -4px color-mix(in srgb, var(--accent) 60%, transparent);
	}
	.bar.empty {
		background: transparent;
		border: 1px dashed var(--line-strong);
	}
	.row-sub {
		color: var(--text);
	}
	.side {
		display: grid;
		gap: var(--sp-4);
	}
	.side .card {
		display: grid;
		gap: var(--sp-4);
	}
	.lang-row {
		display: grid;
		gap: var(--sp-1);
		padding-bottom: var(--sp-4);
		border-bottom: 1px solid var(--line);
	}
	.big {
		font-size: var(--fs-xl);
		color: var(--text-hi);
		letter-spacing: -0.02em;
	}
	.arrow {
		color: var(--text-mute);
	}
	.after {
		color: var(--accent-ink);
	}
	.ci {
		display: grid;
		gap: var(--sp-2);
		justify-items: start;
		padding: var(--sp-5);
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-lg);
	}
	.ci-val {
		color: var(--text);
		font-size: var(--fs-sm);
	}
	.block {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--sp-3);
		margin-top: var(--sp-8);
	}
	.src {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
		overflow-wrap: anywhere;
	}
	.nochange {
		display: grid;
		gap: var(--sp-3);
		justify-items: start;
		padding: var(--sp-10) var(--sp-8);
		text-align: left;
	}
	.quality {
		display: grid;
		gap: var(--sp-4);
		margin-top: var(--sp-8);
	}
	.q-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3);
	}
	.details {
		display: grid;
		gap: var(--sp-4);
		max-width: none;
	}
	.kld {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.kld li {
		display: grid;
		gap: var(--sp-1);
		padding: var(--sp-3) var(--sp-4);
		border-left: 2px solid var(--warn);
		background: var(--bg-1);
		border-radius: 0 var(--r-sm) var(--r-sm) 0;
	}
	.kld strong {
		color: var(--text-hi);
		font-weight: var(--fw-medium);
	}
	.raw-h {
		margin-top: var(--sp-2);
	}

	@media (max-width: 1000px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
