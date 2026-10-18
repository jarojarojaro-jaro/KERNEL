<script lang="ts">
	/**
	 * "What fits": every row shares ONE memory axis (GB). The card's memory is the slot left of the
	 * white edge line; the zone right of it is memory the card does not have. A measured model drops in
	 * (gravity, short settle) in its identity colour: the weights file solid, everything else our
	 * engine allocated (KV cache, context, buffers) lighter, up to the measured memory used. A file that
	 * does not fit (estimate from our formula, labelled) is desaturated, hatched and red-outlined, and
	 * runs past the edge. Colour is always paired with the model's shape mark and name.
	 */
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { MODEL_INFO, variantOf, type CardView } from '$lib/data/measurements';
	import { fmtGB } from '$lib/format';
	import { currentLang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { cardsCopy } from './copy';
	import EstTag from './EstTag.svelte';
	import { EST_SRC, familyOf, ghosts } from './explorer';
	import { Play } from './play.svelte';

	let { card }: { card: CardView } = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].card);

	/*
	 * Text: measured memory in decimal GB (format.ts; GiB figures are converted and the source tip
	 * says so). Bars: each figure against the card's memory as the sheet and the estimator count it,
	 * so a bar's length is the true share of the card. Estimates for files that do not fit are given
	 * as a share of the card's memory.
	 */
	const g = (v: number, unit = 'GB') => fmtGB(v, unit, lang).text;
	const rows = $derived(card.runs.map((r) => ({ r, used: variantOf(r, r.ours)?.vram, file: r.file })));
	const over = $derived(ghosts(card.vramGB).map((x) => ({ ...x, fam: familyOf(x.model.id), lo: x.need.lo, hi: x.need.hi })));
	const share = (v: number) => `${Math.round((v / card.vramGB) * 100)}`;
	/** Shared axis: the card plus room for the largest file that does not fit, in 4 GB steps. */
	const axis = $derived(Math.ceil((Math.max(card.vramGB, ...over.map((x) => x.hi)) * 1.04) / 4) * 4);
	const pct = (v: number) => (v / axis) * 100;
	/** The drop plays when the panel enters the view; at rest (and on SSR) the blocks sit in place. */
	const drop = new Play(() => (rows.length + over.length) * 200 + 1600);
	/** One source chip for the panel: every measured row, and the estimate for files that do not fit. */
	const fitSrc = $derived([
		...rows.flatMap((row) => [...(row.file ? [row.file.src] : []), ...(row.used ? [row.used.src] : []), row.r.conditionsSrc]),
		...(over.length ? [EST_SRC, 'app/landing/src/lib/data/models.json'] : [])
	]);
	const fitNote = $derived(
		[
			...rows.map((row) => `${MODEL_STYLE[row.r.model].short}: ${row.r.conditions[lang]}`),
			rows.some((row) => row.used?.unit === 'GiB') ? t.gibNote : '',
			over.length ? t.fitNoNote : ''
		]
			.filter(Boolean)
			.join(' · ')
	);
	const ticks = $derived(Array.from({ length: axis / 4 + 1 }, (_, i) => i * 4));
</script>

