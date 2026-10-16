import type { ParamMatcher } from '@sveltejs/kit';

/** First segment of the cards explorer: `karty` (pl) or `cards` (en). The pairing with the language is checked in the route's load. */
export const match = ((param: string): param is 'karty' | 'cards' => param === 'karty' || param === 'cards') satisfies ParamMatcher;
