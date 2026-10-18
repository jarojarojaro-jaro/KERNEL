<script lang="ts">
	/**
	 * Everything measured for one card × model: speed bars and the gain, a replay at real speed,
	 * 500-word stopwatches, instruments (tokens/step, prefill, TTFT, memory, kernels), long context,
	 * where the gain comes from, honesty notes, conditions and the model card. Every number is read
	 * from measurements.ts and carries a SourceTip.
	 */
	import HeatBar from '$lib/fx/HeatBar.svelte';
	import RaceLanes, { type Lane } from '$lib/fx/RaceLanes.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { MODEL_INFO, SHEET, VARIANT_HINT, variantLabel, variantOf, words500, type CardView, type RunView, type Variant, type VariantKey } from '$lib/data/measurements';
	import { fmtGB, fmtSec, fmtTps, localizeDecimals } from '$lib/format';
	import { href, num } from '$lib/i18n';
	import { cardsCopy } from './copy';
	import { duel, KLD_PENDING, roundTo } from './explorer';
	import Ratio from './Ratio.svelte';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import GainStack from './GainStack.svelte';
	import LongCtxChart from './LongCtxChart.svelte';
	import TimeRace from './TimeRace.svelte';
	import { Play } from './play.svelte';

	let { card, run, lang }: { card: CardView; run: RunView; lang: 'pl' | 'en' } = $props();

	const t = $derived(cardsCopy[lang].card);
	const d = $derived(duel(run));
	const info = $derived(MODEL_INFO[run.model]);
	const isPick = $derived(card.pick.model === run.model);
	const bonsai = $derived(run.model === 'bonsai');


	const bars = $derived(run.variants.filter((v) => v.decode));
	const maxDecode = $derived(Math.max(...bars.map((v) => v.decode!.v)) * 1.06);
	const hint = (k: VariantKey) => VARIANT_HINT[k === 'a0' || k === 'a1' ? k : 'ours'];
	const subOf = (v: Variant) =>
		[v.decode!.lo != null ? `[${fmtTps(v.decode!.lo, lang)}–${fmtTps(v.decode!.hi!, lang)}]` : '', v.decode!.paren != null ? `(Ollama ${fmtTps(v.decode!.paren, lang)})` : '']
			.filter(Boolean)
			.join(' ');


	/* ---- race ---- */
	const raceKeys = $derived<VariantKey[]>(bonsai ? ['a1', 'ours', 'alt'] : [run.before, run.ours]);
	const lanes = $derived<Lane[]>(
		raceKeys
			.map((k) => ({ k, v: variantOf(run, k) }))
			.filter((x) => x.v?.decode)
			.map(({ k, v }) => ({ id: k, label: variantLabel(run, k)[lang], sub: k === 'alt' ? undefined : run.quant, tps: v!.decode!.v, hot: k === run.ours }))
	);
	const summary = $derived(`${lanes.map((l) => `${l.label}: ${num(l.tps, lang)} t/s`).join(', ')}. ${run.metric[lang]}`);

	/* ---- stopwatches ---- */
	const words = $derived(
		d
			? (['pl', 'en'] as const).map((wl) => ({ wl, before: words500(d.before, wl), ours: words500(d.ours, wl) })).filter((w) => w.before && w.ours)
			: []
	);

	/* ---- instruments ---- */
	type Metric = 'tokStep' | 'msStep' | 'pp512' | 'pp4096' | 'ttft' | 'vram';
	/** How each instrument is printed: one formatter per kind (format.ts), units glued with nbsp. */
	const show = (k: Metric, n: { v: number; unit?: string }, unit = true) => {
		const s = k === 'ttft' ? fmtSec(n.v, lang) : k === 'vram' ? fmtGB(n.v, n.unit, lang).text : k === 'tokStep' ? num(n.v, lang, 2) : k === 'msStep' ? `${num(n.v, lang, 1)}\u00a0ms` : `${num(n.v, lang, 0)}\u00a0t/s`;
		return unit ? s : s.split('\u00a0')[0];
	};
	const METRICS = $derived<{ k: Metric; label: string; hint: string }[]>([
		{ k: 'tokStep', label: t.tokStep, hint: t.tokStepHint },
		{ k: 'msStep', label: t.msStep, hint: t.msStepHint },
		{ k: 'pp512', label: t.pp512, hint: t.ppHint },
		{ k: 'pp4096', label: t.pp4096, hint: t.ppHint },
		{ k: 'ttft', label: t.ttft, hint: t.ttftHint },
		{ k: 'vram', label: t.vram, hint: run.conditions[lang] }
	]);
	/**
	 * Better or worse, per instrument (higher is better for tokens/step and prefill; lower for step
	 * time, first token, memory, kernels). Within ±3% we say "about the same". A longer step under MTP
	 * is not a loss: each step yields several tokens, so we also print the time per token, computed as
	 * step time ÷ tokens per step and marked as derived.
	 */
	const LOWER: Metric[] = ['msStep', 'ttft', 'vram'];
	type Verdict = 'better' | 'worse' | 'same' | 'step';
	const verdict = (k: Metric | 'kernels', b: number, o: number): Verdict => {
		if (Math.abs(o - b) / b < 0.03) return 'same';
		const lower = k === 'kernels' || LOWER.includes(k as Metric);
		return (o < b) === lower ? 'better' : 'worse';
	};
	const instruments = $derived(
		d
			? METRICS.filter((m) => d.before[m.k] && d.ours[m.k]).map((m) => {
					const b = d.before[m.k]!;
					const o = d.ours[m.k]!;
					const tb = d.before.tokStep?.v ?? 1;
					const to = d.ours.tokStep?.v ?? 1;
					const mtp = m.k === 'msStep' && to > 1.2 && o.v > b.v;
					return {
						...m,
						b,
						o,
						v: mtp ? ('step' as Verdict) : verdict(m.k, b.v, o.v),
						hint: mtp ? t.stepNote(num(to, lang, 1), num(b.v / tb, lang, 1), num(o.v / to, lang, 1)) : m.hint
					};
				})
			: []
	);
	/** One source chip per tile: every figure's file and line, every figure's note. */
	const instSrc = $derived([...instruments.flatMap((m) => [m.b.src, m.o.src]), ...(run.kernels ? [run.kernels.up.src] : [])]);
	const instNote = $derived(
		[...instruments.map((m) => `${m.label}: ${m.k === 'vram' && m.o.unit === 'GiB' ? `${m.hint} (${t.gibNote})` : m.hint}`), ...(run.kernels ? [`${t.kernels}: ${t.kernelsHint}`] : [])].join(' · ')
	);

	/* ---- long context: the sheet's depth table, or tg at 8k/32k (upstream best flags vs ours) ---- */
	const long = $derived.by(() => {
		if (run.longCtx) return { depths: run.longCtx.depths, up: run.longCtx.up, ours: run.longCtx.ours, kv: run.longCtx.kv };
		const up = variantOf(run, run.flags);
		const ours = variantOf(run, run.ours);
		if (up?.tg8k && up.tg32k && ours?.tg8k && ours.tg32k) return { depths: [8192, 32768], up: [up.tg8k, up.tg32k], ours: [ours.tg8k, ours.tg32k], kv: '' };
		return null;
	});

	const checks = $derived(SHEET.checks.filter((c) => c.card === card.id && c.model === run.model));
	const formats = $derived(card.id === 'rtx-5060-ti-16' && run.model === 'lfm25' ? SHEET.lfmFormats5060.filter((f) => f.up && f.ours) : []);
	const q = SHEET.correctness.quality;
	const kldMax = Math.max(...(['saluki', 'bonsai'] as const).flatMap((m) => [q[m].ours.v, q[m].noise.v]));

	/*
	 * Each counter, bar and race plays when its tile enters the view. At rest (SSR, reduced motion,
	 * after a play or an interrupted one) everything shows the final measured values.
	 */
	const speed = new Play(2400);
	/** The 500-word race runs in real time: the slowest answer plus a beat. */
	const race500 = new Play(() => (Math.max(0, ...words.map((w) => w.before!.v)) + 1.5) * 1000);
	/** The conditions as chips: the sheet's own clauses, split at commas and semicolons. */
	const condChips = $derived(run.conditions[lang].split(/;\s*|,\s*(?![^()]*\))/).filter(Boolean));
	const barSrc = $derived(bars.flatMap((v) => [v.decode!.src, ...(v.scorecard ? [`${v.scorecard.file} (${v.scorecard.variant}: ${v.scorecard.decode})`] : [])]));
	const barNote = $derived(`${run.sameHarness ? bars.map((v) => hintNote(v.key)).join(' · ') + ' · ' : ''}${run.metric[lang]}`);
	const hintNote = (k: VariantKey) => (bonsai ? variantLabel(run, k)[lang] : `${variantLabel(run, k)[lang]}: ${hint(k)[lang]}`);
