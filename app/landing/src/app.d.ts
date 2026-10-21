declare global {
	namespace App {}
	/** vite.config.ts `define`: true for the public (online) build. */
	const __SITE_PUBLIC__: boolean;
	/** vite.config.ts `define`: PUBLIC_SITE_ORIGIN without a trailing slash, '' when unset (LAN preview). */
	const __SITE_ORIGIN__: string;
}
export {};
