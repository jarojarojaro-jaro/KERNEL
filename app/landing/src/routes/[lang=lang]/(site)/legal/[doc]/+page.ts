import { error } from '@sveltejs/kit';
import { LANGS } from '$lib/i18n';
import { LEGAL_SLUGS, findLegalDoc } from '$lib/legal/docs';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () =>
	LANGS.flatMap((lang) => LEGAL_SLUGS.map((doc) => ({ lang, doc })));

export const load: PageLoad = ({ params }) => {
	if (!findLegalDoc(params.doc)) error(404, 'Not found');
	return { slug: params.doc };
};
