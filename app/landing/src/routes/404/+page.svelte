<script lang="ts">
	/**
	 * 404 as a real page: `.htaccess` has `ErrorDocument 404 /404.html`, and the live site serves a
	 * full page there — header, `<main id="main">`, footer and the cookie banner, exactly like the
	 * `(site)` layout. This route sits outside `[lang=lang]`, so it renders the same three shells
	 * itself. Text 1:1 with the live `404.html`; `noindex` because it is not a landing page.
	 * deploy-ftp.py copies the prerendered file to `build/404.html`.
	 */
	import { BRAND } from '$lib/brand';
	import CookieBanner from '$lib/site/CookieBanner.svelte';
	import Footer from '$lib/site/Footer.svelte';
	import Header from '$lib/site/Header.svelte';
	import { href } from '$lib/i18n';

	const title = `Nie ma takiej strony (404) · ${BRAND.name}`;
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<Header />
<main id="main" tabindex="-1">
	<div class="container section stack page">
		<header class="stack head">
			<p class="overline">Błąd 404</p>
			<h1 class="h1">Nie ma takiej strony</h1>
			<p class="lead">Ten adres nie istnieje albo strona została przeniesiona. Zacznij od strony głównej albo wybierz swoją kartę.</p>
			<p class="lead" lang="en">Page not found. The address does not exist or the page has moved.</p>
		</header>
		<div class="cta">
			<a class="btn btn--primary" href={href('pl', '/')}>Strona główna →</a>
			<a class="btn btn--ghost" href={href('pl', '/karty/')}>Twoja karta</a>
			<a class="btn btn--ghost" href={href('en', '/')} hreflang="en" lang="en">English home page →</a>
		</div>
	</div>
</main>
<Footer />
<CookieBanner />

<style>
	main:focus {
		outline: none;
	}
	.head {
		display: grid;
		gap: var(--sp-3);
	}
	.cta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}
</style>
