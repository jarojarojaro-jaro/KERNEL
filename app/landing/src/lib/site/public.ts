/**
 * Public (online) build: `PUBLIC_SITE_PUBLIC=1 bun run build`. Default off = LAN preview.
 * When on, the methodology pages are not built, every link to them is dropped and internal
 * source paths are stripped from the bundle (vite.config.ts).
 */
export const SITE_PUBLIC: boolean = __SITE_PUBLIC__;

/**
 * Absolute origin for canonical, hreflang and og:url: `PUBLIC_SITE_ORIGIN=https://… bun run build`.
 * '' when unset (LAN preview): those links are relative and og:url is omitted.
 */
export const SITE_ORIGIN: string = __SITE_ORIGIN__;
