/**
 * Prototype onboarding state. Lives in sessionStorage only (cleared when the tab closes) and is
 * never sent anywhere: there is no auth backend yet (labelled on every onboarding page).
 */
import { browser } from '$app/environment';

export interface Session {
	account: { method: 'google' | 'github' | 'email'; email: string | null; marketing: boolean } | null;
}

const KEY = 'onboarding';

export const session = $state<Session>({ account: null });

export function loadSession() {
	if (!browser) return;
	try {
		Object.assign(session, JSON.parse(sessionStorage.getItem(KEY) ?? '{}'));
	} catch {
		/* ignore corrupted state */
	}
}

export function saveSession() {
	try {
		sessionStorage.setItem(KEY, JSON.stringify(session));
	} catch {
		/* storage blocked: state lives for this page view only */
	}
}
