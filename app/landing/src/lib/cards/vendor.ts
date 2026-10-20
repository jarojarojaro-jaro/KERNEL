/**
 * Maker identity colours for card surfaces (tiles, card-page headers, accents): NVIDIA green, AMD
 * red, Intel blue, Apple neutral. Identity only; speed is always the heat ramp.
 *
 * Use: put `style={vendorVars(card.vendor)}` on a wrapper, then in CSS
 *   rgb(var(--v) / a)  the maker colour at any alpha (glows, rims, washes)
 *   var(--v-hi)        a light tint for text and marks on dark (wordmark, small labels)
 *   var(--v-deep)      the near-black base tinted with the maker colour
 *   var(--v-grad)      the showroom background: maker wash from the top-left over the deep base
 *   var(--v-line)      a 1-2 px accent line that fades out to the right
 * Surfaces that use these are dark in both themes (product showroom), so their text uses the dark
 * palette (see CardsTeaser `.tile`).
 */
export type Vendor = 'nvidia' | 'amd' | 'intel' | 'apple';

export const VENDOR: Record<Vendor | 'other', { name: string; rgb: string; hi: string; deep: string }> = {
	nvidia: { name: 'NVIDIA', rgb: '118 185 0', hi: '#9be22a', deep: '#0b1405' },
	amd: { name: 'AMD', rgb: '237 28 36', hi: '#ff5a5f', deep: '#170607' },
	intel: { name: 'Intel', rgb: '0 113 197', hi: '#4fb3ff', deep: '#04101c' },
	apple: { name: 'Apple', rgb: '190 194 204', hi: '#e8eaef', deep: '#0f1012' },
	/** Anything else (CPU-only entries): neutral, no wordmark. */
	other: { name: '', rgb: '150 156 168', hi: '#d4d7de', deep: '#0e0f11' }
};

export const vendorOf = (v: string): Vendor | 'other' => (v in VENDOR ? (v as Vendor) : 'other');

/** The CSS custom properties of a maker (see the module comment). */
export function vendorVars(v: string): string {
	const { rgb, hi, deep } = VENDOR[vendorOf(v)];
	return [
		`--v:${rgb}`,
		`--v-hi:${hi}`,
		`--v-deep:${deep}`,
		`--v-grad:radial-gradient(90% 55% at 50% 34%, rgb(${rgb} / 0.3), transparent 70%), linear-gradient(155deg, rgb(${rgb} / 0.34), rgb(${rgb} / 0.06) 32%, transparent 52%), linear-gradient(200deg, ${deep}, #070708 62%)`,
		`--v-line:linear-gradient(90deg, rgb(${rgb} / 0.9), rgb(${rgb} / 0.25) 55%, transparent)`
	].join('; ');
}

/**
 * AI-generated product renders per maker (Higgsfield Marketing Studio, static/media/vendor/): generic,
 * unbranded hardware in the maker's colour family on a dark studio floor, no logos. `face` is the
 * hub block, `show` the maker page's showroom band, `chip` a faint backdrop of that band. Each file
 * exists as `<name>-640` and `<name>-1024` in AVIF and WebP. Set an entry to null to fall back to the
 * SVG render (GpuArt) when a generated image looks wrong.
 */
export type RenderKind = 'face' | 'show' | 'chip';
export const RENDER: Record<Vendor, Record<RenderKind, string | null>> = {
	nvidia: { face: 'nvidia-face', show: 'nvidia-show', chip: 'nvidia-chip' },
	amd: { face: 'amd-face', show: 'amd-show', chip: 'amd-chip' },
	intel: { face: 'intel-face', show: 'intel-show', chip: 'intel-chip' },
	apple: { face: 'apple-face', show: 'apple-show', chip: 'apple-chip' }
};

/** `srcset` of a render in one format (both widths), or null when the maker has none of that kind. */
export function renderSet(v: string, kind: RenderKind, ext: 'avif' | 'webp'): string | null {
	const vend = vendorOf(v);
	const name = vend === 'other' ? null : RENDER[vend][kind];
	return name ? `/media/vendor/${name}-640.${ext} 640w, /media/vendor/${name}-1024.${ext} 1024w` : null;
}
