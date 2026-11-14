/**
 * Schema.org JSON-LD for the public site. The text is 1:1 with what was hand-added to the live
 * pages on 23.10.2026 (`repo/enigmalabz.com`), so the build matches the live site.
 *
 * Only the origin is built in: on a LAN preview (`SITE_ORIGIN` empty) absolute @ids would be wrong,
 * so callers get `null` and simply render no JSON-LD. That is also what the live site does on the
 * pages that have none.
 */
import { BRAND } from '$lib/brand';
import { SITE_ORIGIN } from '$lib/site/public';
import type { Lang } from '$lib/i18n';

const ORIGIN = SITE_ORIGIN;

/** Home page: Organization + WebSite + SoftwareApplication (3090 numbers: report 67, as on its card). */
export function homeGraph(lang: Lang): object[] | null {
	if (!ORIGIN) return null;
	const inLanguage = lang === 'pl' ? 'pl-PL' : 'en';
	const description =
		lang === 'pl'
			? 'Silnik do lokalnego uruchamiania modeli językowych, który na tym samym sprzęcie i tym samym modelu daje więcej tokenów na sekundę niż typowa aplikacja. Projekt w fazie prototypu, instalatory nie są jeszcze dostępne. Zmierzone tym samym skryptem po obu stronach, model Qwen3.8-27B: Radeon RX 7900 XTX 35,9 → 114,8 t/s (3,2×, metoda ABBA, odpowiedź 500 tokenów), GeForce RTX 3090 40,93 → 79,97 t/s (2,0×, kontekst 262 144).'
			: 'An engine for running language models locally that gets more tokens per second than a typical app on the same hardware and the same model. The project is a prototype; installers are not available yet. Measured with the same script on both sides, Qwen3.8-27B model: Radeon RX 7900 XTX 35.9 → 114.8 t/s (3.2×, ABBA method, 500-token answer), GeForce RTX 3090 40.93 → 79.97 t/s (2.0×, 262,144 context).';
	return [
		{
			'@type': 'Organization',
			'@id': `${ORIGIN}/#organization`,
			name: BRAND.name,
			url: `${ORIGIN}/`,
			logo: { '@type': 'ImageObject', url: `${ORIGIN}/apple-touch-icon.png`, width: 180, height: 180 }
		},
		{
			'@type': 'WebSite',
			'@id': `${ORIGIN}/${lang}/#website`,
			name: BRAND.name,
			url: `${ORIGIN}/${lang}/`,
			inLanguage,
			publisher: { '@id': `${ORIGIN}/#organization` }
		},
		{
			'@type': 'SoftwareApplication',
			'@id': `${ORIGIN}/${lang}/#app`,
			name: BRAND.name,
			url: `${ORIGIN}/${lang}/`,
			applicationCategory: 'DeveloperApplication',
			operatingSystem: 'Windows 10/11 (x64), Linux, macOS (Apple Silicon)',
			description,
			inLanguage,
			publisher: { '@id': `${ORIGIN}/#organization` }
		}
	];
}

export interface Crumb {
	name: string;
	/** Site-relative path with the build's trailing slash: '/pl/karty/rtx-3090/'. */
	path: string;
}

/** BreadcrumbList for the explorer pages (the live site has one on all 38). */
export function breadcrumbs(crumbs: Crumb[]): object | null {
	if (!ORIGIN) return null;
	return {
		'@type': 'BreadcrumbList',
		itemListElement: crumbs.map((c, i) => ({
			'@type': 'ListItem',
			position: i + 1,
			name: c.name,
			item: `${ORIGIN}${c.path}`
		}))
	};
}

/**
 * Crumb labels as the live pages spell them. Kept next to the builder so every explorer page
 * (index, maker, card, versus) uses the same words and the build matches the live site.
 */
export const CARD_CRUMBS = {
	pl: { root: 'Twoja karta', maker: (n: string) => `Karty ${n}`, compare: 'Porównaj karty' },
	en: { root: 'Your card', maker: (n: string) => `${n} cards`, compare: 'Compare cards' }
} as const;
