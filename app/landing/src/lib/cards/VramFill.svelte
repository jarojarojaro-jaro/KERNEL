<script lang="ts">
	/**
	 * "What fits": the measured models that fit this card, every row on ONE memory axis that ends at
	 * the card's memory (GB). A model drops in (gravity, short settle) in its identity colour: the
	 * weights file solid, everything else our engine allocated (KV cache, context, buffers) lighter,
	 * up to the measured memory used. Colour is always paired with the model's shape mark and name.
	 * Sources live in the detail tables below.
	 */
	import { MODEL_INFO, variantOf, type CardView } from '$lib/data/measurements';
	import { fmtGB } from '$lib/format';
	import { currentLang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { cardsCopy } from './copy';
	import { Play } from './play.svelte';

	let { card }: { card: CardView } = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].card);

	/*
	 * Text: measured memory in decimal GB (format.ts; GiB figures are converted). Bars: each figure
	 * against the card's memory as the sheet counts it, so a bar's length is the true share of the card.
	 */
	const g = (v: number, unit = 'GB') => fmtGB(v, unit, lang).text;
	const rows = $derived(card.runs.map((r) => ({ r, used: variantOf(r, r.ours)?.vram, file: r.file })));
	/** The axis is the card: its memory, ticked every 4 GB (2 GB when that does not divide it). */
	const axis = $derived(card.vramGB);
	const step = $derived(axis % 4 === 0 ? 4 : 2);
	const pct = (v: number) => Math.min(100, (v / axis) * 100);
	/** The drop plays when the panel enters the view; at rest (and on SSR) the blocks sit in place. */
	const drop = new Play(() => rows.length * 200 + 1600);
	const ticks = $derived(Array.from({ length: Math.floor(axis / step) + 1 }, (_, i) => i * step));
</script>

<section class="fit wrap hx-surface hx-ring" aria-labelledby="fit-title" use:drop.view>
	<header class="intro">
		<h2 id="fit-title" class="h hx-grad">{t.fitTitle}</h2>
		<p class="fine">{t.fitLede(card.vramGB)}</p>
		<button type="button" class="replay mono" onclick={drop.replay}><span aria-hidden="true">↻</span> {t.fitReplay}</button>
	</header>

	<div class="bars" class:play={drop.on} style="--cells:{axis / step}">
		<div class="row head" aria-hidden="true">
			<span></span>
			<div class="lane">
				<span class="cap mono">{card.short} · {card.vramGB}{'\u00a0'}GB</span>
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
	.cap {
		position: absolute;
		right: 0;
		bottom: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		white-space: nowrap;
		color: var(--text-hi);
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
		margin-left: auto;
		min-height: 2.5rem;
		padding: 0 1rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: transparent;
		color: var(--text);
		font-size: var(--fs-2xs);
		cursor: pointer;
		transition:
			color var(--dur-3) var(--ease-out),
			border-color var(--dur-3) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.replay:hover {
		color: var(--text-hi);
		border-color: var(--hx-ink);
		box-shadow: 0 0 22px -6px var(--hx-glow);
	}

	@media (prefers-reduced-motion: no-preference) {
		/* only while a play runs: at rest the blocks and labels are in their final place */
		.play .val {
			animation: val-in 0.4s var(--ease-out) calc(var(--d) + 0.8s) both;
		}
		.play .block {
			animation: drop 1s linear var(--d) both;
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
	}
	@media (max-width: 30rem) {
		.axis .tick:nth-child(even):not(:last-child) {
			display: none;
		}
	}
</style>
