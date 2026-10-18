<script lang="ts">
	import CursorGlow from '$lib/fx/CursorGlow.svelte';
	import CardsTeaser from '$lib/home/CardsTeaser.svelte';
	import Duo from '$lib/home/Duo.svelte';
	import Engine from '$lib/home/Engine.svelte';
	import Faq from '$lib/home/Faq.svelte';
	import FinalCta from '$lib/home/FinalCta.svelte';
	import Hero from '$lib/home/Hero.svelte';
	import Privacy from '$lib/home/Privacy.svelte';
	import Quality from '$lib/home/Quality.svelte';
	import ResultsTeaser from '$lib/home/ResultsTeaser.svelte';
	import SceneBoost from '$lib/home/SceneBoost.svelte';
	import SceneFit from '$lib/home/SceneFit.svelte';
	import SceneScan from '$lib/home/SceneScan.svelte';
	import { currentLang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';

	const lang = $derived(currentLang());
	const c = $derived(copy[lang]);
</script>

<svelte:head>
	<title>{c.meta.title}</title>
	<meta name="description" content={c.meta.description} />
	<meta property="og:title" content={c.meta.title} />
	<meta property="og:description" content={c.meta.description} />
	<meta property="og:type" content="website" />
	<meta property="og:locale" content={lang === 'pl' ? 'pl_PL' : 'en_US'} />
</svelte:head>

<div class="grain" aria-hidden="true"></div>
<div class="nav-fade" aria-hidden="true"></div>
<CursorGlow />

<Hero {lang} />

<section id="how" class="how heat-top" aria-labelledby="how-title">
	<header class="how-head">
		<Duo text={c.how.title} id="how-title" size="mega" />
	</header>
	<SceneScan {lang} />
	<SceneFit {lang} />
	<SceneBoost {lang} />
</section>

<ResultsTeaser {lang} />
<Engine {lang} />
<Quality {lang} />
<CardsTeaser {lang} />
<Privacy {lang} />
<FinalCta {lang} />
<Faq {lang} />

<style>
	.how {
		position: relative;
		background: var(--bg-0);
	}
	.how-head {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem) 0;
		display: grid;
		gap: var(--sp-5);
	}
</style>
