<script lang="ts">
	/**
	 * Prywatność: one full-bleed statement (a single width, no condensed/wide formula) and a cut wire.
	 * Everything stays on the left of the gap.
	 */
	import { reveal } from '$lib/fx/actions';
	import { href, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].privacy);
</script>

<section id="privacy" class="privacy" aria-labelledby="privacy-title">
	<div class="inner">
		<h2 id="privacy-title" class="statement" use:reveal>{c.title.replace('|', ' ')}</h2>
		<div class="wire" use:reveal aria-hidden="true">
			<span class="node local">{c.diagram[0]}</span>
			<span class="line"></span>
			<span class="node local">{c.diagram[1]}</span>
			<span class="cut"><span></span><span></span></span>
			<span class="node away">{c.diagram[2]}</span>
		</div>
		<div class="foot">
			<p class="lede">{c.lede}</p>
			<a class="cta cta--line" href={href(lang, '/scan')}>{c.link} <span class="arrow" aria-hidden="true">→</span></a>
		</div>
	</div>
</section>

<style>
	.privacy {
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		border-top: 1px solid var(--line);
		background: var(--bg-0);
	}
	/* a centred statement: one sentence, the wire under it */
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		justify-items: center;
		text-align: center;
		gap: clamp(2rem, 4vw, 3.5rem);
	}
	.statement {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.2rem, 0.8rem + 4vw, 5rem);
		font-weight: 800;
		font-stretch: 104%;
		line-height: 1;
		letter-spacing: -0.04em;
		color: var(--text-hi);
		text-wrap: balance;
		max-width: 24ch;
	}
	@media (prefers-reduced-motion: no-preference) {
		/* resting state final; entering view replays a short rise (global reveal) */
	}
	.wire {
		width: 100%;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
	}
	.node {
		flex: none;
		padding: 0.45rem 0.8rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		color: var(--text-hi);
	}
	.node.away {
		border-style: dashed;
		color: var(--text-mute);
		border-color: var(--line);
	}
	.line {
		flex: 1;
		height: 1px;
		background: var(--text-hi);
		transform-origin: 0 50%;
	}
	.cut {
		position: relative;
		flex: 1.4;
		display: flex;
		justify-content: space-between;
		align-items: center;
		height: 1rem;
	}
	.cut span {
		width: 42%;
		height: 1px;
		background: repeating-linear-gradient(90deg, var(--line-strong) 0 4px, transparent 4px 9px);
	}
	.cut::after {
		content: '';
		position: absolute;
		left: 50%;
		top: 50%;
		width: 1px;
		height: 1.6rem;
		background: var(--text-hi);
		transform: translate(-50%, -50%) rotate(20deg);
		box-shadow: 6px 0 0 var(--text-hi);
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .wire:global([data-in]) .line {
			animation: line-in 1.2s var(--ease-out) 0.2s backwards;
		}
	}
	@keyframes line-in {
		from {
			transform: scaleX(0);
		}
	}
	.foot {
		display: grid;
		justify-items: center;
		gap: var(--sp-6);
	}
	.foot .lede {
		max-width: 46ch;
	}
	@media (max-width: 640px) {
		.wire {
			flex-wrap: wrap;
		}
		.line,
		.cut {
			min-width: 3rem;
		}
	}
</style>
