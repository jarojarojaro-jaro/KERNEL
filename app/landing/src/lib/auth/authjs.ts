/**
 * `PUBLIC_AUTH_PROVIDER=authjs`: browser side of Auth.js (`@auth/sveltekit`) running on this app's
 * own server. It speaks the Auth.js REST endpoints directly (same calls as `@auth/sveltekit/client`),
 * so the static build needs no extra package; the server half (adapter-node, `src/auth.ts`, the
 * `handle` hook, the session callback) is set up as described in AUTH.md.
 *
 * Integration points:
 * - `BASE` is the Auth.js `basePath` (default `/auth`); OAuth callbacks land on `/auth/callback/<id>`
 *   with ids `google`, `github`, `huggingface`.
 * - Two Credentials providers on the server: `password` (sign in) and `register` (create + sign in),
 *   both taking `username` + `password`. They report failures by throwing `CredentialsSignin`
 *   subclasses whose `code` (`invalid` | `taken` | `locked`) Auth.js appends to the error URL.
 * - `getSession` expects the server's `callbacks.session` to put `user.id`, `user.name` and the
 *   sign-in `provider` on the session (AUTH.md); the Credentials ids map to the `password` method.
 */
import type { AuthClient, AuthErrorCode, AuthResult, AuthSession, SignInMethod, SignInOptions } from './types';

const BASE = '/auth';
const CODES: Record<string, AuthErrorCode> = { invalid: 'invalid', taken: 'taken', locked: 'locked' };
const OAUTH_METHODS: Record<string, SignInMethod> = { google: 'google', github: 'github', huggingface: 'huggingface' };

const record = (v: unknown): Record<string, unknown> | null => (v && typeof v === 'object' ? { ...v } : null);
const str = (v: unknown): string | null => (typeof v === 'string' && v !== '' ? v : null);

async function getJson(path: string, init?: RequestInit): Promise<Record<string, unknown> | null> {
	const res = await fetch(`${BASE}/${path}`, { credentials: 'same-origin', ...init });
	if (!res.ok) throw new Error(`Auth.js ${path}: HTTP ${res.status}`);
	return record(await res.json());
}

/** POST an Auth.js action; with X-Auth-Return-Redirect the server answers `{ url }` instead of a 302. */
async function action(path: string, fields: Record<string, string>): Promise<URL> {
	const csrfToken = str((await getJson('csrf'))?.csrfToken);
	if (!csrfToken) throw new Error('Auth.js csrf: no token');
	const res = await getJson(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Auth-Return-Redirect': '1' },
		body: new URLSearchParams({ ...fields, csrfToken })
	});
	const url = str(res?.url);
	if (!url) throw new Error(`Auth.js ${path}: no redirect url`);
	return new URL(url, location.origin);
}

/** Runs a sign-in action; follows the returned URL unless it carries `?error=` (then maps `code`). */
async function signIn(path: string, fields: Record<string, string>, options?: SignInOptions): Promise<AuthResult> {
	try {
		const url = await action(path, { ...fields, callbackUrl: new URL(options?.redirectTo ?? location.pathname, location.origin).href });
		const error = url.searchParams.get('error');
		if (error) return { status: 'error', code: CODES[url.searchParams.get('code') ?? ''] ?? (error === 'CredentialsSignin' ? 'invalid' : 'failed'), message: error };
		location.assign(url);
		return { status: 'redirecting' };
	} catch (e) {
		return { status: 'error', code: 'failed', message: e instanceof Error ? e.message : String(e) };
	}
}

export const authjsClient: AuthClient = {
	backend: 'authjs',
	live: true,

	signInWith: (provider, options) => signIn(`signin/${provider}`, {}, options),
	signInWithPassword: (username, password, options) => signIn('callback/password', { username, password }, options),
	signUpWithPassword: (username, password, options) => signIn('callback/register', { username, password }, options),

	async getSession(): Promise<AuthSession | null> {
		let s: Record<string, unknown> | null;
		try {
			s = await getJson('session');
		} catch {
			return null;
		}
		const user = record(s?.user);
		const id = str(user?.id);
		if (!user || !id) return null;
		const expires = str(s?.expires);
		return {
			user: { id, email: str(user.email), name: str(user.name), method: OAUTH_METHODS[str(user.provider) ?? ''] ?? 'password' },
			expiresAt: expires ? Date.parse(expires) : null
		};
	},

	async signOut() {
		await action('signout', { callbackUrl: location.href });
	}
};
