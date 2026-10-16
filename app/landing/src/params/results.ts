import type { ParamMatcher } from '@sveltejs/kit';

/** First segment of the results page: `wyniki` (pl) or `results` (en). The pairing with the language is checked in the route's load. */
export const match = ((param: string): param is 'wyniki' | 'results' => param === 'wyniki' || param === 'results') satisfies ParamMatcher;
