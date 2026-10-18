<script lang="ts">
	/**
	 * Prywatność: one full-bleed statement and the data path as a diagram: scan → your computer is a
	 * live heat filament, the link to the internet is cut. Everything stays on the left of the gap.
	 */
	import { reveal } from '$lib/fx/actions';
	import { href, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].privacy);
</script>

<section id="privacy" class="privacy heat-top" aria-labelledby="privacy-title">
	<div class="inner">
		<h2 id="privacy-title" class="statement" use:reveal>{c.title.replace('|', ' ')}</h2>
		<!-- the data path: scan → your computer is a live heat filament; the link to the internet is cut -->
		<div class="wire" use:reveal aria-hidden="true">
			<span class="node local">
				<svg viewBox="0 0 24 24"><path d="M4 8V5h3M17 5h3v3M20 16v3h-3M7 19H4v-3M4 12h16" /></svg>
				<span>{c.diagram[0]}</span>
			</span>
			<span class="line"><span class="pulse"></span></span>
			<span class="node local home">
				<svg viewBox="0 0 24 24"><path d="M3 5h18v11H3zM8 20h8M12 16v4" /></svg>
				<span>{c.diagram[1]}</span>
			</span>
			<span class="cut"><span></span><span></span></span>
			<span class="node away">
				<svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" /></svg>
				<span>{c.diagram[2]}</span>
			</span>
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
		display: inline-flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.55rem 0.95rem 0.55rem 0.7rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: var(--bg-1);
		color: var(--text-hi);
	}
	.node svg {
		width: 1.25rem;
		height: 1.25rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.5;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.node.local svg {
		color: var(--heat-4);
	}
	/* your computer: where everything happens, warm */
	.node.home {
		border-color: rgb(255 122 26 / 0.6);
		box-shadow:
			0 0 0 4px rgb(255 122 26 / 0.08),
			0 0 30px -6px rgb(255 122 26 / 0.7);
	}
	.node.away {
		border-style: dashed;
		color: var(--text-mute);
		border-color: var(--line);
		background: transparent;
	}
	/* the heat filament: glowing core, a spark running from scan to computer */
	.line {
		position: relative;
		flex: 1;
		height: 2px;
		border-radius: 2px;
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 50%, var(--heat-4));
		box-shadow:
			0 0 8px rgb(255 122 26 / 0.8),
			0 0 22px rgb(226 64 28 / 0.45);
		transform-origin: 0 50%;
		overflow: hidden;
	}
	.pulse {
		position: absolute;
		top: -1px;
		bottom: -1px;
		left: 0;
		width: 22%;
		background: linear-gradient(90deg, transparent, var(--heat-5), transparent);
		transform: translate3d(-100%, 0, 0);
	}
	@media (prefers-reduced-motion: no-preference) {
		.pulse {
			animation: spark 2.4s cubic-bezier(0.5, 0, 0.5, 1) infinite;
		}
	}
	@keyframes spark {
		to {
			transform: translate3d(460%, 0, 0);
		}
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
		background: var(--danger);
		transform: translate(-50%, -50%) rotate(20deg);
		box-shadow: 6px 0 0 var(--danger);
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
