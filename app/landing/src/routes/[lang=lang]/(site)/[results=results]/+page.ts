import { error } from '@sveltejs/kit';
import { LANGS, RESULTS_SEG } from '$lib/i18n';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () => LANGS.map((lang) => ({ lang, results: RESULTS_SEG[lang] }));

/** `wyniki` belongs to Polish and `results` to English; any other pairing is not a page. */
export const load: PageLoad = ({ params }) => {
	if (RESULTS_SEG[params.lang as 'pl' | 'en'] !== params.results) error(404, 'Not found');
};
