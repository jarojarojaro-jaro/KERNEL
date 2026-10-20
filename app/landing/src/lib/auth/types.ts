/**
 * Provider-agnostic auth contract. The UI talks only to this interface (`$lib/auth`); the build-time
 * env `PUBLIC_AUTH_PROVIDER` picks the implementation. Setup of the backend: AUTH.md.
 */

/** Backend selected at build time (`PUBLIC_AUTH_PROVIDER`). */
export type AuthBackend = 'none' | 'authjs';

/** Social sign-in providers shown on the account step. */
export type OAuthProvider = 'google' | 'github' | 'huggingface';

/** How the signed-in user authenticated: a provider, or username + password (no e-mail). */
export type SignInMethod = OAuthProvider | 'password';

export interface AuthUser {
	/** Stable id from the backend (Auth.js user id). */
	id: string;
	/** Present for Google / GitHub; Hugging Face only if the user made it public; never for passwords. */
	email: string | null;
	/** Username (password accounts) or the provider's display name / handle. */
	name: string | null;
	method: SignInMethod;
}

export interface AuthSession {
	user: AuthUser;
	/** Absolute expiry, ms since epoch; null when the backend does not report it. */
	expiresAt: number | null;
}

export interface SignInOptions {
	/** Absolute or same-origin path the browser returns to after a successful sign-in. */
	redirectTo?: string;
}

/**
 * Why a sign-in failed. `invalid`: wrong username or password. `taken`: the username already exists
 * (sign-up). `locked`: too many attempts, try later. `failed`: anything else (network, provider).
 */
export type AuthErrorCode = 'invalid' | 'taken' | 'locked' | 'failed';

/**
 * Outcome of a sign-in call. `redirecting`: the browser is leaving (provider page or the signed-in
 * destination); nothing else to render. `unavailable`: no backend is configured (`none`), the UI
 * continues as a preview. `error`: the backend refused or failed.
 */
export type AuthResult = { status: 'redirecting' } | { status: 'unavailable' } | { status: 'error'; code: AuthErrorCode; message: string };

export interface AuthClient {
	readonly backend: AuthBackend;
	/** True when sign-in really works; false for `none` (preview). */
	readonly live: boolean;
	signInWith(provider: OAuthProvider, options?: SignInOptions): Promise<AuthResult>;
	signInWithPassword(username: string, password: string, options?: SignInOptions): Promise<AuthResult>;
	signUpWithPassword(username: string, password: string, options?: SignInOptions): Promise<AuthResult>;
	getSession(): Promise<AuthSession | null>;
	signOut(): Promise<void>;
}
