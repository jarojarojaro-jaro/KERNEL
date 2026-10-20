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
	<h1 class="h1">Cookie Policy</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Contents</h2>
		<ol>
			<li><a href="#summary">1. In short</a></li>
			<li><a href="#basis">2. Legal basis</a></li>
			<li><a href="#list">3. What we store</a></li>
			<li><a href="#analytics">4. The “analytics” category</a></li>
			<li><a href="#change">5. Changing your mind</a></li>
		</ol>
	</nav>
	<h2 id="summary" class="h2">1. In short</h2>
	<p>The {BRAND.name} website sets no tracking cookies and uses no analytics or advertising tools. The only things we store in your browser are the few technical entries listed below, each either strictly necessary or something you asked for.</p>
	<h2 id="basis" class="h2">2. Legal basis</h2>
	<p>Storing or accessing information on your device needs your consent unless it is strictly necessary to provide a service you explicitly requested (Article 5(3) of the ePrivacy Directive 2002/58/EC; Article 399 of the Polish Electronic Communications Law). Every entry in section 3 falls under that exemption. The rule covers localStorage and sessionStorage as well as cookies.</p>
	<h2 id="list" class="h2">3. What we store</h2>
	<div class="table-wrap">
		<table class="table">
			<caption class="sr-only">Stored items</caption>
			<thead><tr><th scope="col">Name and location</th><th scope="col">Purpose</th><th scope="col">Duration</th><th scope="col">Basis</th></tr></thead>
			<tbody>
				<tr><td><code>theme</code> — localStorage</td><td>remembers light or dark theme; written only after you click the theme toggle</td><td>until you clear site data or change it again</td><td>requested by you — strictly necessary</td></tr>
				<tr><td><code>consent</code> — localStorage</td><td>records your choice in the consent banner (version, analytics yes/no, date)</td><td>until you clear site data or the banner version changes</td><td>strictly necessary to respect your choice</td></tr>
				<tr><td><code>authjs.session-token</code> — cookie (HttpOnly, <code>__Secure-</code> prefix on https) <span class="badge badge--soon">once accounts launch</span></td><td>keeps you signed in to your Account; set only after you sign in</td><td>30 days or until you sign out</td><td>requested by you — strictly necessary</td></tr>
				<tr><td><code>authjs.csrf-token</code>, <code>authjs.callback-url</code>, <code>authjs.state</code>, <code>authjs.pkce.code_verifier</code>, <code>authjs.nonce</code> — cookies <span class="badge badge--soon">once accounts launch</span></td><td>protect the sign-in form against CSRF, secure sign-in with Google, GitHub or Hugging Face, and return you to the right page</td><td>until you close the browser; provider sign-in cookies — 15 minutes</td><td>requested by you — strictly necessary</td></tr>
				<tr><td><code>onboarding</code> — sessionStorage <span class="badge badge--soon">once accounts launch</span></td><td>the signed-in Account name shown under the “Check your hardware” steps</td><td>until you close the browser tab</td><td>requested by you — strictly necessary</td></tr>
			</tbody>
		</table>
	</div>
	<p>Sign-in cookies go only to our own server, so it can recognise your Account. No other entry is ever sent to our server or to third parties.</p>
	<h2 id="analytics" class="h2">4. The “analytics” category</h2>
	<p>The consent banner includes an “analytics” category so that we can ask properly if we ever need to. <strong>No analytics tool is installed today</strong>: nothing loads before you consent and nothing loads after. If we choose a tool, we will first list it here (provider, data stored, duration, any transfer outside the EEA) and ask you again.</p>
	<h2 id="change" class="h2">5. Changing your mind</h2>
	<p>Every page has a “Cookie settings” link in the footer. It reopens the consent banner, where you can change or withdraw your choice; rejecting is as easy as accepting. You can also clear the site’s data in your browser settings at any time, and the banner will appear again.</p>
	<p>For everything else about personal data, see the <a href={href(L, '/legal/privacy')}>Privacy Policy</a>.</p>
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
