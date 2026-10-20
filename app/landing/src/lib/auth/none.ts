/**
 * `PUBLIC_AUTH_PROVIDER=none` (default): no account backend exists yet. Every sign-in answers
 * `unavailable`, there is never a session, and nothing leaves the browser. The account step renders
 * the Google/GitHub buttons disabled and routes people to the waitlist e-mail field instead.
 */
import type { AuthClient } from './types';

export const noneClient: AuthClient = {
	backend: 'none',
	live: false,
	signInWith: async () => ({ status: 'unavailable' }),
	signInWithEmail: async () => ({ status: 'unavailable' }),
	getSession: async () => null,
	signOut: async () => {}
};