<section class="fit wrap hx-surface hx-ring" aria-labelledby="fit-title" use:drop.view>
	<header class="intro">
		<h2 id="fit-title" class="h hx-grad">{t.fitTitle}</h2>
		<p class="fine">{t.fitLede(card.vramGB)}</p>
		<span class="intro-src"><SourceTip {lang} src={fitSrc} note={fitNote} /></span>
		<button type="button" class="replay mono" onclick={drop.replay}><span aria-hidden="true">↻</span> {t.fitReplay}</button>
	</header>

	<div class="bars" class:play={drop.on} style="--card:{pct(card.vramGB)}%; --cells:{axis}">
		<div class="row head" aria-hidden="true">
			<span></span>
			<div class="lane">
				<span class="cap mono" style="left:{pct(card.vramGB)}%">{card.short} · {card.vramGB}{'\u00a0'}GB</span>
				{#if over.length}<span class="beyond mono" style="left:{pct(card.vramGB)}%">{t.fitBeyond}</span>{/if}
			</div>
		</div>
		{#key drop.n}
			{#each rows as row, i (row.r.model)}
				{@const main = row.used?.v ?? row.file?.v ?? 0}
				<div class="row" style="--d:{i * 200}ms; --mc:{MODEL_STYLE[row.r.model].color}">
					<div class="label">
						<span class="m"><ModelMark model={row.r.model} /> {MODEL_STYLE[row.r.model].short}</span>
						<span class="q mono">{row.r.quant}</span>
					</div>
					<div class="lane">
						<div class="track" role="img" aria-label="{MODEL_INFO[row.r.model].name} {row.r.quant}: {row.file ? `${t.fitFile} ${g(row.file.v, row.file.unit)}` : ''}{row.file && row.used ? ', ' : ''}{row.used ? `${t.fitUsed} ${g(row.used.v, row.used.unit)}` : ''} / {card.vramGB} GB">
							<div class="block" style="width:calc({pct(main)}% - 4px)">
								{#if row.used && row.file}<div class="weights" style="width:{Math.min(100, (row.file.v / row.used.v) * 100).toFixed(2)}%"></div>{/if}
							</div>
							<span class="val mono" style="left:{pct(main)}%">{row.used ? g(row.used.v, row.used.unit) : row.file ? g(row.file.v, row.file.unit) : ''}</span>
						</div>
						<div class="facts mono">
							{#if row.file}<span class="chip"><i class="key w"></i>{t.fitFile} <b>{g(row.file.v, row.file.unit)}</b></span>{/if}
							{#if row.used}<span class="chip"><i class="key u"></i>{t.fitUsed} <b>{g(row.used.v, row.used.unit)}</b></span>{/if}
						</div>
					</div>
				</div>
			{/each}
			{#each over as x, i (x.model.id)}
				<div class="row ghost" style="--d:{(rows.length + i) * 200}ms; --mc:{x.fam ? MODEL_STYLE[x.fam].color : 'var(--before)'}">
					<div class="label">
						<span class="m">{#if x.fam}<ModelMark model={x.fam} />{/if} {x.model.name}</span>
						<span class="q mono">{x.model.quant}</span>
					</div>
					<div class="lane">
						<div class="track" role="img" aria-label="{x.model.name} {x.model.quant}: {t.fitNo}, {t.fitNoNote} ≈ {t.fitShare(share(x.lo), share(x.hi))}">
							<div class="block" style="width:calc({pct(x.hi)}% - 4px)">
								<span class="no mono">✕ {t.fitNo}</span>
							</div>
						</div>
						<div class="facts mono">
							<span class="chip">{t.fitFile} <b>{g(x.model.sizeGB)}</b></span>
							<span class="chip">≈{'\u00a0'}<b>{t.fitShare(share(x.lo), share(x.hi))}</b></span>
							<EstTag text={cardsCopy[lang].gallery.estimateShort} />
						</div>
					</div>
				</div>
			{/each}
		{/key}
		<div class="row axis" aria-hidden="true">
			<span></span>
			<div class="lane">
				{#each ticks as v, i (v)}<span class="tick mono" style="left:{pct(v)}%">{v}{i === ticks.length - 1 ? '\u00a0GB' : ''}</span>{/each}
			</div>
		</div>
	</div>
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.fit {
		display: grid;
		gap: var(--sp-5);
		padding: clamp(1.5rem, 3vw, 2.5rem);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background:
			radial-gradient(80% 60% at 0% 0%, rgb(255 255 255 / 0.03), transparent 60%),
			linear-gradient(180deg, var(--bg-1), #070708);
	}
	.intro {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-5);
	}
	.intro-src {
		margin-left: auto;
	}
	.h {
		margin: 0;
		font-size: var(--fs-2xl);
		font-weight: 800;
		font-stretch: 112%;
		letter-spacing: -0.02em;
		color: var(--text-hi);
	}
	.intro .fine {
		margin: 0;
		flex: 1 1 18rem;
	}
	.bars {
		display: grid;
		gap: var(--sp-5);
	}
	.row {
		display: grid;
		grid-template-columns: minmax(8rem, 11rem) minmax(0, 1fr);
		gap: var(--sp-2) var(--sp-5);
		align-items: start;
	}
	.label {
		display: grid;
		gap: 0.15rem;
		padding-top: 1.9rem;
	}
	.m {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-weight: 700;
		font-stretch: 108%;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.q {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.lane {
		position: relative;
		display: grid;
		gap: var(--sp-2);
		min-width: 0;
	}
	.head .lane,
	.axis .lane {
		height: 1.2rem;
	}
	.cap,
	.beyond {
		position: absolute;
		bottom: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		white-space: nowrap;
	}
	.cap {
		transform: translateX(calc(-100% - 0.6rem));
		color: var(--text-hi);
	}
	.beyond {
		transform: translateX(0.7rem);
		color: var(--text-mute);
	}
	.track {
		position: relative;
		margin-top: 1.3rem;
		height: 2.6rem;
		border-radius: var(--r-md);
		background:
			repeating-linear-gradient(90deg, transparent 0 calc(100% / var(--cells) - 1px), rgb(255 255 255 / 0.05) calc(100% / var(--cells) - 1px) calc(100% / var(--cells))),
			#08080a;
		box-shadow: inset 0 0 0 1px var(--line);
	}
	/* beyond the card: memory it does not have */
	.track::before {
		content: '';
		position: absolute;
		left: var(--card);
		right: 0;
		top: 0;
		bottom: 0;
		border: 1px dashed var(--line);
		border-left: 0;
		border-radius: 0 var(--r-md) var(--r-md) 0;
		background: #050506;
	}
	/* the card's edge: a line at the same x on every row */
	.track::after {
		content: '';
		position: absolute;
		left: var(--card);
		top: -0.4rem;
		bottom: -0.4rem;
		margin-left: -1px;
		border-left: 2px solid var(--text-hi);
		pointer-events: none;
	}
	/* fits: the model's colour, vivid; weights solid, the rest of the engine's memory lighter */
	.block {
		position: absolute;
		top: 3px;
		bottom: 3px;
		left: 2px;
		border-radius: calc(var(--r-md) - 3px);
		background: linear-gradient(180deg, color-mix(in srgb, var(--mc) 55%, transparent), color-mix(in srgb, var(--mc) 35%, transparent));
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.18) inset,
			0 0 22px -6px color-mix(in srgb, var(--mc) 60%, transparent);
		overflow: hidden;
		display: flex;
		align-items: center;
	}
	.weights {
		position: absolute;
		inset: 0 auto 0 0;
		background: linear-gradient(180deg, color-mix(in srgb, var(--mc) 100%, #fff 18%), var(--mc));
		box-shadow: 1px 0 0 rgb(0 0 0 / 0.45);
	}
	.val {
		position: absolute;
		bottom: calc(100% + 0.3rem);
		transform: translateX(-100%);
		font-size: var(--fs-xs);
		font-weight: 650;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.facts {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.chip {
		display: inline-flex;
		align-items: center;
		padding: 0.2rem 0.55rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: var(--bg-1);
	}
	.chip b {
		margin-left: 0.3rem;
		color: var(--text-hi);
		font-weight: 600;
	}
	.key {
		display: inline-block;
		width: 0.6rem;
		height: 0.6rem;
		margin-right: 0.4rem;
		border-radius: 2px;
	}
	.key.w {
		background: var(--mc);
	}
	.key.u {
		background: color-mix(in srgb, var(--mc) 45%, transparent);
	}

	/* does not fit: desaturated, hatched (hatching = estimate / does not fit), red outline */
	.ghost .block {
		background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--mc) 30%, #3a3a40) 0 6px, #141417 6px 12px);
		border: 1.5px solid var(--danger);
		box-shadow: none;
	}
	.no {
		position: relative;
		padding: 0 0.75rem;
		font-size: var(--fs-xs);
		font-weight: 650;
		color: var(--danger-ink);
		white-space: nowrap;
	}

	.axis .tick {
		position: absolute;
		top: 0;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		transform: translateX(-50%);
	}
	.axis .tick:first-child {
		transform: none;
	}
	.axis .tick:last-child {
		transform: translateX(-100%);
	}

	.replay {
		min-height: 2.5rem;
		padding: 0 1rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: transparent;
		color: var(--text);
		font-size: var(--fs-2xs);
		cursor: pointer;
		transition:
			border-color var(--dur-2),
			box-shadow var(--dur-2);
	}
	.replay:hover {
		color: var(--text-hi);
		border-color: var(--heat-3);
		box-shadow: 0 0 22px -6px rgb(255 122 26 / 0.6);
	}

	@media (prefers-reduced-motion: no-preference) {
		/* only while a play runs: at rest the blocks and labels are in their final place */
		.play .val {
			animation: val-in 0.4s var(--ease-out) calc(var(--d) + 0.8s) both;
		}
		.play .row:not(.ghost) .block {
			animation: drop 1s linear var(--d) both;
		}
		.play .ghost .block {
			animation: jam 1.4s var(--ease-out) var(--d) both;
		}
	}
	@keyframes val-in {
		from {
			opacity: 0;
		}
	}
	@keyframes drop {
		0% {
			opacity: 0;
			transform: translateY(-190%);
			animation-timing-function: cubic-bezier(0.5, 0, 0.75, 0);
		}
		40% {
			opacity: 1;
			transform: translateY(0);
			animation-timing-function: cubic-bezier(0.2, 0.7, 0.4, 1);
		}
		58% {
			transform: translateY(-14%);
			animation-timing-function: cubic-bezier(0.5, 0, 0.75, 0);
		}
		74% {
			transform: translateY(0);
			animation-timing-function: cubic-bezier(0.2, 0.7, 0.4, 1);
		}
		86% {
			transform: translateY(-3%);
			animation-timing-function: cubic-bezier(0.5, 0, 0.75, 0);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}
	@keyframes jam {
		0% {
			opacity: 0;
			transform: translateX(-40%);
		}
		45% {
			opacity: 1;
			transform: translateX(0);
		}
		55% {
			transform: translateX(-1.6%);
		}
		65% {
			transform: translateX(0.8%);
		}
		75% {
			transform: translateX(-0.8%);
		}
		85% {
			transform: translateX(0.3%);
		}
		100% {
			opacity: 1;
			transform: translateX(0);
		}
	}
	@media (max-width: 48rem) {
		.fit {
			padding: var(--sp-4);
		}
		.row {
			grid-template-columns: 1fr;
		}
		.row.head > span:first-child,
		.row.axis > span:first-child {
			display: none;
		}
		.label {
			padding-top: 0;
			grid-template-columns: auto auto;
			justify-content: start;
			gap: 0.6rem;
			align-items: baseline;
		}
		.beyond {
			display: none;
		}
	}
	@media (max-width: 30rem) {
		.axis .tick:nth-child(even):not(:last-child) {
			display: none;
		}
	}
</style>
