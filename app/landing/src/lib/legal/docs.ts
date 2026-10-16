import type { Component } from 'svelte';
import type { Lang } from '$lib/i18n';
import TermsPl from './pl/terms.svelte';
import PrivacyPl from './pl/privacy.svelte';
import CookiesPl from './pl/cookies.svelte';
import AiPl from './pl/ai.svelte';
import ImprintPl from './pl/imprint.svelte';
import TermsEn from './en/terms.svelte';
import PrivacyEn from './en/privacy.svelte';
import CookiesEn from './en/cookies.svelte';
import AiEn from './en/ai.svelte';
import ImprintEn from './en/imprint.svelte';

export const LEGAL_VERSION: Record<Lang, string> = {
	pl: 'Projekt v0.1, 2026-10-16',
	en: 'Draft v0.1, 2026-10-16'
};

export type LegalSlug = 'terms' | 'privacy' | 'cookies' | 'ai' | 'imprint';

export interface LegalDoc {
	slug: LegalSlug;
	title: Record<Lang, string>;
	description: Record<Lang, string>;
	version: Record<Lang, string>;
	component: Record<Lang, Component>;
}

export const LEGAL_DOCS: readonly LegalDoc[] = [
	{
		slug: 'terms',
		title: { pl: 'Regulamin', en: 'Terms of Service' },
		description: {
			pl: 'Zasady korzystania ze strony, konta, aplikacji, CLI i lokalnego API; prawa konsumenta i reklamacje.',
			en: 'Rules for the website, account, desktop app, CLI and local API; consumer rights and complaints.'
		},
		version: LEGAL_VERSION,
		component: { pl: TermsPl, en: TermsEn }
	},
	{
		slug: 'privacy',
		title: { pl: 'Polityka prywatności', en: 'Privacy Policy' },
		description: {
			pl: 'Jakie dane przetwarzamy (niewiele), dlaczego, jak długo i jakie masz prawa (RODO).',
			en: 'What data we process (very little), why, for how long, and your GDPR rights.'
		},
		version: LEGAL_VERSION,
		component: { pl: PrivacyPl, en: PrivacyEn }
	},
	{
		slug: 'cookies',
		title: { pl: 'Polityka cookies', en: 'Cookie Policy' },
		description: {
			pl: 'Bez śledzących cookies. Pełna lista tego, co strona zapisuje w przeglądarce.',
			en: 'No tracking cookies. A complete list of what the site stores in your browser.'
		},
		version: LEGAL_VERSION,
		component: { pl: CookiesPl, en: CookiesEn }
	},
	{
		slug: 'ai',
		title: { pl: 'Informacja o AI', en: 'AI Notice' },
		description: {
			pl: 'Obowiązki przejrzystości z art. 50 AI Act: z czym rozmawiasz i jak oznaczamy treści.',
			en: 'AI Act Article 50 transparency: what you are talking to and how outputs are marked.'
		},
		version: LEGAL_VERSION,
		component: { pl: AiPl, en: AiEn }
	},
	{
		slug: 'imprint',
		title: { pl: 'Dane firmy', en: 'Imprint' },
		description: {
			pl: 'Dane usługodawcy i kontakt ds. bezpieczeństwa — uzupełnimy po rejestracji spółki.',
			en: 'Provider details and security contact — to be completed once the company is registered.'
		},
		version: LEGAL_VERSION,
		component: { pl: ImprintPl, en: ImprintEn }
	}
];

export const LEGAL_SLUGS: readonly LegalSlug[] = LEGAL_DOCS.map((d) => d.slug);

export function findLegalDoc(slug: string): LegalDoc | undefined {
	return LEGAL_DOCS.find((d) => d.slug === slug);
}
