import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

/** The compare view is `/en/…/compare/` only. */
export const load: PageLoad = ({ params }) => {
	if (params.lang !== 'en') error(404, 'Not found');
};
