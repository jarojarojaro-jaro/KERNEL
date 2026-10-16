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
	<h1 class="h1">AI Notice</h1>
	<p class="source">{LEGAL_VERSION[L]}</p>
	<nav aria-labelledby="toc-title" class="card card--inset toc">
		<h2 id="toc-title" class="h3">Contents</h2>
		<ol>
			<li><a href="#system">1. You are using an AI system</a></li>
			<li><a href="#errors">2. Outputs can be wrong</a></li>
			<li><a href="#local">3. Models run on your device</a></li>
			<li><a href="#disclosure">4. How the app tells you</a></li>
			<li><a href="#marking">5. Marking AI-generated text</a></li>
			<li><a href="#media">6. No images or video</a></li>
			<li><a href="#role">7. Our role under the AI Act</a></li>
			<li><a href="#report">8. Reporting a problem</a></li>
		</ol>
	</nav>
	<h2 id="system" class="h2">1. You are using an AI system</h2>
	<p>{BRAND.name} runs language models on your computer. When you chat in the App, you are interacting with an artificial intelligence system, not a person. We tell you this under Article 50(1) of Regulation (EU) 2024/1689 (the AI Act).</p>
	<h2 id="errors" class="h2">2. Outputs can be wrong</h2>
	<p>Language models generate text statistically. They can state false facts, invent sources or give out-of-date information. Check anything that matters, and do not treat outputs as legal, medical or financial advice.</p>
	<h2 id="local" class="h2">3. Models run on your device</h2>
	<p>The Model runs on your own hardware. Your conversations are not sent to us or to the Model’s creator. Our acceleration changes how the Model is executed on your hardware; we do not alter the Model’s weights to change its behaviour.</p>
	<h2 id="disclosure" class="h2">4. How the app tells you</h2>
	<p>The first time you interact in a chat window, the App shows a clear message that you are talking to an AI system. In line with Article 50(5), it is clear, distinguishable and accessible: screen readers announce it, it does not disappear on a timer, and it meets WCAG 2.2 AA contrast.</p>
	<h2 id="marking" class="h2">5. Marking AI-generated text</h2>
	<p>Article 50(2) requires providers of AI systems that generate text to mark outputs in a machine-readable way. We plan to watermark texts longer than 200 tokens. The watermark will be applied identically in “before” and “after” modes, so both produce comparable output and the speed-up stays independently verifiable.</p>
	<p><strong>Status:</strong> how this obligation applies to locally run models, and which method to use, is awaiting a legal opinion and a query to the Polish AI authority (KRiBSI). It is not implemented yet. We will describe it here before the App is released.</p>
	<h2 id="media" class="h2">6. No images or video</h2>
	<p>{BRAND.name} does not generate images, audio or video, including deepfakes, so the Article 50(4) obligations for such content do not apply to us.</p>
	<h2 id="role" class="h2">7. Our role under the AI Act</h2>
	<p>We are not a provider of a general-purpose AI (GPAI) model; the Models come from their creators. Our work concerns how a model is executed, and the compute used for any modification is far below the one-third-of-original-training-compute threshold that the European Commission’s guidelines use as the indicator for becoming a GPAI provider. We are, however, the provider of an AI system (the App) and we meet the Article 50 transparency obligations.</p>
	<p>In Poland, the AI Act is supervised by the Commission for the Development and Safety of Artificial Intelligence (KRiBSI), established by the Polish Act on Artificial Intelligence Systems.</p>
	<h2 id="report" class="h2">8. Reporting a problem</h2>
	<p>If a Model produced harmful or unlawful content, or you did not see the AI disclosure, write to us at the address below. With your permission, we will pass reports about a Model itself on to its creator.</p>
	<CompanyData lang={L} fields={['email']} />
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
