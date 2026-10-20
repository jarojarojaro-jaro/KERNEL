/**
 * `PUBLIC_AUTH_PROVIDER=authjs`: browser side of Auth.js (`@auth/sveltekit`) running on this app's
 * own server. It speaks the Auth.js REST endpoints directly (same calls as `@auth/sveltekit/client`),
 * so the static build needs no extra package; the server half (adapter-node, `src/auth.ts`, the
 * `handle` hook, the session callback) is set up as described in AUTH.md.
 *
 * Integration points:
 * - `BASE` is the Auth.js `basePath` (default `/auth`); OAuth callbacks land on `/auth/callback/<id>`.
 * - `EMAIL_PROVIDER` is the id of the Auth.js e-mail provider configured on the server
 *   (`nodemailer` for any SMTP relay; `resend`, `sendgrid`, … if one of those is used instead).
 * - `getSession` expects the server's `callbacks.session` to copy `user.id` and the sign-in
 *   `provider` onto the session (AUTH.md, Auth.js step 4); without it the id falls back to the
 *   e-mail and the method to `email`.
 */
import type { AuthClient, AuthSession, OAuthProvider, SignInOptions } from './types';

const BASE = '/auth';
const EMAIL_PROVIDER = 'nodemailer';

const record = (v: unknown): Record<string, unknown> | null => (v && typeof v === 'object' ? (v as Record<string, unknown>) : null);
const str = (v: unknown): string | null => (typeof v === 'string' ? v : null);

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

/** Runs a sign-in action and maps `?error=` on the returned url and thrown failures to AuthResult. */
async function signIn(path: string, fields: Record<string, string>, options: SignInOptions | undefined, redirect: boolean) {
	try {
		const url = await action(path, { ...fields, callbackUrl: new URL(options?.redirectTo ?? location.pathname, location.origin).href });
		const error = url.searchParams.get('error');
		if (error) return { status: 'error', message: error } as const;
		if (!redirect) return { status: 'email-sent' } as const;
		location.assign(url);
		return { status: 'redirecting' } as const;
	} catch (e) {
		return { status: 'error', message: e instanceof Error ? e.message : String(e) } as const;
	}
}

export const authjsClient: AuthClient = {
	backend: 'authjs',
	live: true,

	signInWith: (provider: OAuthProvider, options?: SignInOptions) => signIn(`signin/${provider}`, {}, options, true),

	// The server mails the link and answers with its verify-request page, which we do not open.
	signInWithEmail: (email: string, options?: SignInOptions) => signIn(`signin/${EMAIL_PROVIDER}`, { email }, options, false),

	async getSession(): Promise<AuthSession | null> {
		let s: Record<string, unknown> | null;
		try {
			s = await getJson('session');
		} catch {
			return null;
		}
		const user = record(s?.user);
		if (!user) return null;
		const email = str(user.email);
		const provider = str(user.provider);
		const expires = str(s?.expires);
		return {
			user: { id: str(user.id) ?? email ?? '', email, method: provider === 'google' || provider === 'github' ? provider : 'email' },
			expiresAt: expires ? Date.parse(expires) : null
		};
	},

	async signOut() {
		await action('signout', { callbackUrl: location.href });
	}
};
