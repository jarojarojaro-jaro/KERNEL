/**
 * Provider-agnostic auth contract. The UI talks only to this interface (`$lib/auth`); the build-time
 * env `PUBLIC_AUTH_PROVIDER` picks the implementation. Setup of each backend: AUTH.md.
 */

/** Backend selected at build time (`PUBLIC_AUTH_PROVIDER`). */
export type AuthBackend = 'none' | 'authjs' | 'supabase';

/** Social sign-in providers shown on the account step. */
export type OAuthProvider = 'google' | 'github';

/** How the signed-in user authenticated. */
export type SignInMethod = OAuthProvider | 'email';

export interface AuthUser {
	/** Stable id from the backend (Auth.js user id / Supabase auth.users.id). */
	id: string;
	email: string | null;
	method: SignInMethod;
}

export interface AuthSession {
	user: AuthUser;
	/** Absolute expiry, ms since epoch; null when the backend does not report it. */
	expiresAt: number | null;
}

export interface SignInOptions {
	/** Absolute or same-origin path the provider returns to after a successful sign-in. */
	redirectTo?: string;
}

/**
 * Outcome of a sign-in call. `redirecting`: the browser is leaving for the provider (nothing else to
 * render). `email-sent`: a magic link is on its way. `unavailable`: no backend is configured
 * (`none`), the UI shows the waitlist path instead. `error`: the backend answered with a failure.
 */
export type AuthResult = { status: 'redirecting' } | { status: 'email-sent' } | { status: 'unavailable' } | { status: 'error'; message: string };

export interface AuthClient {
	readonly backend: AuthBackend;
	/** True when sign-in really works; false for `none` (buttons render disabled). */
	readonly live: boolean;
	signInWith(provider: OAuthProvider, options?: SignInOptions): Promise<AuthResult>;
	signInWithEmail(email: string, options?: SignInOptions): Promise<AuthResult>;
	getSession(): Promise<AuthSession | null>;
	signOut(): Promise<void>;
}
