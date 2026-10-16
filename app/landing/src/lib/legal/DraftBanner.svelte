<script lang="ts">
	import type { Lang } from '$lib/i18n';
	import { LEGAL_VERSION } from './docs';

	let { lang }: { lang: Lang } = $props();
</script>

<div class="notice notice--warn draft" role="note">
	<span class="notice__icon" aria-hidden="true">!</span>
	<div class="stack">
		{#if lang === 'pl'}
			<p><strong>Projekt do weryfikacji przez prawnika.</strong> {LEGAL_VERSION.pl}. Treść nie jest jeszcze wiążąca i nie stanowi porady prawnej.</p>
			<p>Spółka nie została jeszcze zarejestrowana, dlatego pola z danymi administratora i dostawcy są celowo puste. <span class="badge badge--soon wrap">Dane firmy zostaną uzupełnione po rejestracji spółki (sp. z o.o.)</span></p>
		{:else}
			<p><strong>Draft — to be reviewed by a lawyer.</strong> {LEGAL_VERSION.en}. This text is not yet binding and is not legal advice.</p>
			<p>The company has not been registered yet, so the controller and provider data fields are intentionally empty. <span class="badge badge--soon wrap">Company details will be added once the company (sp. z o.o.) is registered</span></p>
		{/if}
	</div>
</div>

<style>
	.wrap {
		white-space: normal;
	}
	.draft {
		margin-block-end: var(--sp-8);
	}
	.draft p {
		margin: 0;
	}
</style>
