<script lang="ts">
	import { SITE_PUBLIC } from '$lib/site/public';
	/**
	 * Final CTA: the closing statement is a token stream, side by side, that never stops (StreamDuel,
	 * shared with the hero): the same answer flows without Enigma LABZ (the typical app, a0) and with it
	 * (our engine, a2), RTX 3090 × Qwen3.8-27B, at exactly the measured median t/s; our side emits in
	 * steps of the measured MTP tokens per step, a counter of tokens written grows under each pane.
	 * The text is an example, the pace is measured.
	 */
	import { magnetic } from '$lib/fx/actions';
	import StreamDuel from '$lib/fx/StreamDuel.svelte';
	import { variantLabel } from '$lib/data/measurements';
	import { cardsHref, href, num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, HERO_CARD, HERO_GAIN, HERO_MODEL, HERO_RUN, HERO_V } from './data';
	import Duo from './Duo.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].final);
	const dl = $derived(copy[lang].duel);
	const cold = HERO_V.a0.decode!;
	const hot = HERO_V.a2.decode!;
	const gain = HERO_GAIN.total?.v ?? hot.v / cold.v;
	const lanes = $derived([
		{ id: 'cold' as const, tag: dl.without, who: variantLabel(HERO_RUN, 'a0')[lang], tps: cold.v, burst: HERO_V.a0.tokStep?.v ?? 1 },
		{ id: 'hot' as const, tag: dl.with, who: variantLabel(HERO_RUN, 'a2')[lang], tps: hot.v, burst: HERO_V.a2.tokStep?.v ?? 1 }
	]);
	const vars = $derived({ card: HERO_CARD.name, model: HERO_MODEL, quant: HERO_RUN.quant, a0: num(cold.v, lang), a2: num(hot.v, lang) });
</script>

<section class="final heat-top" aria-labelledby="final-title">
	<div class="heat" aria-hidden="true"></div>
	<div class="inner">
		<div class="copy">
			<Duo text={c.title} id="final-title" burn />
			<p class="lede">{c.lede}</p>
		</div>
		<div class="duel">
			<StreamDuel {lanes} {gain} text={c.text} {lang} labels={dl} summary={fill(c.summary, vars)}>
				{#snippet caption()}
					<span>{HERO_CARD.name} · {HERO_MODEL} {HERO_RUN.quant}</span>
					<span class="note">{c.note}</span>
				{/snippet}
			</StreamDuel>
		</div>
		<div class="ctas">
			<a class="cta cta--bone" href={cardsHref(lang)} use:magnetic>{c.cards} <span class="arrow" aria-hidden="true">→</span></a>
			{#if !SITE_PUBLIC}<a class="cta cta--line" href={href(lang, '/methodology')} use:magnetic>{c.method}</a>{/if}
		</div>
	</div>
</section>

<style>
	.final {
		position: relative;
		overflow: clip;
		padding-block: clamp(4rem, 3rem + 4vw, 7rem);
		background: var(--bg-0);
		isolation: isolate;
	}
	.heat {
		position: absolute;
		inset: auto -20% -40% -20%;
		height: 100%;
		z-index: -1;
		background:
			radial-gradient(35% 45% at 72% 85%, rgb(255 122 26 / 0.3), transparent 70%),
			radial-gradient(60% 60% at 70% 100%, rgb(226 64 28 / 0.42), rgb(122 46 31 / 0.15) 50%, transparent 75%);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
		grid-template-areas:
			'copy duel'
			'ctas duel';
		grid-template-rows: auto 1fr;
		gap: var(--sp-8) clamp(2rem, 5vw, 5rem);
		align-items: start;
	}
	.copy {
		grid-area: copy;
		align-self: end;
		display: grid;
		gap: var(--sp-6);
	}
	.ctas {
		grid-area: ctas;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
	}
	.duel {
		grid-area: duel;
		min-width: 0;
	}
	.note::before {
		content: '· ';
	}
	@media (max-width: 900px) {
		.inner {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'copy' 'duel' 'ctas';
			grid-template-rows: none;
		}
	}
</style>
