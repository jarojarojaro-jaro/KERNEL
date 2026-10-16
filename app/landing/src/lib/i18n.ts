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

/** Same page in the other language (keeps the rest of the path and the query). */
export function switchLangHref(to: Lang): string {
	const parts = page.url.pathname.split('/');
	parts[1] = to;
	return parts.join('/') || `/${to}`;
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

export function num(v: number, lang: Lang, digits = 1): string {
	return v.toLocaleString(lang === 'pl' ? 'pl-PL' : 'en-US', {
		minimumFractionDigits: digits,
		maximumFractionDigits: digits
	});
}
