import { error } from '@sveltejs/kit';
import { ENTRIES, findEntry } from '$lib/cards/explorer';
import { CARDS_SEG, LANGS } from '$lib/i18n';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () => LANGS.flatMap((lang) => ENTRIES.map((e) => ({ lang, cards: CARDS_SEG[lang], id: e.id })));

export const load: PageLoad = ({ params }) => {
	if (!findEntry(params.id)) error(404, 'Not found');
	return { id: params.id };
};
