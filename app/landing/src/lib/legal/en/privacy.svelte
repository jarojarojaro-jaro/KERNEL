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
	<h1 class="h1">Privacy Policy</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Contents</h2>
		<ol>
			<li><a href="#controller">1. Who is responsible for your data</a></li>
			<li><a href="#principle">2. Our principle: as little data as possible</a></li>
			<li><a href="#website">3. The website</a></li>
			<li><a href="#waitlist">4. The waitlist</a></li>
			<li><a href="#account">5. Your account</a></li>
			<li><a href="#scan">6. The hardware scan</a></li>
			<li><a href="#app">7. The desktop app</a></li>
			<li><a href="#recipients">8. Recipients and processors</a></li>
			<li><a href="#transfers">9. Transfers outside the EEA</a></li>
			<li><a href="#retention">10. How long we keep data</a></li>
			<li><a href="#rights">11. Your rights</a></li>
			<li><a href="#automated">12. Automated decision-making</a></li>
			<li><a href="#changes">13. Changes to this policy</a></li>
		</ol>
	</nav>
	<h2 id="controller" class="h2">1. Who is responsible for your data</h2>
	<p>The controller of personal data processed in connection with {BRAND.name} will be the company listed below once it is registered:</p>
	<CompanyData lang={L} fields={['legalName', 'address', 'krs', 'nip', 'email', 'dpo']} />
	<p>We will assess whether we must appoint a data protection officer (Art. 37 GDPR); with the current, minimal processing we probably do not.</p>
	<h2 id="principle" class="h2">2. Our principle: as little data as possible</h2>
	<p>The product is built to run locally. Models, prompts and conversations stay on your device and never reach us. Telemetry in the App is off by default. The Website uses no analytics and no trackers.</p>
	<h2 id="website" class="h2">3. The website</h2>
	<p>We use no analytics, no ad pixels and no profiling. Our hosting server keeps technical request logs, including your IP address. Because an IP address can be personal data (CJEU, 19 October 2016, C-582/14, <em>Breyer</em>), we treat these logs as personal data. For browser storage, see the <a href={href(L, '/legal/cookies')}>Cookie Policy</a>.</p>
	<h2 id="waitlist" class="h2">4. The waitlist</h2>
	<p>If you join the waitlist, we process your e-mail address and the price option you picked. You confirm your sign-up through a link we e-mail you (double opt-in). The legal basis is your consent (Art. 6(1)(a) GDPR). You can withdraw it at any time via the link in every e-mail or by writing to us; this does not affect processing that took place before.</p>
	<p><strong>Current status:</strong> the form’s backend is not live, so the form on the Website currently sends nothing.</p>
	<h2 id="account" class="h2">5. Your account</h2>
	<p>For an Account we process your e-mail address, and if you sign in with Google or GitHub, your account identifier with that provider and your e-mail address. We request only minimal scopes (for example <code>openid email</code> on Google and <code>user:email</code> on GitHub). We never access your contacts, repositories or anything else.</p>
	<h2 id="scan" class="h2">6. The hardware scan</h2>
	<p>The scan runs locally and sends nothing on its own. It produces a single-line code that you can read in full. If you paste that code into the form on our Website, it is processed only in your browser and never reaches our server.</p>
	<div class="table-wrap">
		<table class="table">
			<caption class="sr-only">Hardware scan scope</caption>
			<thead><tr><th scope="col">Read locally (needed to match a model)</th><th scope="col">Never read</th></tr></thead>
			<tbody>
				<tr><td>operating system and version; CPU (model, threads, AVX2/AVX-512); total RAM</td><td>computer name (hostname), user name, home directory paths</td></tr>
				<tr><td>GPU: vendor, model, VRAM, driver version, target architecture, PCIe generation and width</td><td>serial numbers, GPU UUIDs, MAC addresses, disk serials</td></tr>
				<tr><td>available compute backends (CUDA, ROCm, Vulkan, Metal) and their versions</td><td>kernel boot parameters, dmesg, system logs</td></tr>
				<tr><td>free space on the selected drive</td><td>file lists, installed applications, history</td></tr>
				<tr><td>power source (AC / battery) and temperatures — live and local only</td><td>location, IP geolocation, the content of prompts and chats</td></tr>
			</tbody>
		</table>
	</div>
	<p>We access information on your device only to provide the service you explicitly asked for (matching a Model), which falls within the exemption in Article 5(3) of the ePrivacy Directive 2002/58/EC and Article 399(2) of the Polish Electronic Communications Law. Sending anything to us always requires separate consent.</p>
	<h2 id="app" class="h2">7. The desktop app</h2>
	<p>Telemetry is off by default. We split telemetry into three independent categories; consent for each is separate and off until you give it:</p>
	<ol>
		<li><strong>Crash reports</strong> — before each report is sent you see exactly what it contains and can discard it.</li>
		<li><strong>Share acceleration profile anonymously</strong> — we receive hardware, Model, settings and benchmark result, with no IP address and no installation ID. Our ingestion service drops the IP address on arrival and never stores it.</li>
		<li><strong>Usage statistics</strong> — we do not collect them at all. There is no switch because there is nothing to switch on; we mention it so you know the absence is deliberate.</li>
	</ol>
	<p>Your prompts and conversations never leave your device, whatever your settings. The local API listens only on your computer’s loopback interface.</p>
	<h2 id="recipients" class="h2">8. Recipients and processors</h2>
	<ul>
		<li>a hosting provider with its seat and servers in the EEA — <span class="badge badge--soon">to be chosen</span>; bound by a data processing agreement under Art. 28 GDPR;</li>
		<li>an e-mail delivery provider (waitlist, Account) — <span class="badge badge--soon">to be chosen</span>, preferably in the EEA;</li>
		<li>Google and GitHub — only if you choose to sign in with them; they act as separate controllers for their own services;</li>
		<li>a planned Merchant of Record payment provider such as Paddle — only once sales begin; it is a separate controller for payment data.</li>
	</ul>
	<h2 id="transfers" class="h2">9. Transfers outside the EEA</h2>
	<p>Signing in with Google or GitHub may involve transferring data to the United States. Such transfers rely on the European Commission’s adequacy decision for the EU-US Data Privacy Framework where the provider is certified, and otherwise on standard contractual clauses. If you would rather avoid this, sign in with your e-mail address.</p>
	<h2 id="retention" class="h2">10. How long we keep data</h2>
	<div class="table-wrap">
		<table class="table">
			<caption class="sr-only">Retention table</caption>
			<thead><tr><th scope="col">Context</th><th scope="col">Data</th><th scope="col">Purpose and legal basis</th><th scope="col">Retention</th></tr></thead>
			<tbody>
				<tr><td>Website (server logs)</td><td>IP address, date and time, requested URL, status code, user agent</td><td>security and availability — legitimate interests (Art. 6(1)(f) GDPR)</td><td>up to 14 days, then deleted (to be confirmed with the hosting provider)</td></tr>
				<tr><td>Waitlist</td><td>e-mail address, chosen price option, consent date and confirmation (double opt-in)</td><td>release notification and pricing research — consent (Art. 6(1)(a))</td><td>until you withdraw consent or 30 days after the paid edition launches; unconfirmed sign-ups — 7 days</td></tr>
				<tr><td>Account</td><td>e-mail address, Google/GitHub account ID, creation date</td><td>running your Account — performance of a contract (Art. 6(1)(b))</td><td>until you delete the Account; backups overwritten within 30 days</td></tr>
				<tr><td>Crash reports (optional)</td><td>stack trace, App version, OS, GPU model — after you preview them</td><td>fixing bugs — consent (Art. 6(1)(a))</td><td>90 days</td></tr>
				<tr><td>Acceleration profile (optional)</td><td>GPU model, driver, Model, settings and benchmark result; no IP, no installation ID</td><td>building the profile database — consent (Art. 6(1)(a)); once anonymised it is no longer personal data</td><td>indefinitely, as anonymous data</td></tr>
				<tr><td>Complaints and correspondence</td><td>contact details, your message</td><td>handling it — legal obligation and legal claims (Art. 6(1)(c) and (f))</td><td>until the limitation period for claims expires</td></tr>
			</tbody>
		</table>
	</div>
	<h2 id="rights" class="h2">11. Your rights</h2>
	<p>You have the right to:</p>
	<ul>
		<li>access your data and get a copy (Art. 15 GDPR);</li>
		<li>rectification (Art. 16);</li>
		<li>erasure (Art. 17);</li>
		<li>restriction of processing (Art. 18);</li>
		<li>data portability (Art. 20);</li>
		<li>object to processing based on legitimate interests (Art. 21);</li>
		<li>withdraw consent at any time, without affecting earlier processing;</li>
		<li>lodge a complaint with the Polish supervisory authority, the President of the Personal Data Protection Office (Prezes UODO, ul. Stawki 2, 00-193 Warsaw, uodo.gov.pl), or with the authority in your own EU country.</li>
	</ul>
	<p>Send requests to the controller’s e-mail address in section 1. We will reply without undue delay and within one month at the latest.</p>
	<h2 id="automated" class="h2">12. Automated decision-making</h2>
	<p>We do not make decisions based solely on automated processing, including profiling, that produce legal or similarly significant effects for you (Art. 22 GDPR). The hardware-based model recommendation is only a suggestion you can override.</p>
	<h2 id="changes" class="h2">13. Changes to this policy</h2>
	<p>We will announce material changes on the Website and e-mail Account holders in advance.</p>
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
