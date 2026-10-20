import { page } from '$app/state';

export type Lang = 'pl' | 'en';
export const LANGS: readonly Lang[] = ['pl', 'en'];

/** Current language from the `[lang=lang]` route param. */
export function currentLang(): Lang {
	return page.params.lang === 'en' ? 'en' : 'pl';
}

/**
 * Localised href with the trailing slash the static build uses (`trailingSlash = 'always'`,
 * so every page is `<path>/index.html` and works on any static host):
 * `href('en', '/start')` → `/en/start/`, `href('pl', '/#faq')` → `/pl/#faq`.
 */
export function href(lang: Lang, path = '/'): string {
	const [p, hash] = path.split('#');
	const clean = p.replace(/^\/+|\/+$/g, '');
	return `/${lang}/${clean ? `${clean}/` : ''}${hash ? `#${hash}` : ''}`;
}

/** Localised first path segment of the cards explorer: `/pl/karty/`, `/en/cards/`. */
export const CARDS_SEG = { pl: 'karty', en: 'cards' } as const satisfies Record<Lang, string>;

/** Path of the cards explorer (optionally one card or the compare view) in a language. */
export function cardsHref(lang: Lang, rest = ''): string {
	return href(lang, `/${CARDS_SEG[lang]}/${rest}`);
}

/** Localised segment of the results page: `/pl/wyniki/`, `/en/results/`. */
export const RESULTS_SEG = { pl: 'wyniki', en: 'results' } as const satisfies Record<Lang, string>;

export function resultsHref(lang: Lang): string {
	return href(lang, `/${RESULTS_SEG[lang]}/`);
}

/** `pathname` translated to another language: swaps the lang prefix and localised segments. */
export function localizePath(pathname: string, to: Lang): string {
	const parts = pathname.split('/');
	parts[1] = to;
	if (parts[2] === CARDS_SEG.pl || parts[2] === CARDS_SEG.en) {
		parts[2] = CARDS_SEG[to];
		if (parts[3] === 'porownaj' || parts[3] === 'compare') parts[3] = to === 'pl' ? 'porownaj' : 'compare';
	}
	if (parts[2] === RESULTS_SEG.pl || parts[2] === RESULTS_SEG.en) parts[2] = RESULTS_SEG[to];
	return parts.join('/') || `/${to}`;
}

/** Same page in the other language (keeps the rest of the path). */
export function switchLangHref(to: Lang): string {
	return localizePath(page.url.pathname, to);
}

/**
 * Polish plural categories (CLDR: one / few / many). `plural(5, ['model', 'modele', 'modeli'])`.
 * English callers pass `[one, other, other]`.
 */
export function plural(n: number, forms: [string, string, string], lang: Lang = 'pl'): string {
	if (lang === 'en') return n === 1 ? forms[0] : forms[1];
	if (!Number.isInteger(n)) return forms[1];
	const m10 = n % 10;
	const m100 = n % 100;
	if (n === 1) return forms[0];
	if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return forms[1];
	return forms[2];
}

/** One Intl.NumberFormat per (lang, digits): `toLocaleString` with options builds a new formatter on every call. */
const NUM_FMT = new Map<string, Intl.NumberFormat>();

export function num(v: number, lang: Lang, digits = 1): string {
	const k = lang + digits;
	let f = NUM_FMT.get(k);
	if (!f) NUM_FMT.set(k, (f = new Intl.NumberFormat(lang === 'pl' ? 'pl-PL' : 'en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })));
	return f.format(v);
}
