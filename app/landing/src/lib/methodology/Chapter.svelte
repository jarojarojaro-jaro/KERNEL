<script lang="ts">
	import type { Snippet } from 'svelte';
	import { reveal } from '$lib/fx/actions';
	import BgLoop from '$lib/fx/BgLoop.svelte';
	import Hl from '$lib/home/Hl.svelte';

	interface Props {
		id: string;
		/** 0-based chapter index; drives the number and how hot the chapter glows. */
		index: number;
		total: number;
		kicker: string;
		/** Heading text; words wrapped in *…* render in the shared `.hx-accent` ember. */
		title: string;
		lead: string;
		sourcesLabel: string;
		sources: string[];
		/** The first chapter carries the page h1. */
		hero?: boolean;
		/** A subtle background loop behind the chapter head (static/media path without extension). */
		loop?: string;
		children: Snippet;
	}
	let { id, index, total, kicker, title, lead, sourcesLabel, sources, hero = false, loop, children }: Props = $props();
	const no = $derived(String(index + 1).padStart(2, '0'));
	const of = $derived(String(total).padStart(2, '0'));
</script>

<section {id} class="ch" class:hero style="--heat:{index / (total - 1)}" aria-labelledby="{id}-h">
	{#if loop}<div class="loop"><BgLoop src={loop} /></div>{/if}
	<div class="glow" aria-hidden="true"></div>
	<header class="ch-head container" use:reveal>
		<span class="ghost mono" aria-hidden="true">{no}</span>
		<p class="kick"><span class="no mono">{no}</span><span class="of mono" aria-hidden="true">/ {of}</span><span class="bar" aria-hidden="true"></span><span class="kt">{kicker}</span></p>
		{#if hero}
			<h1 id="{id}-h" class="ch-title giga"><Hl text={title} /></h1>
		{:else}
			<h2 id="{id}-h" class="ch-title"><Hl text={title} /></h2>
		{/if}
		<p class="ch-lead">{lead}</p>
	</header>
	<div class="stage container" use:reveal={{ threshold: 0.08 }}>
		{@render children()}
	</div>
	<details class="srcs container">
		<summary><span class="mono">{sourcesLabel}</span><span class="cnt mono">{sources.length}</span></summary>
		<ul>
			{#each sources as s (s)}<li class="mono">{s}</li>{/each}
		</ul>
	</details>
</section>

<style>
	.ch {
		position: relative;
		isolation: isolate;
		padding-block: clamp(4.5rem, 3rem + 6vw, 9rem) clamp(2rem, 1.5rem + 2vw, 3rem);
		scroll-margin-top: 4rem;
	}
	/* chapter seam: a hairline that glows hot in the middle instead of a flat grey rule */
	.ch + :global(.ch)::before {
		content: '';
		position: absolute;
		top: 0;
		left: 50%;
		width: min(72rem, 100% - 2 * var(--gutter));
		height: 1px;
		transform: translateX(-50%);
		background: linear-gradient(90deg, transparent, var(--line) 15%, color-mix(in srgb, var(--heat-3) 60%, var(--line)) 50%, var(--line) 85%, transparent);
	}
	.hero {
		padding-top: clamp(3.5rem, 2rem + 5vw, 7rem);
	}
	/* the page heats up chapter by chapter: glow strength follows --heat (0 → 1) */
	.glow {
		position: absolute;
		inset: 0 0 auto;
		height: min(46rem, 100%);
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(48rem 26rem at 85% 0%, color-mix(in srgb, var(--heat-3) calc(4% + var(--heat) * 14%), transparent), transparent 70%),
			radial-gradient(36rem 20rem at 5% 30%, color-mix(in srgb, var(--heat-2) calc(2% + var(--heat) * 8%), transparent), transparent 70%);
	}
	/* the chapter's theme as a faint moving texture: lit only, fading out under the head; dark theme
	   only (hidden boxes never load the video) */
	.loop {
		position: absolute;
		inset: 0 0 auto;
		height: min(40rem, 100%);
		z-index: -1;
		opacity: 0.22;
		mix-blend-mode: screen;
		pointer-events: none;
		-webkit-mask-image: linear-gradient(180deg, transparent, #000 18%, #000 45%, transparent);
		mask-image: linear-gradient(180deg, transparent, #000 18%, #000 45%, transparent);
	}
	:global(:root[data-theme='light']) .loop {
		display: none;
	}
	.ch-head {
		position: relative;
		display: grid;
		gap: clamp(1rem, 0.8rem + 0.6vw, 1.5rem);
	}
	/* the chapter number as a large hollow figure behind the head: rhythm you can see while scrolling */
	.ghost {
		position: absolute;
		top: -0.12em;
		right: 0;
		z-index: -1;
		font-size: clamp(7rem, 3rem + 11vw, 15rem);
		font-weight: 700;
		line-height: 1;
		letter-spacing: -0.02em;
		color: transparent;
		-webkit-text-stroke: 1px color-mix(in srgb, var(--heat-3) calc(18% + var(--heat) * 22%), transparent);
		pointer-events: none;
		user-select: none;
	}
	.kick {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.no {
		font-size: var(--fs-md);
		font-weight: 700;
		letter-spacing: 0.02em;
		padding-inline-end: 0.08em;
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.of {
		margin-left: calc(-1 * var(--sp-2));
		color: var(--text-mute);
		letter-spacing: 0.06em;
	}
	.bar {
		width: clamp(2rem, 1rem + 3vw, 4rem);
		height: 2px;
		border-radius: 2px;
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 12px color-mix(in srgb, var(--heat-3) 70%, transparent);
		transform-origin: left;
	}
	.kt {
		color: var(--text);
	}
	.ch-title {
		margin: 0;
		max-width: 20ch;
		font-size: clamp(2.1rem, 1.2rem + 3.3vw, 4.2rem);
		line-height: 1.04;
		letter-spacing: -0.04em;
		font-weight: 680;
		color: var(--text-hi);
		text-wrap: balance;
		overflow-wrap: break-word;
		/* no hyphenation: a split accent word (sin-gle) breaks the ember fragment and reads badly */
		hyphens: manual;
	}
	.hero .ch-title {
		font-size: clamp(2rem, 0.9rem + 5.5vw, 5.4rem);
		max-width: 17ch;
		letter-spacing: -0.045em;
	}
	.ch-lead {
		margin: 0;
		max-width: 60ch;
		font-size: clamp(1rem, 0.94rem + 0.3vw, 1.2rem);
		line-height: 1.65;
		color: var(--text);
		text-wrap: pretty;
	}
	.stage {
		margin-top: clamp(2.5rem, 1.8rem + 2.4vw, 4rem);
	}
	/* opener choreography: kicker, rule, title and lead rise in sequence (resting state is final) */
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .ch-head:global([data-in]) {
			animation: none;
		}
		:global(html.js) .ch-head:global([data-in]) > :not(.ghost) {
			animation: ch-rise 0.95s var(--ease-out) backwards;
		}
		:global(html.js) .ch-head:global([data-in]) > .ch-title {
			animation-delay: 90ms;
		}
		:global(html.js) .ch-head:global([data-in]) > .ch-lead {
			animation-delay: 190ms;
		}
		:global(html.js) .ch-head:global([data-in]) .bar {
			animation: ch-draw 1.1s var(--ease-out) 120ms backwards;
		}
		:global(html.js) .ch-head:global([data-in]) > .ghost {
			animation: ch-ghost 1.6s var(--ease-out) backwards;
		}
		:global(html.js) .stage:global([data-in]) {
			animation-delay: 260ms;
		}
	}
	@keyframes ch-rise {
		from {
			opacity: 0;
			transform: translate3d(0, 18px, 0);
		}
	}
	@keyframes ch-draw {
		from {
			transform: scaleX(0);
		}
	}
	@keyframes ch-ghost {
		from {
			opacity: 0;
			transform: translate3d(0, 24px, 0) scale(0.96);
		}
	}
	@media (max-width: 720px) {
		.ghost {
			font-size: 6rem;
			top: -0.35em;
			opacity: 0.6;
		}
	}
	.srcs {
		margin-top: var(--sp-8);
		color: var(--text-mute);
	}
	.srcs summary {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
		min-height: 2.75rem;
		cursor: pointer;
		font-size: var(--fs-xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		list-style: none;
		border-radius: var(--r-sm);
		transition: color var(--dur-2);
	}
	.srcs summary::-webkit-details-marker {
		display: none;
	}
	.srcs summary::before {
		content: '+';
		display: inline-grid;
		place-items: center;
		width: 1.25rem;
		height: 1.25rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-xs);
		transition: transform var(--dur-3) var(--ease-spring);
	}
	.srcs[open] summary::before {
		transform: rotate(45deg);
	}
	.srcs summary:hover,
	.srcs summary:focus-visible {
		color: var(--text-hi);
	}
	.srcs summary:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.cnt {
		color: var(--accent-ink);
	}
	.srcs ul {
		margin: var(--sp-2) 0 0;
		padding: 0 0 0 var(--sp-4);
		border-left: 1px solid color-mix(in srgb, var(--heat-3) 45%, var(--line));
		display: grid;
		gap: var(--sp-1);
		list-style: none;
		font-size: var(--fs-2xs);
		line-height: 1.6;
		overflow-wrap: anywhere;
	}
</style>
