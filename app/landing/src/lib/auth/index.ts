/**
 * Auth entry point. `PUBLIC_AUTH_PROVIDER` (build time, `.env`; default `none`) picks the backend:
 * - `none`: no accounts yet; every sign-in answers `unavailable` and the UI continues as a preview
 *   (none.ts).
 * - `authjs`: Auth.js on this app's server (Google, GitHub, Hugging Face OIDC, username + password),
 *   needs adapter-node (authjs.ts, AUTH.md).
 * Any other value fails the build, so a typo never ships a silently disabled login.
 */
import { PUBLIC_AUTH_PROVIDER } from '$env/static/public';
import { authjsClient } from './authjs';
import { noneClient } from './none';
import type { AuthBackend, AuthClient, AuthSession, OAuthProvider, SignInOptions } from './types';

export type { AuthBackend, AuthClient, AuthErrorCode, AuthResult, AuthSession, AuthUser, OAuthProvider, SignInMethod, SignInOptions } from './types';

const CLIENTS: Record<AuthBackend, AuthClient> = { none: noneClient, authjs: authjsClient };

const backend = PUBLIC_AUTH_PROVIDER || 'none';
if (backend !== 'none' && backend !== 'authjs') throw new Error(`PUBLIC_AUTH_PROVIDER must be none or authjs (got "${backend}")`);

/** The configured client; `auth.live` tells the UI whether sign-in really works. */
export const auth: AuthClient = CLIENTS[backend];

export const signInWith = (provider: OAuthProvider, options?: SignInOptions) => auth.signInWith(provider, options);
export const signInWithPassword = (username: string, password: string, options?: SignInOptions) => auth.signInWithPassword(username, password, options);
export const signUpWithPassword = (username: string, password: string, options?: SignInOptions) => auth.signUpWithPassword(username, password, options);
export const getSession = (): Promise<AuthSession | null> => auth.getSession();
export const signOut = () => auth.signOut();
