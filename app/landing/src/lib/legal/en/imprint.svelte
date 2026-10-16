<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { href, type Lang } from '$lib/i18n';
	import DraftBanner from '../DraftBanner.svelte';
	import CompanyData from '../CompanyData.svelte';
	import { LEGAL_VERSION } from '../docs';

	/** The document is written in one language; `lang` is accepted for a uniform registry API. */
	let { lang: _lang }: { lang?: Lang } = $props();
	const L: Lang = 'en';
</script>

<article class="prose legal">
	<DraftBanner lang={L} />
	<h1 class="h1">Imprint</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Contents</h2>
		<ol>
			<li><a href="#provider">1. Service provider</a></li>
			<li><a href="#security">2. Security reports</a></li>
			<li><a href="#documents">3. Other documents</a></li>
		</ol>
	</nav>
	<h2 id="provider" class="h2">1. Service provider</h2>
	<p>{BRAND.name} is a project of a Polish limited liability company in formation. The details required by Article 5 of the Polish Act on Providing Services by Electronic Means and Article 206 of the Commercial Companies Code will be added as soon as the company is entered in the National Court Register.</p>
	<CompanyData lang={L} />
	<h2 id="security" class="h2">2. Security reports</h2>
	<p>Please report vulnerabilities confidentially to the address below. We plan to publish <code>/.well-known/security.txt</code> (RFC 9116) and a coordinated vulnerability disclosure policy, as required by Regulation (EU) 2024/2847 (the Cyber Resilience Act). Until the company is registered, this channel is not yet available.</p>
	<CompanyData lang={L} fields={['security']} />
	<h2 id="documents" class="h2">3. Other documents</h2>
	<ul>
		<li><a href={href(L, '/legal/terms')}>Terms of Service</a></li>
		<li><a href={href(L, '/legal/privacy')}>Privacy Policy</a></li>
		<li><a href={href(L, '/legal/cookies')}>Cookie Policy</a></li>
		<li><a href={href(L, '/legal/ai')}>AI Notice</a></li>
	</ul>
</article>

<style>
	.toc {
		margin-block: var(--sp-6);
	}
	.toc h2 {
		margin-top: 0;
	}
	.legal :global(h2[id]) {
		scroll-margin-top: var(--sp-16);
	}
</style>
