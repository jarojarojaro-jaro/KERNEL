/**
 * Public (online) build: `PUBLIC_SITE_PUBLIC=1 bun run build`. Default off = LAN preview.
 * When on, the methodology pages are not built, every link to them is dropped and internal
 * source paths are stripped from the bundle (vite.config.ts).
 */
export const SITE_PUBLIC: boolean = __SITE_PUBLIC__;
