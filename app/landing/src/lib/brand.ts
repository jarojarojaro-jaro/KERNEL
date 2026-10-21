/**
 * Central brand configuration.
 * Change it here and every page, meta tag, legal draft and the desktop prototype follows.
 */
export const BRAND = {
	name: 'Enigma LABZ',
	/** Used where diacritics are unsafe (file names, CLI binary, User-Agent). */
	ascii: 'enigma-labz',
	/** CLI binary name shown in terminal examples. */
	cli: 'enigma',
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
