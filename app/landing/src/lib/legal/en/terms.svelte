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
	<h1 class="h1">Terms of Service</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Contents</h2>
		<ol>
			<li><a href="#about">1. Who we are and what these terms cover</a></li>
			<li><a href="#definitions">2. Definitions</a></li>
			<li><a href="#services">3. The services</a></li>
			<li><a href="#requirements">4. Technical requirements</a></li>
			<li><a href="#account">5. Your account</a></li>
			<li><a href="#editions">6. Free and paid editions</a></li>
			<li><a href="#consumer">7. Your rights as a consumer</a></li>
			<li><a href="#use">8. Acceptable use and model licences</a></li>
			<li><a href="#ai">9. AI and honest performance claims</a></li>
			<li><a href="#liability">10. Liability</a></li>
			<li><a href="#complaints">11. Complaints</a></li>
			<li><a href="#adr">12. Out-of-court dispute resolution</a></li>
			<li><a href="#law">13. Governing law</a></li>
			<li><a href="#changes">14. Changes to these Terms</a></li>
		</ol>
	</nav>
	<h2 id="about" class="h2">1. Who we are and what these terms cover</h2>
	<p>These Terms govern the electronic services provided under the {BRAND.name} name, within the meaning of Article 8 of the Polish Act of 18 July 2002 on Providing Services by Electronic Means.</p>
	<p>The provider is a Polish limited liability company that is still being formed. Its details will appear below once it is entered in the National Court Register:</p>
	<CompanyData lang={L} />
	<p>You can read, download and print these Terms free of charge before you use any service.</p>
	<h2 id="definitions" class="h2">2. Definitions</h2>
	<ul>
		<li><strong>“we”, “us”</strong> — the provider named in section 1.</li>
		<li><strong>“you”</strong> — anyone using the services; <strong>“consumer”</strong> — a natural person acting outside their trade or profession, including a sole trader in the situation described in Article 38a of the Polish Consumer Rights Act.</li>
		<li><strong>“Website”</strong> — our website and its subpages.</li>
		<li><strong>“App”</strong> — the {BRAND.name} desktop application installed on your computer, including the command-line tool (<strong>CLI</strong>) and the <strong>local API</strong>, which is reachable only on your own machine.</li>
		<li><strong>“Account”</strong> — your optional user account.</li>
		<li><strong>“Model”</strong> — a third-party language model you download and run locally under its own licence.</li>
		<li><strong>“Digital content”</strong> — the App, acceleration profiles and other data supplied in digital form.</li>
		<li><strong>“Hardware scan”</strong> — the script or App feature that reads hardware details locally to match you with a Model.</li>
	</ul>
	<h2 id="services" class="h2">3. The services</h2>
	<p>We provide:</p>
	<ul>
		<li>the Website, including product information, benchmark results and the <a href={href(L, '/methodology')}>Methodology</a> page;</li>
		<li>a waitlist form — <em>at the moment the form sends nothing anywhere, because its backend is not live yet</em>;</li>
		<li>a model picker that runs entirely in your browser, using details you type in or a pasted hardware-scan code;</li>
		<li>the Account;</li>
		<li>the App, CLI and local API for download and use on your device.</li>
	</ul>
	<p>Models run on your own hardware. Your prompts and conversations never leave your device, and we never see them.</p>
	<h2 id="requirements" class="h2">4. Technical requirements</h2>
	<p>To use the Website you need an internet connection and an up-to-date browser with JavaScript enabled. The App requires a computer running Linux, Windows or macOS that meets the hardware requirements of the chosen Model; the App shows them before any download.</p>
	<p>Using online services carries ordinary risks such as malware and phishing. Only download the App from the Website and check checksums or signatures where we publish them.</p>
	<h2 id="account" class="h2">5. Your account</h2>
	<ul>
		<li>An Account is optional and free. The free edition of the App works without one.</li>
		<li>You can sign up with Google, GitHub or Hugging Face, or with just a username and password, without an e-mail address. With an outside provider we request only the minimum: your account identifier, username and, if the provider shares it, your e-mail address. An Account without an e-mail address cannot be recovered if you lose the password.</li>
		<li>Keep your sign-in details to yourself.</li>
		<li>You can delete your Account at any time with one click in the Account settings. No reason needed; deletion ends the Account agreement immediately.</li>
		<li>We may terminate the Account agreement for a serious reason (a material breach of section 8) on 14 days’ notice, telling you why by e-mail or, if the Account has no e-mail address, with a notice after sign-in.</li>
	</ul>
	<h2 id="editions" class="h2">6. Free and paid editions</h2>
	<ul>
		<li>The free edition of the App costs nothing and has no time limit.</li>
		<li>A paid edition is planned but <strong>not on sale</strong>. Any prices on the Website are a pricing hypothesis we are testing. Picking a price option on the waitlist is not an order and creates no obligation to pay.</li>
		<li>Before we sell anything, these Terms will be extended with prices, payment methods (we plan to use a Merchant of Record payment provider), contract duration and cancellation rules.</li>
	</ul>
	<h2 id="consumer" class="h2">7. Your rights as a consumer</h2>
	<ul>
		<li>If you are a consumer and conclude a contract at a distance, you may withdraw within 14 days without giving a reason (Article 27 of the Polish Consumer Rights Act).</li>
		<li>For paid digital content not supplied on a tangible medium, the right of withdrawal ends once supply begins, but only if you gave your express prior consent, acknowledged that you would lose the right, and we sent you confirmation (Article 38(1)(13) of the Act). We will ask for this with a separate, unticked checkbox.</li>
		<li>We are responsible for the App conforming to the contract under Chapter 5b of the Act, and we will provide and tell you about updates, including security updates, needed to keep it conforming for as long as you can reasonably expect (Article 43k).</li>
		<li>Sole traders covered by Article 38a get the same protection.</li>
	</ul>
	<h2 id="use" class="h2">8. Acceptable use and model licences</h2>
	<ul>
		<li>Do not use the services to create or share unlawful content or in a way that breaks the law or infringes anyone’s rights.</li>
		<li>Every Model comes under its creator’s licence, which the App shows before download, and you agree to follow it. In particular: Gemma models (up to and including Gemma 3) are subject to the <em>Gemma Prohibited Use Policy</em>; gpt-oss models are subject to their creator’s usage policy.</li>
		<li>We do not offer Llama 4 models because of their licence terms, and we do not offer “uncensored” models with their safeguards removed.</li>
		<li>Do not circumvent the App’s security, disrupt the Website, or reverse-engineer the App beyond what mandatory law allows.</li>
	</ul>
	<h2 id="ai" class="h2">9. AI and honest performance claims</h2>
	<p>The App is an AI system. Model outputs can be wrong, incomplete or out of date, and they are not legal, medical or financial advice. See the <a href={href(L, '/legal/ai')}>AI Notice</a>.</p>
	<p>In line with the EU Unfair Commercial Practices Directive (2005/29/EC) and its Polish implementation, every speed claim we make is a measurement on named hardware, with its source, configuration and method documented on the <a href={href(L, '/methodology')}>Methodology</a> page. Anything untested is labelled as an estimate or “soon”. Your results may differ.</p>
	<h2 id="liability" class="h2">10. Liability</h2>
	<ul>
		<li>We take reasonable care to keep the services running, apart from maintenance windows.</li>
		<li>If you are not a consumer, our liability is limited to actual loss and excludes lost profits, to the extent the law allows.</li>
		<li>If you are a consumer, nothing in these Terms excludes or limits our liability where mandatory law forbids it, including your remedies when digital content does not conform to the contract.</li>
		<li>We are not responsible for what a Model generates at your request or for how you use it, unless that results from the App not conforming to the contract.</li>
	</ul>
	<h2 id="complaints" class="h2">11. Complaints</h2>
	<ul>
		<li>Send complaints to the e-mail address in section 1 (it will be published once the company is registered).</li>
		<li>Please include your contact details, a description of the problem and what you would like us to do. We will still handle complaints that miss some of this.</li>
		<li>We will reply within 14 days. If we do not, the consumer’s complaint is deemed accepted to the extent provided by law.</li>
	</ul>
	<h2 id="adr" class="h2">12. Out-of-court dispute resolution</h2>
	<p>If you are a consumer, you can use out-of-court routes, including your local consumer ombudsman (rzecznik konsumentów), the regional Trade Inspection, and the information provided by the Polish competition and consumer authority at <a href="https://polubowne.uokik.gov.pl/" rel="noopener">polubowne.uokik.gov.pl</a>.</p>
	<p>The European Commission’s ODR platform was shut down on 20 July 2025 under Regulation (EU) 2024/3228, so we do not link to it.</p>
	<h2 id="law" class="h2">13. Governing law</h2>
	<p>Polish law applies. If you are a consumer, this does not deprive you of the protection of mandatory rules of the country where you habitually live (Article 6(2) of the Rome I Regulation).</p>
	<p>Disputes with non-consumers go to the court with jurisdiction over our registered office.</p>
	<h2 id="changes" class="h2">14. Changes to these Terms</h2>
	<p>We may change these Terms for a valid reason, such as a change in the law, in the scope of the services, or in security requirements. Account holders will be told at least 14 days before a change takes effect (by e-mail if the Account has one, otherwise with a notice after sign-in) and may delete their Account before then if they disagree.</p>
	<p>Changes do not affect rights you acquired before they take effect.</p>
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
