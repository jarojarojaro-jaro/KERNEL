import { error } from '@sveltejs/kit';
import { CARDS_SEG } from '$lib/i18n';
import type { LayoutLoad } from './$types';

/** `karty` belongs to Polish and `cards` to English; any other pairing is not a page. */
export const load: LayoutLoad = ({ params }) => {
	if (CARDS_SEG[params.lang as 'pl' | 'en'] !== params.cards) error(404, 'Not found');
};
