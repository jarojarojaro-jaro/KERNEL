<script lang="ts">
	/**
	 * FAQ as a list of big questions (native <details>: keyboard and screen readers for free) next
	 * to a vertical headline. A closed question is condensed (wdth 75); opening it stretches it wide
	 * (wdth 118) and the answer slides in on the right half.
	 */
	import { TOK_PER_WORD } from '$lib/estimator';
	import { num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { HERO_CARD, HERO_GAIN, HERO_MODEL, fmtRatio } from './data';
	import Rich from './Rich.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].faq);
	const vars = $derived({
		card: HERO_CARD.name,
		model: HERO_MODEL,
		pl: num(TOK_PER_WORD.pl, lang, 2),
		en: num(TOK_PER_WORD.en, lang, 2)
	});
</script>

<section id="faq" class="faq heat-top" aria-labelledby="faq-title">
	<div class="inner">
		<header class="head">
			<h2 id="faq-title" class="vert">{c.title.replace('|', ' ')}</h2>
		</header>
		<div class="list">
			{#each c.items as [q, a], i (q)}
				<details>
					<summary>
						<span class="n" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
						<span class="q">{q}</span>
						<span class="ic" aria-hidden="true"></span>
					</summary>
					<p class="a"><Rich text={a} {vars} speed={{ total: { text: fmtRatio(HERO_GAIN.total!.v, lang), v: HERO_GAIN.total!.v } }} /></p>
				</details>
			{/each}
		</div>
	</div>
</section>

<style>
	.faq {
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem) clamp(3rem, 2rem + 3vw, 5rem);
		background: var(--bg-0);
	}
	/* vertical headline down the left edge, the questions to its right */
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 5rem);
		align-items: start;
	}
	.head {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--sp-5);
		position: sticky;
		top: 6rem;
	}
	.vert {
		margin: 0;
		writing-mode: vertical-rl;
		transform: rotate(180deg);
		font-family: var(--font-display);
		font-size: clamp(2.6rem, 1rem + 3.4vw, 4.6rem);
		font-weight: 840;
		font-stretch: 100%;
		line-height: 0.9;
		letter-spacing: -0.04em;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.list {
		border-top: 1px solid var(--line-strong);
	}
	details {
		border-bottom: 1px solid var(--line);
		interpolate-size: allow-keywords;
	}
	details::details-content {
		block-size: 0;
		overflow: clip;
		transition:
			block-size 0.45s var(--ease-out),
			content-visibility 0.45s allow-discrete;
	}
	details[open]::details-content {
		block-size: auto;
	}
	summary {
		display: grid;
		grid-template-columns: 3.5rem minmax(0, 1fr) 2.5rem;
		align-items: center;
		gap: var(--sp-4);
		padding: clamp(1.25rem, 2.4vw, 2.1rem) 0;
		cursor: pointer;
		list-style: none;
		border-radius: var(--r-sm);
	}
	summary::-webkit-details-marker {
		display: none;
	}
	.n {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
		letter-spacing: 0.08em;
	}
	.q {
		font-family: var(--font-display);
		font-size: clamp(1.2rem, 0.9rem + 1.1vw, 1.9rem);
		font-weight: 760;
		line-height: 1.1;
		letter-spacing: -0.025em;
		color: var(--text);
		transition: color var(--dur-2);
		text-wrap: balance;
	}
	summary:hover .q {
		color: var(--text-hi);
	}
	details[open] .q {
		color: var(--heat-4);
	}
	/* the open answer gets a heat rule along its edge */
	details {
		position: relative;
	}
	details::before {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: -1px;
		height: 2px;
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 14px rgb(255 122 26 / 0.6);
		transform-origin: 0 50%;
		transform: scaleX(0);
		transition: transform 0.5s var(--ease-out);
	}
	details[open]::before {
		transform: none;
	}
	.ic {
		position: relative;
		width: 1.4rem;
		height: 1.4rem;
		justify-self: end;
	}
	.ic::before,
	.ic::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		top: 50%;
		height: 2px;
		background: var(--text);
		transition: transform 0.35s var(--ease-spring);
	}
	.ic::after {
		transform: rotate(90deg);
	}
	details[open] .ic::after {
		transform: rotate(0deg);
	}
	.a {
		margin-left: 45%;
		padding: 0 3.5rem clamp(1.5rem, 3vw, 2.25rem) 0;
		color: var(--text);
		font-size: clamp(1rem, 0.9rem + 0.3vw, 1.2rem);
		line-height: 1.6;
		max-width: 58ch;
	}
	@media (max-width: 900px) {
		.inner {
			grid-template-columns: minmax(0, 1fr);
		}
		.head {
			position: static;
			align-items: flex-start;
		}
		.vert {
			writing-mode: horizontal-tb;
			transform: none;
			white-space: normal;
		}
		summary {
			grid-template-columns: 2rem minmax(0, 1fr) 1.5rem;
		}
		.a {
			margin-left: calc(2rem + var(--sp-4));
			padding-right: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		details::details-content,
		.q {
			transition: none;
		}
	}
</style>
