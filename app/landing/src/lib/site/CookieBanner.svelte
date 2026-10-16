<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { currentLang, href } from '$lib/i18n';
	import { consent, initConsent, saveConsent } from './consent.svelte';
	import { copy } from './copy';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang].cookies);
	let details = $state(false);
	let analytics = $state(false);
	let panel: HTMLElement | undefined = $state();

	onMount(initConsent);

	$effect(() => {
		if (consent.open) {
			analytics = consent.record?.analytics ?? false;
			// Reopened from the footer: move focus to the panel. On the first visit we do not steal focus.
			if (consent.record) tick().then(() => panel?.focus());
		}
	});
</script>

{#if consent.ready && consent.open}
	<section class="cookie" aria-labelledby="cookie-title" tabindex="-1" bind:this={panel}>
		<div class="inner">
			<div class="text">
				<h2 id="cookie-title" class="h3">{t.title}</h2>
				<p class="small">{t.body} <a href={href(lang, '/legal/cookies')}>{t.policy}</a></p>
			</div>
			{#if details}
				<fieldset class="cats">
					<legend class="sr-only">{t.settings}</legend>
					<label class="switch"><input type="checkbox" checked disabled /> <span><strong>{t.necessary}</strong><br /><span class="hint">{t.necessaryHint}</span></span></label>
					<label class="switch"><input type="checkbox" bind:checked={analytics} /> <span><strong>{t.analytics}</strong><br /><span class="hint">{t.analyticsHint}</span></span></label>
				</fieldset>
			{/if}
			<div class="cluster buttons">
				<button class="btn btn--secondary btn--sm" type="button" onclick={() => saveConsent(false)}>{t.reject}</button>
				{#if details}
					<button class="btn btn--secondary btn--sm" type="button" onclick={() => saveConsent(analytics)}>{t.save}</button>
				{:else}
					<button class="btn btn--ghost btn--sm" type="button" aria-expanded={details} onclick={() => (details = true)}>{t.settings}</button>
				{/if}
				<button class="btn btn--secondary btn--sm" type="button" onclick={() => saveConsent(true)}>{t.accept}</button>
			</div>
		</div>
	</section>
{/if}

<style>
	.cookie {
		position: fixed;
		z-index: var(--z-banner);
		inset: auto var(--sp-4) var(--sp-4) auto;
		width: min(30rem, calc(100% - 2 * var(--sp-4)));
		background:
			linear-gradient(180deg, color-mix(in srgb, var(--text-hi) 3%, transparent), transparent 50%),
			var(--bg-2);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-xl);
		box-shadow: var(--shadow-2);
		padding: var(--sp-6);
	}
	.cookie:focus {
		outline: none;
	}
	.cookie:focus-visible {
		outline: 2px solid var(--focus);
	}
	.inner {
		display: grid;
		gap: var(--sp-4);
	}
	.text {
		display: grid;
		gap: var(--sp-2);
	}
	.text h2 {
		font-size: var(--fs-md);
	}
	.cats {
		border: 0;
		padding: 0;
		margin: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.cats .switch {
		align-items: flex-start;
	}
	.buttons {
		justify-content: flex-end;
	}
</style>
