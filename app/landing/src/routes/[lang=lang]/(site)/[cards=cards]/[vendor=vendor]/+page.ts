import { VENDORS } from '$lib/cards/explorer';
import { CARDS_SEG, LANGS } from '$lib/i18n';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () => LANGS.flatMap((lang) => VENDORS.map((vendor) => ({ lang, cards: CARDS_SEG[lang], vendor })));

export const load: PageLoad = ({ params }) => ({ vendor: params.vendor });