</script>

<div class="bento" style="--mc:{MODEL_STYLE[run.model].color}">
	<!-- ============ SPEED ============ -->
	<div role="group" class="tile speed" aria-labelledby="speed-{run.model}" use:speed.view>
		<h2 id="speed-{run.model}" class="eyebrow"><ModelMark model={run.model} /> {t.speed} · {MODEL_STYLE[run.model].short}</h2>
		<div class="speed-in">
			<div class="speed-head">
				{#if bonsai}
					<p class="honest-title">{t.bonsaiTitle}</p>
				{:else if d?.ratio}
					<p class="ratio">
						<Ratio value={d.ratio} {lang} size="xl" replay={speed.n} />
						<span class="rw">{t.faster}</span>
					</p>
				{:else}
					<p class="warn mono">{t.scriptsWarn}</p>
				{/if}
				<p class="fine sub">{run.sameHarness ? t.speedLede : run.metric[lang]}</p>
				{#if run.note}
					<details class="honest">
						<summary class="mono">{t.honestMore}</summary>
						<p>{localizeDecimals(run.note[lang], lang)}</p>
					</details>
				{/if}
			</div>
			{#if run.sameHarness}
				<div class="bars">
					{#each bars as v, i (v.key)}
						<HeatBar value={roundTo(v.decode!.v, 1)} replay={speed.n} max={maxDecode} label={variantLabel(run, v.key)[lang]} sub={subOf(v)} cold={v.key === run.before} {lang} decimals={1} delay={i * 200} />
					{/each}
					<span class="tile-src"><SourceTip {lang} src={barSrc} note={barNote} /></span>
				</div>
			{:else}
				<!-- different scripts: no bars side by side, each number with its own script -->
				<div class="bars">
					<dl class="apart">
						{#each bars as v (v.key)}
							<div>
								<dt>{variantLabel(run, v.key)[lang]}</dt>
								<dd><span class="big mono">{fmtTps(v.decode!.v, lang)}</span> <span class="u">t/s</span></dd>
							</div>
						{/each}
					</dl>
					<span class="tile-src"><SourceTip {lang} src={barSrc} note={barNote} /></span>
				</div>
			{/if}
		</div>
	</div>

	<!-- ============ 500 WORDS ============ -->
	{#if words.length && d && run.sameHarness}
		<div role="group" class="tile words" aria-labelledby="words-{run.model}" use:race500.view>
			<div class="t-head">
				<h3 id="words-{run.model}" class="h hx-h">{t.words}</h3>
				<span class="t-tools">
					<SourceTip {lang} src={words.flatMap((w) => [w.before!.src, w.ours!.src])} note={words.some((w) => w.ours!.derived) ? t.wordsDerived : `${t.wordsLede} ${run.metric[lang]}`} />
					<button type="button" class="ghost-btn mono" onclick={race500.replay} aria-label={t.wordsRun}><span aria-hidden="true">↻</span></button>
				</span>
			</div>
			{#each words as w (w.wl)}
				<div class="wrow">
					<div class="wl">
						<p class="mono" lang={w.wl}>{w.wl === 'pl' ? t.wordsPl : t.wordsEn}</p>
					</div>
					<TimeRace
						lanes={[
							{ label: variantLabel(run, run.before)[lang], seconds: w.before!.v, hot: false },
							{ label: variantLabel(run, run.ours)[lang], seconds: w.ours!.v, hot: true }
						]}
						run={race500.on}
						runKey={String(race500.n)}
						{lang}
						labels={{ done: t.wordsDone, saved: t.wordsSaved }}
					/>
				</div>
			{/each}
		</div>
	{/if}

	<!-- ============ RACE (same script only) ============ -->
	{#if run.sameHarness && lanes.length > 1}
		<div role="group" class="tile race" aria-labelledby="race-{run.model}">
			<div class="t-head">
				<h3 id="race-{run.model}" class="h hx-h">{t.race}</h3>
				<p class="fine">{t.raceLede}</p>
			</div>
			<RaceLanes {lanes} text={t.raceText} {lang} loop={false} {summary} runKey="{card.id}-{run.model}" />
		</div>
	{/if}

	<!-- ============ INSTRUMENTS ============ -->
	{#if instruments.length || run.kernels}
		<div role="group" class="tile inst-tile" aria-labelledby="inst-{run.model}">
			<div class="t-head">
				<h3 id="inst-{run.model}" class="h hx-h">{t.instruments}</h3>
				<span class="t-tools">
					<p class="fine">{variantLabel(run, run.before)[lang]} → {variantLabel(run, run.ours)[lang]}</p>
					<SourceTip {lang} src={instSrc} note={instNote} />
				</span>
			</div>
			<ul class="inst" role="list">
				{#each instruments as m (m.k)}
					{@const top = Math.max(m.b.v, m.o.v)}
					<li class="cell">
						<p class="cl">{m.label}</p>
						<p class="cv mono">
							<span class="cold-text">{show(m.k, m.b, false)}</span>
							<span class="arr" aria-hidden="true">→</span>
							<span class="hi" class:hx-num={m.v === 'better'}>{show(m.k, m.o)}</span>
						</p>
						<div class="mini" aria-hidden="true">
							<i class="b" style="--w:{(m.b.v / top) * 100}%"></i>
							<i class="o" style="--w:{(m.o.v / top) * 100}%"></i>
						</div>
						<p class="vd vd--{m.v}">{t.verdict[m.v]}</p>
					</li>
				{/each}
				{#if run.kernels}
					{@const kv = verdict('kernels', run.kernels.up.v, run.kernels.ours.v)}
					<li class="cell">
						<p class="cl">{t.kernels}</p>
						<p class="cv mono">
							<span class="cold-text">{num(run.kernels.up.v, lang, 0)}</span>
							<span class="arr" aria-hidden="true">→</span>
							<span class="hi" class:hx-num={kv === 'better'}>{num(run.kernels.ours.v, lang, 0)}</span>
						</p>
						<div class="mini" aria-hidden="true">
							<i class="b" style="--w:100%"></i>
							<i class="o" style="--w:{(run.kernels.ours.v / run.kernels.up.v) * 100}%"></i>
						</div>
						<p class="vd vd--{kv}">{t.verdict[kv]}</p>
					</li>
				{/if}
			</ul>
		</div>
	{/if}

	<!-- ============ LONG CONTEXT ============ -->
	{#if long}
		<div role="group" class="tile long" aria-labelledby="long-{run.model}">
			<div class="t-head">
				<h3 id="long-{run.model}" class="h hx-h">{t.longCtx}</h3>
				<SourceTip {lang} src={[...new Set([...long.up.map((n) => n.src), ...long.ours.map((n) => n.src)])]} note="{t.longCtxLede}{long.kv ? ` ${long.kv}.` : ''}" />
			</div>
			<LongCtxChart depths={long.depths} up={long.up} ours={long.ours} {lang} title="{t.longCtx}, {info.name}" labels={{ up: bonsai ? variantLabel(run, run.flags)[lang] : t.upstream, ours: t.ours, depth: t.depth }} />
		</div>
	{/if}

	<!-- ============ WHERE THE GAIN COMES FROM ============ -->
	{#if run.gain?.flags && run.gain.engine && run.gain.total && d?.flags?.decode}
		<div role="group" class="tile gain" aria-labelledby="why-{run.model}">
			<div class="t-head">
				<h3 id="why-{run.model}" class="h hx-h">{t.why}</h3>
			</div>
			<GainStack gain={run.gain} text={run.gainText?.[lang]} before={d.before.decode!} flags={d.flags.decode} ours={d.ours.decode!} {lang} labels={{ before: variantLabel(run, run.before)[lang], flags: t.whyFlags, engine: t.whyEngine, total: t.gain, none: t.whyNone }} />
		</div>
	{/if}

	<!-- ============ OTHER LFM FORMATS (5060 Ti) ============ -->
	{#if formats.length}
		<div role="group" class="tile formats-tile" aria-labelledby="fmt-{run.model}">
			<div class="t-head">
				<h3 id="fmt-{run.model}" class="h hx-h">{t.formats}</h3>
				<span class="t-tools">
					<p class="fine">{t.formatsLede}</p>
					<SourceTip {lang} src={formats.flatMap((f) => [f.gb.src, f.up!.src, f.kld.src])} note={formats.map((f) => `${f.file}, ${fmtGB(f.gb.v, 'GB', lang).text}`).join(' · ')} />
				</span>
			</div>
			<ul class="formats" role="list">
				{#each formats as f (f.file)}
					<li>
						<p class="fn">{lang === 'en' ? f.file.replace('oficjalny', 'official').replace('społeczność', 'community') : f.file}</p>
						<p class="mono fv"><span class="cold-text">{fmtTps(f.up!.v, lang)}</span> → <span class="hi">{fmtTps(f.ours!.v, lang)}</span>{'\u00a0'}t/s</p>
						<p class="mono fk">{t.formatsKld} {num(f.kld.v, lang, 3)}{#if f.kld.v > 1}<span class="bad"> · {t.formatsBad}</span>{/if}</p>
						{#if f.md5Same}<div class="frow"><span class="badge mono">{t.md5Same}</span></div>{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- ============ QUALITY ============ -->
	<div role="group" class="tile quality" aria-labelledby="q-{run.model}">
		<p class="badge-q"><span class="chk" aria-hidden="true">✓</span> {t.quality}</p>
		<h3 id="q-{run.model}" class="sr-only">{t.honesty}</h3>
		<dl class="kld">
			{#each ['saluki', 'bonsai'] as const as m (m)}
				<div class="kpair">
					<dt class="mono"><ModelMark model={m} /> {MODEL_STYLE[m].short}</dt>
					<dd>
						<span class="kb ours" style="--w:{(q[m].ours.v / kldMax) * 100}%"></span>
						<span class="kv mono">{t.kldOurs} <b>{num(q[m].ours.v, lang, 5)}</b></span>
					</dd>
					<dd>
						<span class="kb noise" style="--w:{(q[m].noise.v / kldMax) * 100}%"></span>
						<span class="kv mono">{t.kldNoise} {num(q[m].noise.v, lang, 5)}</span>
					</dd>
				</div>
			{/each}
		</dl>
		{#if KLD_PENDING.includes(run.model)}<p class="pending mono">{t.kldPending(MODEL_STYLE[run.model].short)}</p>{/if}
		<p class="row-links">
			<a href={href(lang, '/methodology#quality')}>{t.methodology} →</a>
			<SourceTip {lang} src={[SHEET.correctness.md5Diff, q.saluki.ours.src]} note={t.qualityBody} />
		</p>
	</div>

	<!-- ============ CONDITIONS ============ -->
	<div role="group" class="tile cond" aria-labelledby="c-{run.model}">
		<h3 id="c-{run.model}" class="eyebrow">{t.conditions}</h3>
		<ul class="chips" role="list">
			{#each condChips as c (c)}<li class="chip mono">{localizeDecimals(c, lang)}</li>{/each}
			<li class="chip mono metric">{run.sameHarness ? 'spec_sweep · T=1 · 400 tok' : t.scriptsWarn}</li>
		</ul>
		<SourceTip
			{lang}
			src={[run.conditionsSrc, card.hwSrc, ...checks.map((c) => c.file)]}
			note={[run.metric[lang], card.hwLine ? localizeDecimals(card.hwLine[lang], lang) : '', ...checks.map((c) => t.checkNote(num(c.sheet, lang), num(c.scorecard, lang, 2)))].filter(Boolean).join(' · ')}
		/>
	</div>

	<!-- ============ MODEL ============ -->
	<div role="group" class="tile model" aria-labelledby="m-{run.model}">
		<h3 id="m-{run.model}" class="m-name"><ModelMark model={run.model} size="0.9em" /> {#each info.name.split(' ') as w, i (i)}{i ? ' ' : ''}<span class="nw">{w}</span>{/each}</h3>
		{#if isPick}<p class="pick"><span class="star" aria-hidden="true">★</span> {t.pickBadge}</p>{/if}
		<p class="body">{info.what[lang]}</p>
		<ul class="chips" role="list">
			<li class="chip mono">{run.quant}</li>
			{#if run.file}<li class="chip mono">{fmtGB(run.file.v, run.file.unit, lang).text}</li>{/if}
			{#each info.good as g (g.en)}<li class="chip">{g[lang]}</li>{/each}
		</ul>
		<p class="lic fine">{t.license}: {info.license[lang]}</p>
		<SourceTip {lang} src={[info.src, info.licenseSrc, ...(run.file ? [run.file.src] : [])]} note={isPick ? localizeDecimals(card.pick.why[lang], lang) : ''} />
	</div>
</div>

<style>
	/* ---------- bento: related data in one dense grid of tiles ---------- */
	.bento {
		display: grid;
		grid-template-columns: repeat(12, minmax(0, 1fr));
		gap: var(--sp-3);
		padding-top: var(--sp-4);
	}
	.tile {
		position: relative;
		min-width: 0;
		display: grid;
		gap: var(--sp-4);
		align-content: start;
		padding: clamp(1rem, 2vw, 1.6rem);
		border: 1px solid rgb(255 122 26 / 0.2);
		border-radius: var(--r-xl);
		background:
			radial-gradient(90% 60% at 0% 0%, color-mix(in srgb, var(--mc) 8%, transparent), transparent 60%),
			radial-gradient(80% 70% at 100% 100%, rgb(255 122 26 / 0.08), transparent 60%),
			linear-gradient(180deg, rgb(17 15 14 / 0.94), rgb(7 7 8 / 0.94));
		box-shadow: var(--shadow-2);
		overflow: hidden;
		transition:
			border-color var(--dur-3),
			box-shadow var(--dur-3) var(--ease-out);
	}
	/* hover lights the rim and raises an ember glow under the tile */
	.tile:is(:hover, :focus-within) {
		border-color: rgb(255 122 26 / 0.6);
		box-shadow:
			var(--shadow-2),
			0 0 30px -10px rgb(255 122 26 / 0.4),
			0 26px 60px -30px rgb(226 64 28 / 0.75);
	}
	/* a heat line along the bottom of every tile, the model colour along the top */
	.tile::after {
		content: '';
		position: absolute;
		inset: auto 8% 0;
		height: 1px;
		background: var(--hx-line-c);
		opacity: 0.55;
		pointer-events: none;
		transition: opacity var(--dur-3);
	}
	.tile:is(:hover, :focus-within)::after {
		opacity: 1;
	}
	/* a thin model-colour accent along the top of every tile */
	.tile::before {
		content: '';
		position: absolute;
		inset: 0 0 auto;
		height: 2px;
		background: linear-gradient(90deg, var(--mc), transparent 70%);
		opacity: 0.7;
	}
	.speed {
		grid-column: span 7;
	}
	.words {
		grid-column: span 5;
	}
	.race,
	.inst-tile,
	.formats-tile {
		grid-column: 1 / -1;
	}
	.long {
		grid-column: span 7;
	}
	.gain {
		grid-column: span 5;
	}
	.quality,
	.cond,
	.model {
		grid-column: span 4;
	}
	/* no speed-words pairing (different scripts): speed takes the row */
	.speed:last-child,
	.speed:not(:has(+ .words)) {
		grid-column: 1 / -1;
	}
	.long:not(:has(+ .gain)) {
		grid-column: 1 / -1;
	}
	@media (max-width: 64rem) {
		.speed,
		.words,
		.long,
		.gain {
			grid-column: 1 / -1;
		}
		.quality,
		.cond {
			grid-column: span 6;
		}
		.model {
			grid-column: 1 / -1;
		}
	}
	@media (max-width: 40rem) {
		.bento {
			gap: var(--sp-2);
		}
		.quality,
		.cond {
			grid-column: 1 / -1;
		}
	}
	/* source chips keep their own width inside grid tiles */
	.tile > :global(.src-btn) {
		justify-self: start;
	}
	.t-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-2) var(--sp-4);
	}
	.t-head .fine {
		margin: 0;
	}
	.t-tools {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
	}
	.h {
		margin: 0;
		font-size: var(--fs-lg);
		font-weight: 750;
		font-stretch: 108%;
		letter-spacing: -0.015em;
		color: var(--text-hi);
	}
	.eyebrow {
		margin: 0;
		gap: 0.5rem;
	}
	.nw {
		white-space: nowrap;
	}

	/* ---------- speed ---------- */
	.speed-in {
		display: grid;
		grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
		align-items: center;
		gap: var(--sp-5) clamp(1.5rem, 3vw, 3rem);
	}
	@media (max-width: 52rem) {
		.speed-in {
			grid-template-columns: 1fr;
		}
	}
	.speed-head {
		display: grid;
		gap: var(--sp-3);
		align-content: start;
	}
	.ratio {
		margin: 0;
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0 var(--sp-3);
		line-height: 0.85;
	}
	.ratio :global(.rx--xl) {
		font-size: clamp(4rem, 2rem + 6vw, 8rem);
	}
	.rw {
		font-size: var(--fs-lg);
		font-weight: 700;
		color: var(--text-hi);
	}
	.sub {
		margin: 0;
	}
	.honest-title {
		margin: 0;
		font-size: var(--fs-2xl);
		font-weight: 800;
		font-stretch: 108%;
		line-height: 1.05;
		letter-spacing: -0.03em;
		color: var(--text-hi);
	}
	.honest {
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.honest summary {
		cursor: pointer;
		width: fit-content;
		padding: 0.3rem 0.65rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-hi);
		list-style: none;
	}
	.honest summary:hover {
		border-color: var(--heat-3);
	}
	.honest summary::-webkit-details-marker {
		display: none;
	}
	.honest p {
		margin: var(--sp-2) 0 0;
		padding-left: var(--sp-3);
		border-left: 2px solid var(--heat-2);
		line-height: 1.5;
		max-width: 52ch;
	}
	.bars {
		display: grid;
		gap: var(--sp-4);
	}
	/* one source chip per tile, under its figures */
	.tile-src {
		justify-self: end;
	}
	.warn {
		margin: 0;
		display: inline-block;
		padding: 0.35rem 0.7rem;
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-sm);
		color: var(--text-hi);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		justify-self: start;
	}
	.apart {
		margin: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
		gap: var(--sp-3);
	}
	.apart div:hover {
		border-color: rgb(255 122 26 / 0.55);
	}
	.apart div {
		padding: var(--sp-4);
		border: 1px solid rgb(255 122 26 / 0.16);
		transition:
			border-color var(--dur-2),
			background-color var(--dur-2);
		border-radius: var(--r-lg);
	}
	.apart dt {
		color: var(--text);
		font-weight: 600;
		font-size: var(--fs-sm);
	}
	.apart dd {
		margin: var(--sp-2) 0 0;
	}
	.apart .big {
		font-size: var(--fs-2xl);
		color: var(--text-hi);
	}
	.u {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}

	/* ---------- words ---------- */
	.wrow {
		display: grid;
		gap: var(--sp-2);
	}
	.wl {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
	}
	.wl p {
		margin: 0;
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	@media (min-width: 40.01rem) {
		.words :global(.lane) {
			grid-template-columns: minmax(6rem, 8rem) minmax(0, 1fr) 6.5rem;
		}
	}
	.words :global(.target) {
		font-size: var(--fs-xl);
	}
	.ghost-btn {
		display: inline-grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		border: 1px solid var(--line-strong);
		border-radius: 50%;
		background: transparent;
		color: var(--text);
		font-size: var(--fs-sm);
		cursor: pointer;
	}
	.ghost-btn:hover {
		color: var(--text-hi);
		border-color: var(--heat-3);
		box-shadow: 0 0 22px -6px rgb(255 122 26 / 0.6);
	}

	/* ---------- instruments: dense cells; the last row stretches, no orphans ---------- */
	.inst {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.cell:hover {
		border-color: rgb(255 122 26 / 0.55);
		background: rgb(255 122 26 / 0.05);
	}
	.cell {
		flex: 1 1 13rem;
		display: grid;
		gap: var(--sp-2);
		align-content: start;
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid rgb(255 122 26 / 0.16);
		transition:
			border-color var(--dur-2),
			background-color var(--dur-2);
		border-radius: var(--r-lg);
		background: rgb(255 255 255 / 0.015);
	}
	.cl {
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.cv {
		margin: 0;
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0.35rem;
		font-size: var(--fs-md);
	}
	.hi {
		color: var(--text-hi);
		font-weight: 600;
	}
	.arr {
		color: var(--text-mute);
		font-size: var(--fs-xs);
	}
	.mini {
		display: grid;
		gap: 3px;
	}
	.mini i {
		display: block;
		height: 3px;
		width: var(--w);
		border-radius: 2px;
	}
	.mini .b {
		background: var(--before);
	}
	.mini .o {
		background: var(--text-hi);
	}
	/* a better "after" bar runs hot; worse or unchanged stays bone */
	.cell:has(.vd--better) .mini .o {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 8px rgb(255 122 26 / 0.5);
	}
	/* better / worse: words and an arrow, bone for better, steel for worse; never heat */
	.vd {
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.vd--better {
		color: var(--hx-ink);
	}
	.vd--worse {
		color: var(--before);
	}
	.vd--same,
	.vd--step {
		color: var(--text-mute);
	}

	/* ---------- formats ---------- */
	.formats {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr));
		gap: var(--sp-2);
	}
	.formats li:hover {
		border-color: rgb(255 122 26 / 0.55);
		background: rgb(255 122 26 / 0.05);
	}
	.formats li {
		display: grid;
		gap: var(--sp-2);
		padding: var(--sp-4);
		border: 1px solid rgb(255 122 26 / 0.16);
		transition:
			border-color var(--dur-2),
			background-color var(--dur-2);
		border-radius: var(--r-lg);
	}
	.formats p {
		margin: 0;
	}
	.fn {
		font-weight: 650;
		color: var(--text-hi);
	}
	.fv {
		font-size: var(--fs-md);
	}
	.fk {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.bad {
		color: var(--text-hi);
		text-decoration: underline dashed var(--line-strong);
		text-underline-offset: 3px;
	}
	.frow {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
	}
	.badge {
		padding: 0.25rem 0.6rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		font-size: var(--fs-2xs);
		color: var(--text);
	}

	/* ---------- quality ---------- */
	.badge-q {
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.6rem;
		font-size: var(--fs-md);
		font-weight: 700;
		line-height: 1.25;
		color: var(--text-hi);
	}
	.chk {
		display: inline-grid;
		place-items: center;
		flex: none;
		width: 1.8rem;
		height: 1.8rem;
		border-radius: 50%;
		background: var(--ok-soft);
		border: 1px solid var(--ok);
		color: var(--ok-ink);
		font-size: var(--fs-sm);
	}
	.kld {
		margin: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.kpair {
		display: grid;
		gap: 0.3rem;
	}
	.kpair dt {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.kpair dd {
		margin: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--sp-2);
	}
	.kb {
		height: 6px;
		width: var(--w);
		border-radius: 3px;
	}
	.kb.ours {
		background: var(--text-hi);
	}
	.kb.noise {
		background: var(--before);
	}
	.kv {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		white-space: nowrap;
	}
	.kv b {
		color: var(--text-hi);
		font-weight: 600;
	}
	.pending {
		margin: 0;
		padding: 0.35rem 0.6rem;
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-sm);
		font-size: var(--fs-2xs);
		color: var(--text-hi);
	}
	.row-links {
		margin: 0;
		display: flex;
		gap: var(--sp-3);
		align-items: center;
	}
	.row-links a {
		color: var(--text-hi);
		font-weight: 600;
		font-size: var(--fs-sm);
	}

	/* ---------- conditions & model ---------- */
	.chips {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.chip:hover {
		border-color: rgb(255 122 26 / 0.55);
	}
	.chip {
		padding: 0.3rem 0.65rem;
		border: 1px solid rgb(255 122 26 / 0.16);
		transition:
			border-color var(--dur-2),
			background-color var(--dur-2);
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.02);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	.chip.metric {
		border-style: dashed;
	}
	.m-name {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0 0.5rem;
		font-size: var(--fs-xl);
		font-weight: 800;
		font-stretch: 108%;
		letter-spacing: -0.02em;
		line-height: 1.1;
		color: var(--text-hi);
	}
	.pick {
		margin: 0;
		width: fit-content;
		padding: 0.3rem 0.7rem;
		border: 1px solid var(--mc);
		border-radius: var(--r-pill);
		background: color-mix(in srgb, var(--mc) 12%, transparent);
		font-size: var(--fs-xs);
		font-weight: 650;
		color: var(--text-hi);
	}
	.star {
		color: var(--mc);
	}
	.body {
		margin: 0;
		color: var(--text);
		font-size: var(--fs-sm);
		line-height: 1.5;
	}
	.lic {
		margin: 0;
	}
	.model {
		background:
			radial-gradient(90% 70% at 100% 0%, color-mix(in srgb, var(--mc) 14%, transparent), transparent 60%),
			linear-gradient(180deg, var(--bg-1), #070708);
	}
</style>
