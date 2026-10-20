<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { currentLang } from '$lib/i18n';
	import AbbaLab from '$lib/methodology/AbbaLab.svelte';
	import Archive from '$lib/methodology/Archive.svelte';
	import Chapter from '$lib/methodology/Chapter.svelte';
	import { CH_SOURCES, COPY } from '$lib/methodology/copy';
	import Graveyard from '$lib/methodology/Graveyard.svelte';
	import Lossless from '$lib/methodology/Lossless.svelte';
	import Metal from '$lib/methodology/Metal.svelte';
	import QuestionRace from '$lib/methodology/QuestionRace.svelte';
	import Rail from '$lib/methodology/Rail.svelte';
	import RecordBoard from '$lib/methodology/RecordBoard.svelte';
	import SpecPlayground from '$lib/methodology/SpecPlayground.svelte';
	import StepScope from '$lib/methodology/StepScope.svelte';

	const lang = $derived(currentLang());
	const c = $derived(COPY[lang]);
	const VIZ = [QuestionRace, AbbaLab, Lossless, StepScope, SpecPlayground, Metal, Graveyard, RecordBoard];
</script>

<svelte:head>
	<title>{c.meta.title} · {BRAND.name}</title>
	<meta name="description" content={c.meta.desc} />
</svelte:head>

<article class="journey heat-scope">
	<Rail items={c.ch} label={c.rail} />
	{#each c.ch as ch, i (ch.id)}
		{@const Viz = VIZ[i]}
		<Chapter id={ch.id} index={i} total={c.ch.length} kicker="{c.chapter} {i + 1} · {ch.kicker}" title={ch.title} lead={ch.lead} sourcesLabel={c.sources} sources={CH_SOURCES[ch.id]} hero={i === 0}>
			<Viz {lang} />
		</Chapter>
	{/each}
	<Archive />
</article>

<style>
	.journey {
		overflow-x: clip;
	}
	/* ---- shared building blocks of the chapter visuals ---- */
	:where(.journey) :global(.panel) {
		position: relative;
		padding: clamp(1.1rem, 0.8rem + 1.2vw, 1.75rem);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: linear-gradient(180deg, color-mix(in srgb, var(--bg-2) 70%, transparent), var(--bg-1));
		box-shadow: var(--shadow-2);
		min-width: 0;
	}
	:where(.journey) :global(.panel-h) {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	:where(.journey) :global(.small) {
		margin: 0;
		font-size: var(--fs-sm);
		line-height: 1.6;
		color: var(--text);
	}
	:where(.journey) :global(.fine) {
		margin: 0;
		font-size: var(--fs-2xs);
		line-height: 1.55;
		color: var(--text-mute);
	}
	:where(.journey) :global(.tag-ill),
	:where(.journey) :global(.tag-m) {
		display: inline-block;
		padding: 0.1rem 0.45rem;
		border-radius: var(--r-pill);
		font-family: var(--font-mono);
		font-size: 0.625rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		border: 1px solid var(--warn);
		color: var(--warn-ink);
		vertical-align: middle;
	}
	:where(.journey) :global(.tag-m) {
		border-color: var(--ok);
		color: var(--ok-ink);
	}
	:where(.journey) :global(.seg) {
		display: inline-flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		padding: 0.25rem;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-2);
		justify-self: start;
		max-width: 100%;
	}
	:where(.journey) :global(.seg button) {
		min-height: 2.5rem;
		padding: 0 0.9rem;
		border: 0;
		border-radius: var(--r-sm);
		background: none;
		color: var(--text-mute);
		font: inherit;
		font-size: var(--fs-sm);
		font-weight: 560;
		cursor: pointer;
		transition:
			background-color var(--dur-2),
			color var(--dur-2);
	}
	:where(.journey) :global(.seg button:hover) {
		color: var(--text-hi);
	}
	:where(.journey) :global(.seg button[aria-pressed='true']) {
		background: var(--bg-3);
		color: var(--text-hi);
		box-shadow:
			inset 0 -2px 0 var(--heat-3),
			0 6px 18px -10px var(--heat-3);
	}
	:where(.journey) :global(.seg button:focus-visible),
	:where(.journey) :global(.btn-m:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	:where(.journey) :global(.btn-m) {
		min-height: 2.75rem;
		padding: 0 1rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-md);
		background: var(--bg-3);
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-sm);
		font-weight: 600;
		cursor: pointer;
		transition:
			transform var(--dur-1),
			border-color var(--dur-2),
			background-color var(--dur-2);
	}
	:where(.journey) :global(.btn-m:hover:not(:disabled)) {
		border-color: var(--heat-3);
	}
	:where(.journey) :global(.btn-m:active:not(:disabled)) {
		transform: scale(0.97);
	}
	:where(.journey) :global(.btn-m:disabled) {
		opacity: 0.4;
		cursor: default;
	}
	:where(.journey) :global(.btn-m.hot) {
		border-color: var(--heat-3);
		background: linear-gradient(180deg, var(--heat-3), var(--heat-2));
		color: var(--on-accent);
		box-shadow: 0 10px 26px -14px var(--heat-3);
	}
	:where(.journey) :global(.btn-m.ghost) {
		background: none;
	}
	:where(.journey) :global(.btn-m.ghost[aria-pressed='true']) {
		border-color: var(--heat-3);
		color: var(--accent-ink);
	}
	:where(.journey) :global(.chip) {
		display: inline-block;
		padding: 0.2rem 0.5rem;
		border-radius: var(--r-xs);
		border: 1px solid var(--line-strong);
		background: var(--bg-2);
		font-size: var(--fs-xs);
		color: var(--text);
	}
</style>
