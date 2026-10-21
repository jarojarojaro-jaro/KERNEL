import { goto } from '$app/navigation';
import { signInWith, signInWithPassword, signUpWithPassword, type AuthErrorCode, type AuthResult, type OAuthProvider } from '$lib/auth';
import { href, type Lang } from '$lib/i18n';

export const USERNAME_RE = /^[A-Za-z0-9._-]{3,32}$/;
export const MIN_PASSWORD = 10;

export type Method = OAuthProvider | { mode: 'signin' | 'signup'; username: string; password: string };

/**
 * Runs one account method and continues to /start/paths. With `PUBLIC_AUTH_PROVIDER=none` every
 * method answers `unavailable` and we just move on (nothing is sent or stored); a real provider
 * either redirects (OAuth, the browser leaves) or answers ok/error. Returns the error code to show,
 * or null when the page is navigating away.
 */
export async function authenticate(lang: Lang, method: Method): Promise<AuthErrorCode | null> {
	const next = href(lang, '/start/paths');
	let res: AuthResult;
	if (typeof method === 'string') res = await signInWith(method, { redirectTo: next });
	else if (method.mode === 'signup') res = await signUpWithPassword(method.username, method.password, { redirectTo: next });
	else res = await signInWithPassword(method.username, method.password, { redirectTo: next });
	if (res.status === 'redirecting') return null;
	if (res.status === 'unavailable') {
		await goto(next);
		return null;
	}
	return res.code;
}
