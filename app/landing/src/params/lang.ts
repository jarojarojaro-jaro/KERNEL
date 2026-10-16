import type { ParamMatcher } from '@sveltejs/kit';

export const match = ((param: string): param is 'pl' | 'en' => param === 'pl' || param === 'en') satisfies ParamMatcher;
