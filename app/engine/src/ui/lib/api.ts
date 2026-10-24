/** Thin client for the local Enigma API (CONTRACT.md "API"). Errors carry the backend's `{error}` text. */
import type { AppState, Hw, LicenseInfo, Recommendation } from '../../shared/types';

export class ApiError extends Error {
	constructor(
		readonly status: number,
		message: string
	) {
		super(message);
	}
}

async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
	const init: RequestInit = { method, headers: { accept: 'application/json' } };
	if (body !== undefined) {
		init.headers = { accept: 'application/json', 'content-type': 'application/json' };
		init.body = JSON.stringify(body);
	}
	let res: Response;
	try {
		res = await fetch(path, init);
	} catch (e) {
		throw new ApiError(0, e instanceof Error ? e.message : String(e));
	}
	const text = await res.text();
	let data: unknown = null;
	if (text) {
		try {
			data = JSON.parse(text);
		} catch {
			data = null;
		}
	}
	if (!res.ok) {
		const msg = data && typeof data === 'object' && 'error' in data && typeof data.error === 'string' ? data.error : text || res.statusText;
		throw new ApiError(res.status, msg);
	}
	return data as T;
}

export const api = {
	state: () => call<AppState>('GET', '/api/state'),
	license: (key: string) => call<LicenseInfo>('POST', '/api/license', { key }),
	scan: () => call<Hw>('POST', '/api/scan'),
	recommend: (minCtx?: number) => call<Recommendation>('POST', '/api/recommend', minCtx === undefined ? {} : { minCtx }),
	start: (optionId: string) => call<unknown>('POST', '/api/start', { optionId }),
	cancel: () => call<unknown>('POST', '/api/cancel'),
	engineStart: () => call<unknown>('POST', '/api/engine/start'),
	engineStop: () => call<unknown>('POST', '/api/engine/stop')
};
