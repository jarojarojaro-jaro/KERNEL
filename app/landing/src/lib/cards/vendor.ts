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

/**
 * Photoreal product shots (AI-generated with OpenRouter `openai/gpt-image-2.5-sunburst`, static/media/cards/):
 * the real products, not generic hardware, from one camera (3/4 front, slightly from above, soft key light
 * from the top left) on a transparent 3:2 canvas, product centred. Markings are the products' own, small.
 * No studio black to blend away: draw glows and light stripes BEHIND the photo. Each file exists as
 * `<id>-480|800|1200` in AVIF and WebP (ProductPhoto renders them).
 */
export type PhotoId = 'rx-7900-xtx-pulse' | 'rtx-3090-fe' | 'arc-b580' | 'mac-studio';
export const PHOTO_W = 1200;
export const PHOTO_H = 800;
const PHOTO_WIDTHS = [480, 800, 1200];
export const PHOTO: Record<PhotoId, { alt: { pl: string; en: string } }> = {
	'rx-7900-xtx-pulse': { alt: { pl: 'Karta Sapphire PULSE Radeon RX 7900 XTX', en: 'Sapphire PULSE Radeon RX 7900 XTX graphics card' } },
	'rtx-3090-fe': { alt: { pl: 'Karta GeForce RTX 3090 Founders Edition', en: 'GeForce RTX 3090 Founders Edition graphics card' } },
	'arc-b580': { alt: { pl: 'Karta Intel Arc B580 Limited Edition', en: 'Intel Arc B580 Limited Edition graphics card' } },
	'mac-studio': { alt: { pl: 'Komputer Apple Mac Studio', en: 'Apple Mac Studio computer' } }
};
/** Each maker's hero product: the hub block and the maker page's showroom. */
export const MAKER_PHOTO: Record<Vendor, PhotoId> = { nvidia: 'rtx-3090-fe', amd: 'rx-7900-xtx-pulse', intel: 'arc-b580', apple: 'mac-studio' };
/**
 * Card pages that show a photo: only the exact model (the 7900 XTX page is our lab's PULSE), and the
 * Mac Studio only for the Apple chips it ships with. Every other card keeps the SVG render.
 */
const CARD_PHOTO: Record<string, PhotoId> = {
	'rx-7900-xtx': 'rx-7900-xtx-pulse',
	'rtx-3090': 'rtx-3090-fe',
	'arc-b580': 'arc-b580',
	'apple-m1-max': 'mac-studio',
	'apple-m2-max': 'mac-studio',
	'apple-m4-max': 'mac-studio'
};
export const photoOf = (cardId: string): PhotoId | null => CARD_PHOTO[cardId] ?? null;

/** `srcset` of a photo in one format. */
export const photoSet = (id: PhotoId, ext: 'avif' | 'webp'): string => PHOTO_WIDTHS.map((w) => `/media/cards/${id}-${w}.${ext} ${w}w`).join(', ');
