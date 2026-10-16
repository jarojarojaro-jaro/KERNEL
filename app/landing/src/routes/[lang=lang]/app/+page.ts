import type { EntryGenerator } from './$types';

/** Prerender the prototype in both languages; every screen is crawled from the index links. */
export const entries: EntryGenerator = () => [{ lang: 'pl' }, { lang: 'en' }];
