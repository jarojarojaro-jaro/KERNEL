<script lang="ts">
	import { currentLang, href } from '$lib/i18n';
	import { BRAND } from '$lib/brand';
	import { LEGAL_DOCS, LEGAL_VERSION } from '$lib/legal/docs';
	import DraftBanner from '$lib/legal/DraftBanner.svelte';

	const lang = $derived(currentLang());
	const T = {
		pl: { title: 'Dokumenty prawne', lead: 'Regulamin, prywatność, cookies, informacja o AI i dane firmy.' },
		en: { title: 'Legal documents', lead: 'Terms, privacy, cookies, AI notice and company details.' }
	} as const;
	const t = $derived(T[lang]);
</script>

<svelte:head><title>{t.title} · {BRAND.name}</title><meta name="description" content={t.lead} /></svelte:head>

<section class="section">
	<div class="container container--narrow">
		<header class="head">
			<p class="eyebrow">{LEGAL_VERSION[lang]}</p>
			<h1 class="giga">{t.title}</h1>
			<p class="lede">{BRAND.name}: {t.lead}</p>
		</header>
		<DraftBanner {lang} />
		<ul class="docs" role="list">
			{#each LEGAL_DOCS as d, i (d.slug)}
				<li>
					<a class="doc" href={href(lang, `/legal/${d.slug}`)}>
						<span class="ix mono" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
						<span class="txt">
							<span class="name">{d.title[lang]}</span>
							<span class="desc">{d.description[lang]}</span>
						</span>
						<span class="arrow" aria-hidden="true">→</span>
					</a>
				</li>
			{/each}
		</ul>
	</div>
</section>

<style>
	.head {
		display: grid;
		gap: var(--sp-5);
		margin-bottom: var(--sp-10);
	}
	.docs {
		list-style: none;
		padding: 0;
		margin: 0;
		border-top: 1px solid var(--line);
	}
	.doc {
		display: grid;
		grid-template-columns: 3rem minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--sp-4);
		padding: var(--sp-6) var(--sp-2);
		border-bottom: 1px solid var(--line);
		color: var(--text);
		text-decoration: none;
		transition: background-color var(--dur-2) var(--ease-out);
	}
	.doc:hover {
		background: color-mix(in srgb, var(--text-hi) 3%, transparent);
	}
	.ix {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.txt {
		display: grid;
		gap: var(--sp-1);
	}
	.name {
		font-size: var(--fs-xl);
		font-weight: 680;
		font-stretch: 106%;
		letter-spacing: -0.025em;
		color: var(--text-hi);
	}
	.desc {
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.arrow {
		font-size: var(--fs-lg);
		color: var(--text-mute);
		transition:
			transform var(--dur-3) var(--ease-out),
			color var(--dur-2) var(--ease-out);
	}
	.doc:hover .arrow {
		transform: translateX(6px);
		color: var(--text-hi);
	}
	@media (max-width: 520px) {
		.doc {
			grid-template-columns: 2rem minmax(0, 1fr) auto;
			gap: var(--sp-3);
		}
		.name {
			font-size: var(--fs-lg);
		}
	}
</style>
