import type { ParamMatcher } from '@sveltejs/kit';

/** Maker pages of the cards explorer (`/pl/karty/nvidia/`). A matched route wins over `[id]`; no card id is a maker name. */
export const match = ((param: string): param is 'nvidia' | 'amd' | 'intel' | 'apple' => param === 'nvidia' || param === 'amd' || param === 'intel' || param === 'apple') satisfies ParamMatcher;
