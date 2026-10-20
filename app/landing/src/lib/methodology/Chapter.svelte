<script lang="ts">
	import type { Snippet } from 'svelte';
	import { reveal } from '$lib/fx/actions';
	import BgLoop from '$lib/fx/BgLoop.svelte';

	interface Props {
		id: string;
		/** 0-based chapter index; drives the number and how hot the chapter glows. */
		index: number;
		total: number;
		kicker: string;
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
</script>

<section {id} class="ch" class:hero style="--heat:{index / (total - 1)}" aria-labelledby="{id}-h">
	{#if loop}<div class="loop"><BgLoop src={loop} /></div>{/if}
	<div class="glow" aria-hidden="true"></div>
	<header class="ch-head container" use:reveal>
		<p class="kick"><span class="no mono">{no}</span><span class="bar" aria-hidden="true"></span>{kicker}</p>
		{#if hero}
			<h1 id="{id}-h" class="ch-title giga">{title}</h1>
		{:else}
			<h2 id="{id}-h" class="ch-title">{title}</h2>
		{/if}
		<p class="ch-lead">{lead}</p>
	</header>
	<div class="stage container">
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
	.ch + :global(.ch) {
		border-top: 1px solid var(--line);
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
		display: grid;
		gap: var(--sp-4);
	}
	.kick {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.no {
		font-size: var(--fs-sm);
		font-weight: 600;
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.bar {
		width: 2.5rem;
		height: 2px;
		border-radius: 2px;
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 12px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.ch-title {
		margin: 0;
		max-width: 22ch;
		font-size: clamp(2rem, 1.3rem + 2.8vw, 3.6rem);
		line-height: 1.04;
		letter-spacing: -0.035em;
		font-weight: 650;
		color: var(--text-hi);
		text-wrap: balance;
		overflow-wrap: break-word;
		hyphens: auto;
	}
	.hero .ch-title {
		font-size: clamp(2rem, 0.9rem + 5.5vw, 5.2rem);
		max-width: 18ch;
	}
	.ch-lead {
		margin: 0;
		max-width: 62ch;
		font-size: var(--fs-md);
		line-height: 1.6;
		color: var(--text);
	}
	.stage {
		margin-top: clamp(2rem, 1.5rem + 2vw, 3.5rem);
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
