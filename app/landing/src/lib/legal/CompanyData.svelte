<script lang="ts">
	import { BRAND } from '$lib/brand';
	import type { Lang } from '$lib/i18n';

	/** Renders company data fields from BRAND.company; empty values show an explicit "to be filled" badge. */
	let { lang, fields = ['legalName', 'address', 'krs', 'nip', 'regon', 'email'] }: {
		lang: Lang;
		fields?: (keyof typeof BRAND.company | 'dpo' | 'security')[];
	} = $props();

	const LABELS = {
		pl: {
			legalName: 'Firma (nazwa)',
			address: 'Adres siedziby',
			krs: 'Numer KRS',
			nip: 'NIP',
			regon: 'REGON',
			email: 'Adres e-mail do kontaktu',
			dpo: 'Inspektor ochrony danych (IOD)',
			security: 'Kontakt ds. zgłoszeń bezpieczeństwa'
		},
		en: {
			legalName: 'Company name',
			address: 'Registered office',
			krs: 'KRS number (National Court Register)',
			nip: 'NIP (tax ID)',
			regon: 'REGON (statistical ID)',
			email: 'Contact e-mail',
			dpo: 'Data protection officer (DPO)',
			security: 'Security contact'
		}
	} as const;

	const EMPTY = { pl: '— (do uzupełnienia po rejestracji spółki)', en: '— (to be completed after company registration)' };

	function value(k: (typeof fields)[number]): string | null {
		if (k === 'dpo' || k === 'security') return null;
		return BRAND.company[k];
	}
</script>

<dl class="company">
	{#each fields as k (k)}
		<div class="company__row">
			<dt>{LABELS[lang][k]}</dt>
			<dd>
				{#if value(k)}
					{value(k)}
				{:else}
					<span class="badge badge--soon">{EMPTY[lang]}</span>
				{/if}
			</dd>
		</div>
	{/each}
</dl>

<style>
	.company {
		display: grid;
		gap: var(--sp-2);
		margin: var(--sp-4) 0;
		padding: var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-1);
	}
	.company__row {
		display: grid;
		grid-template-columns: minmax(10rem, 1fr) 2fr;
		gap: var(--sp-3);
	}
	dt {
		color: var(--text-mute);
	}
	dd {
		margin: 0;
	}
	@media (max-width: 40rem) {
		.company__row {
			grid-template-columns: 1fr;
			gap: var(--sp-1);
		}
	}
</style>
