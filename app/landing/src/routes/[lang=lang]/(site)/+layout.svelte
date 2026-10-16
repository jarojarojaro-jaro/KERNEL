<script lang="ts">
	import CookieBanner from '$lib/site/CookieBanner.svelte';
	import Footer from '$lib/site/Footer.svelte';
	import Header from '$lib/site/Header.svelte';

	let { children } = $props();
</script>

<Header />
<main id="main" tabindex="-1">
	{@render children()}
</main>
<Footer />
<CookieBanner />

<style>
	main:focus {
		outline: none;
	}
</style>
