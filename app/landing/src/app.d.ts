declare global {
	namespace App {}
	/** vite.config.ts `define`: true for the public (online) build. */
	const __SITE_PUBLIC__: boolean;
}
export {};
