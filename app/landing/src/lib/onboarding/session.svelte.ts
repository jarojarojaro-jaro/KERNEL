/**
 * Onboarding account state, mirrored to sessionStorage (cleared when the tab closes). It comes only
 * from a live auth backend (`getSession()`); with `PUBLIC_AUTH_PROVIDER=none` the account step is a
 * preview and nothing is stored.
 */
import { browser } from '$app/environment';
import { auth, type SignInMethod } from '$lib/auth';

export interface Session {
	account: { method: SignInMethod; email: string | null; name: string | null } | null;
}

const KEY = 'onboarding';

export const session = $state<Session>({ account: null });

export function loadSession() {
	if (!browser) return;
	if (!auth.live) {
		// Preview build: drop anything an older prototype build left behind.
		try {
			sessionStorage.removeItem(KEY);
		} catch {
			/* storage blocked: nothing to clear */
		}
		return;
	}
	try {
		Object.assign(session, JSON.parse(sessionStorage.getItem(KEY) ?? '{}'));
	} catch {
		/* ignore corrupted state */
	}
	// Back from an OAuth round trip, or a returning visitor: the backend is the truth.
	auth.getSession().then((s) => {
		session.account = s ? { method: s.user.method, email: s.user.email, name: s.user.name } : null;
		try {
			sessionStorage.setItem(KEY, JSON.stringify(session));
		} catch {
			/* storage blocked: state lives for this page view only */
		}
	});
}
