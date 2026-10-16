import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
	const seg = event.url.pathname.split('/')[1];
	const lang = seg === 'en' ? 'en' : 'pl';
	return resolve(event, { transformPageChunk: ({ html }) => html.replace('%lang%', lang) });
};
