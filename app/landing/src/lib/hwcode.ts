/**
 * Parser for the paste-code printed by app/scan/{scan.sh,scan-macos.sh,scan.ps1}.
 * Format: `HW1;os=…;gpu=…;sub=…;vendor=…;vram=…;ngpu=…;drv=…;ram=…;thr=…;isa=…;pcie=…;um=…;sum=XXXX`
 * Checksum over the text before `;sum=`: h = (h·31 + byte) mod 65521, 4 uppercase hex digits.
 * The code is plain text on purpose: the user can read every field before pasting it.
 */
export const HW_KEYS = ['os', 'gpu', 'sub', 'vendor', 'vram', 'ngpu', 'drv', 'ram', 'thr', 'isa', 'pcie', 'um'] as const;
export type HwKey = (typeof HW_KEYS)[number];
export type HwCode = Record<HwKey, string | null>;

export function hwChecksum(text: string): string {
	let h = 0;
	for (const b of new TextEncoder().encode(text)) h = (h * 31 + b) % 65521;
	return h.toString(16).toUpperCase().padStart(4, '0');
}

export type ParseResult = { ok: true; code: HwCode } | { ok: false; error: 'format' | 'checksum' };

export function parseHwCode(raw: string): ParseResult {
	const line = raw.trim().split(/\r?\n/).find((l) => l.trim().startsWith('HW1;'))?.trim();
	if (!line) return { ok: false, error: 'format' };
	const at = line.lastIndexOf(';sum=');
	if (at < 0) return { ok: false, error: 'format' };
	if (hwChecksum(line.slice(0, at)) !== line.slice(at + 5).toUpperCase()) return { ok: false, error: 'checksum' };
	const code = Object.fromEntries(HW_KEYS.map((k) => [k, null])) as HwCode;
	for (const part of line.slice(4, at).split(';')) {
		const eq = part.indexOf('=');
		const k = part.slice(0, eq) as HwKey;
		const v = part.slice(eq + 1).trim();
		if (eq > 0 && HW_KEYS.includes(k)) code[k] = v === '?' || v === '' ? null : v;
	}
	return { ok: true, code };
}
