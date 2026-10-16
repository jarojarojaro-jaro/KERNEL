/**
 * Consent record (ePrivacy art. 5(3) / PKE art. 399). Nothing optional loads before an explicit
 * "accept"; today the analytics category has no tool behind it, so `whenAllowed` callbacks never
 * run until one is integrated and listed in the cookie policy.
 */
import { browser } from '$app/environment';

const KEY = 'consent';
const VERSION = 1;

export interface ConsentRecord {
	v: number;
	analytics: boolean;
	at: string;
}

function load(): ConsentRecord | null {
	if (!browser) return null;
	try {
		const r = JSON.parse(localStorage.getItem(KEY) ?? 'null') as ConsentRecord | null;
		return r?.v === VERSION ? r : null;
	} catch {
		return null;
	}
}

export const consent = $state<{ record: ConsentRecord | null; open: boolean; ready: boolean }>({
	record: null,
	open: false,
	ready: false
});

const pending: (() => void)[] = [];

export function initConsent() {
	consent.record = load();
	consent.open = consent.record === null;
	consent.ready = true;
}

export function saveConsent(analytics: boolean) {
	consent.record = { v: VERSION, analytics, at: new Date().toISOString() };
	try {
		localStorage.setItem(KEY, JSON.stringify(consent.record));
	} catch {
		/* storage blocked: the choice still applies for this page view */
	}
	consent.open = false;
	if (analytics) pending.splice(0).forEach((fn) => fn());
}

/** Gate for any future optional script. Runs `fn` only after an explicit analytics consent. */
export function whenAllowed(fn: () => void) {
	if (consent.record?.analytics) fn();
	else pending.push(fn);
}
