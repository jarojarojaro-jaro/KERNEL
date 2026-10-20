/**
 * `PUBLIC_AUTH_PROVIDER=none` (default): no account backend exists yet. Every sign-in answers
 * `unavailable`, there is never a session, and nothing leaves the browser. The account step treats
 * `unavailable` as a preview and simply continues to the next step without storing anything.
 */
import type { AuthClient } from './types';

export const noneClient: AuthClient = {
	backend: 'none',
	live: false,
	signInWith: async () => ({ status: 'unavailable' }),
	signInWithPassword: async () => ({ status: 'unavailable' }),
	signUpWithPassword: async () => ({ status: 'unavailable' }),
	getSession: async () => null,
	signOut: async () => {}
};
