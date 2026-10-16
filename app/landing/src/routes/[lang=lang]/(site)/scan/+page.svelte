<script lang="ts">
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import ScanCommands from '$lib/onboarding/ScanCommands.svelte';
	import { copy } from '$lib/site/copy';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].scan);
	const p = $derived(copy[lang].privacy);
</script>

<svelte:head><title>{t.title}</title><meta name="description" content={t.lead} /></svelte:head>

<div class="container section stack page">
	<header class="stack head">
		<p class="overline">{p.overline}</p>
		<h1 class="h1">{t.title}</h1>
		<p class="lead">{t.lead}</p>
	</header>
	<div class="grid">
		<div class="card"><ScanCommands /></div>
		<aside class="stack side">
			<div class="card card--inset">
				<h2 class="h3">{p.never}</h2>
				<ul>{#each p.neverList as n (n)}<li>{n}</li>{/each}</ul>
			</div>
			<a class="btn btn--primary" href={href(lang, '/start/hardware')}>{ob[lang].hw.title} →</a>
		</aside>
	</div>
</div>

<style>
	.page {
		--stack: var(--sp-8);
	}
	.head {
		--stack: var(--sp-3);
		max-width: 48rem;
	}
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
		gap: var(--sp-6);
		align-items: start;
	}
	.side {
		--stack: var(--sp-4);
	}
	ul {
		margin: var(--sp-3) 0 0;
		padding-left: 1.2em;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-sm);
	}
	@media (max-width: 900px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}
</style>
