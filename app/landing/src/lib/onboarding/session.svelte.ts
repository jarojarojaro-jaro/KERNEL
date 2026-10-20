/**
 * Onboarding state. Lives in sessionStorage only (cleared when the tab closes). With
 * `PUBLIC_AUTH_PROVIDER=none` there is no account backend: the account step records a waitlist
 * sign-up here and nothing is sent. With a live backend the account comes from `getSession()`.
 */
import { browser } from '$app/environment';
import { auth, type SignInMethod } from '$lib/auth';

export interface Session {
	account: { method: SignInMethod | 'waitlist'; email: string | null } | null;
	/** Optional news consent ticked on the account step (kept across the OAuth round trip). */
	marketing: boolean;
}

const KEY = 'onboarding';

export const session = $state<Session>({ account: null, marketing: false });

export function loadSession() {
	if (!browser) return;
	try {
		Object.assign(session, JSON.parse(sessionStorage.getItem(KEY) ?? '{}'));
	} catch {
		/* ignore corrupted state */
	}
	if (auth.live) {
		// Back from an OAuth / magic-link round trip, or a returning visitor: the backend is the truth.
		auth.getSession().then((s) => {
			if (s) session.account = { method: s.user.method, email: s.user.email };
			else if (session.account?.method !== 'waitlist') session.account = null;
			saveSession();
		});
	}
}

export function saveSession() {
	try {
		sessionStorage.setItem(KEY, JSON.stringify(session));
	} catch {
		/* storage blocked: state lives for this page view only */
	}
}
