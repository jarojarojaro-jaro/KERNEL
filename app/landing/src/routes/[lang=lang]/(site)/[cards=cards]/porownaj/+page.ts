import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

/** The compare view is `/pl/…/porownaj/` only. */
export const load: PageLoad = ({ params }) => {
	if (params.lang !== 'pl') error(404, 'Not found');
};
