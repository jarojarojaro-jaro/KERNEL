/**
 * One way to print every kind of number on the site (home, cards explorer, methodology).
 * Locale decimals (PL comma, EN dot), one multiplier style, one memory unit.
 */
import { num, type Lang } from '$lib/i18n';

/** Digits for a speed-up factor: two below ×1.2 (so ×1.05 does not round to ×1.1), else one. */
export const ratioDigits = (ratio: number) => (ratio < 1.2 ? 2 : 1);

/** Speed-up factor, always suffix style: "2,0×", "1,05×". */
export const fmtRatio = (ratio: number, lang: Lang) => `${num(ratio, lang, ratioDigits(ratio))}×`;

/** Tokens per second: one decimal ("78,0"). */
export const fmtTps = (v: number, lang: Lang) => num(v, lang, 1);

/** Seconds: one decimal ("17,3 s"). */
export const fmtSec = (v: number, lang: Lang) => `${num(v, lang, 1)}\u00a0s`;

/**
 * Memory, one decimal, labelled "GB" the way GPU vendors label VRAM (a "16 GB" card has 16 GiB).
 * Some sources print GiB (5060 Ti sheet); those values are shown as-is so they compare directly
 * with the card's capacity, and `binary` tells the caller to say so in the source tip.
 */
export function fmtGB(v: number, unit: string | undefined, lang: Lang): { text: string; binary: boolean } {
	return { text: `${num(v, lang, 1)}\u00a0GB`, binary: unit === 'GiB' };
}

/** Text of the sheet's prose cells for the current page: dot decimals become commas in Polish. */
export const localizeDecimals = (s: string, lang: Lang) => (lang === 'pl' ? s.replace(/(\d)\.(\d)/g, '$1,$2') : s);
