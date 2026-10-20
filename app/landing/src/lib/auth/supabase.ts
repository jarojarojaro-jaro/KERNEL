/**
 * `PUBLIC_AUTH_PROVIDER=supabase`: Supabase Auth (GoTrue) over its REST API, implicit flow, no SDK.
 * Works with the static build: Supabase hosts the OAuth callback
 * (`https://<project>.supabase.co/auth/v1/callback`) and sends the browser back to `redirectTo` with
 * the tokens in the URL fragment, which `getSession` reads once and moves to localStorage.
 *
 * Integration points:
 * - `PUBLIC_SUPABASE_URL` / `PUBLIC_SUPABASE_ANON_KEY` (public by design; row-level security guards
 *   the data, AUTH.md). Both are empty in the committed `.env`.
 * - Every `redirectTo` must be listed under Authentication → URL Configuration → Redirect URLs.
 * - Session storage key `STORE` must be added to the Cookie Policy table before going live.
 * - To move to PKCE or server-side sessions, swap this file for `@supabase/ssr`; the AuthClient
 *   contract stays the same.
 */
import { PUBLIC_SUPABASE_ANON_KEY, PUBLIC_SUPABASE_URL } from '$env/static/public';
import type { AuthClient, AuthSession, OAuthProvider, SignInOptions } from './types';

const API = `${PUBLIC_SUPABASE_URL.replace(/\/$/, '')}/auth/v1`;
const STORE = 'auth.supabase';
const KEY_HEADERS = { apikey: PUBLIC_SUPABASE_ANON_KEY, Authorization: `Bearer ${PUBLIC_SUPABASE_ANON_KEY}` };

interface Tokens {
	access_token: string;
	refresh_token: string;
	/** seconds since epoch */
	expires_at: number;
}

const str = (v: unknown): string | null => (typeof v === 'string' && v !== '' ? v : null);

/** Token set from a GoTrue response, the redirect fragment or storage (`expires_in` when `expires_at` is absent). */
function toTokens(src: unknown): Tokens | null {
	if (!src || typeof src !== 'object') return null;
	const o: Record<string, unknown> = { ...src };
	const access_token = str(o.access_token);
	const refresh_token = str(o.refresh_token);
	if (!access_token || !refresh_token) return null;
	const at = Number(o.expires_at);
	return { access_token, refresh_token, expires_at: Number.isFinite(at) && at > 0 ? at : Math.floor(Date.now() / 1000) + Number(o.expires_in ?? 3600) };
}

function save(t: Tokens | null) {
	try {
		if (t) localStorage.setItem(STORE, JSON.stringify(t));
		else localStorage.removeItem(STORE);
	} catch {
		/* storage blocked: the session lives for this page view only */
	}
}

function load(): Tokens | null {
	try {
		return toTokens(JSON.parse(localStorage.getItem(STORE) ?? 'null'));
	} catch {
		return null;
	}
}

/** Tokens handed back in the fragment after an OAuth or magic-link round trip; the hash is cleared. */
function fromFragment(): Tokens | null {
	if (!location.hash.includes('access_token=')) return null;
	const t = toTokens(Object.fromEntries(new URLSearchParams(location.hash.slice(1))));
	history.replaceState(history.state, '', location.pathname + location.search);
	return t;
}

async function api(path: string, init: RequestInit & { token?: string } = {}): Promise<unknown> {
	const res = await fetch(`${API}/${path}`, {
		...init,
		headers: { ...KEY_HEADERS, 'Content-Type': 'application/json', ...(init.token ? { Authorization: `Bearer ${init.token}` } : {}) }
	});
	if (!res.ok) {
		const body: unknown = await res.json().catch(() => null);
		const msg = body && typeof body === 'object' && 'msg' in body ? str(body.msg) : null;
		throw new Error(msg ?? `Supabase ${path}: HTTP ${res.status}`);
	}
	return res.status === 204 ? null : res.json();
}

export const supabaseClient: AuthClient = {
	backend: 'supabase',
	live: true,

	async signInWith(provider: OAuthProvider, options?: SignInOptions) {
		const q = new URLSearchParams({ provider, redirect_to: new URL(options?.redirectTo ?? location.pathname, location.origin).href });
		location.assign(`${API}/authorize?${q}`);
		return { status: 'redirecting' };
	},

	async signInWithEmail(email: string, options?: SignInOptions) {
		try {
			const q = new URLSearchParams({ redirect_to: new URL(options?.redirectTo ?? location.pathname, location.origin).href });
			await api(`otp?${q}`, { method: 'POST', body: JSON.stringify({ email, create_user: true }) });
			return { status: 'email-sent' };
		} catch (e) {
			return { status: 'error', message: e instanceof Error ? e.message : String(e) };
		}
	},

	async getSession(): Promise<AuthSession | null> {
		let t = fromFragment() ?? load();
		if (!t) return null;
		try {
			if (t.expires_at - 30 < Date.now() / 1000) {
				t = toTokens(await api('token?grant_type=refresh_token', { method: 'POST', body: JSON.stringify({ refresh_token: t.refresh_token }) }));
				if (!t) throw new Error('Supabase refresh: no tokens');
			}
			save(t);
			const user = await api('user', { token: t.access_token });
			if (!user || typeof user !== 'object' || !('id' in user)) return null;
			const meta = 'app_metadata' in user && user.app_metadata && typeof user.app_metadata === 'object' && 'provider' in user.app_metadata ? user.app_metadata.provider : null;
			return {
				user: { id: String(user.id), email: 'email' in user ? str(user.email) : null, method: meta === 'google' || meta === 'github' ? meta : 'email' },
				expiresAt: t.expires_at * 1000
			};
		} catch {
			save(null);
			return null;
		}
	},

	async signOut() {
		const t = load();
		save(null);
		if (t) await api('logout', { method: 'POST', token: t.access_token }).catch(() => null);
	}
};
