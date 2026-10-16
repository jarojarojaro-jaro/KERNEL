/**
 * Central brand configuration. The product name is an OPEN DECISION (PLAN §12 pt 7):
 * candidates from report 06 §3.1: Podkręt, Nocna Zmiana / NightShift, Turbina, Rozpęd, Tuned.
 * Change it here and every page, meta tag, legal draft and the desktop prototype follows.
 */
export const BRAND = {
	name: 'Podkręt',
	/** Used where diacritics are unsafe (file names, CLI binary, User-Agent). */
	ascii: 'podkret',
	/** CLI binary name shown in terminal examples. */
	cli: 'podkret',
	/** No domain is registered yet; pages that need an origin use the current one at runtime. */
	domain: null as string | null,
	/** Company data stays empty until the company exists (PLAN §7). Never fill with placeholders. */
	company: {
		legalName: null as string | null,
		address: null as string | null,
		krs: null as string | null,
		nip: null as string | null,
		regon: null as string | null,
		email: null as string | null
	},
	/** Local API default port of the desktop daemon (prototype value, see APP-ARCHITECTURE.md §2). */
	apiPort: 11500
} as const;

export const NAME_CANDIDATES = ['Podkręt', 'Nocna Zmiana / NightShift', 'Turbina', 'Rozpęd', 'Tuned'] as const;
