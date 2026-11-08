<script lang="ts">
	/**
	 * The social/SEO block every public page carries: OG, Twitter and icons.
	 *
	 * One source for all 70 public pages (the /app/ prototype layout has its own, thinner head).
	 * The image is the static `og-<lang>.jpg` (1200×630) in `static/`; on a LAN preview
	 * `SITE_ORIGIN` is empty, so `og:image`/`twitter:image` are omitted — a relative og:image is
	 * useless to crawlers, and the icons cover the local case.
	 */
	import { BRAND } from '$lib/brand';
	import { currentLang, type Lang } from '$lib/i18n';
	import { SITE_ORIGIN } from '$lib/site/public';

	interface Props {
		title: string;
		description: string;
		/** og:type — 'website' unless the page is an article. */
		type?: string;
		/** Schema.org objects to publish as JSON-LD (one graph, or a single object). */
		jsonld?: object | object[];
		/** Page language; defaults to the `[lang]` route param. */
		lang?: Lang;
	}

	let { title, description, type = 'website', jsonld, lang }: Props = $props();

	const l = $derived(lang ?? currentLang());
	const locale = $derived(l === 'pl' ? 'pl_PL' : 'en_US');
	const image = $derived(SITE_ORIGIN ? `${SITE_ORIGIN}/og-${l}.jpg` : null);
	const imageAlt = $derived(
		l === 'pl'
			? `${BRAND.name}: ten sam sprzęt, ten sam model, po prostu szybciej`
			: `${BRAND.name}: same hardware, same model, just faster`
	);
	/**
	 * A single object renders on its own (that is how the live explorer pages carry a bare
	 * BreadcrumbList); an array is published as one `@graph` (the live home page).
	 */
	const ldJson = $derived(
		jsonld == null
			? null
			: JSON.stringify(
					Array.isArray(jsonld)
						? { '@context': 'https://schema.org', '@graph': jsonld }
						: { '@context': 'https://schema.org', ...jsonld }
				)
	);
</script>

<svelte:head>
	<meta property="og:type" content={type} />
	<meta property="og:locale" content={locale} />
	<meta property="og:site_name" content={BRAND.name} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	{#if image}
		<meta property="og:image" content={image} />
		<meta property="og:image:width" content="1200" />
		<meta property="og:image:height" content="630" />
		<meta property="og:image:alt" content={imageAlt} />
	{/if}
	<meta name="twitter:card" content={image ? 'summary_large_image' : 'summary'} />
	<meta name="twitter:title" content={title} />
	<meta name="twitter:description" content={description} />
	{#if image}<meta name="twitter:image" content={image} />{/if}
	{#if ldJson}
		<!-- A <script> body is static text in Svelte, so the JSON-LD tag goes through {@html}. -->
		{@html `<script type="application/ld+json">${ldJson}</script>`}
	{/if}
</svelte:head>
