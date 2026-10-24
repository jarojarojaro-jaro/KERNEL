/**
 * The one reactive store: the backend's AppState (GET /api/state, then SSE `state`), the log lines and
 * the latest progress per label (SSE `progress`), plus the user's language and theme.
 */
import type { AppState, Phase, Progress } from '../../shared/types';
import { api } from './api';
import { DICT, type Lang } from './i18n';

export interface LogLine {
	t: number;
	level: string;
	msg: string;
}

/** Progress events keyed by `${phase}:${label}` so the download screen can show engine, model and checksum side by side. */
export type ProgressMap = Record<string, Progress>;

const MAX_LOG = 800;

class Store {
	state = $state<AppState | null>(null);
	/** null until the first answer; false while the backend is unreachable. */
	online = $state<boolean | null>(null);
	logs = $state<LogLine[]>([]);
	progress = $state<ProgressMap>({});
	lang = $state<Lang>(document.documentElement.getAttribute('lang') === 'en' ? 'en' : 'pl');
	theme = $state<'dark' | 'light'>(document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark');
	logOpen = $state(false);

	t = $derived(DICT[this.lang]);

	#es: EventSource | null = null;
	#retry: number | undefined;

	setLang(l: Lang) {
		this.lang = l;
		document.documentElement.setAttribute('lang', l);
		try {
			localStorage.setItem('enigma.lang', l);
		} catch {
			/* storage blocked: the choice lasts for this session */
		}
	}

	setTheme(th: 'dark' | 'light') {
		this.theme = th;
		document.documentElement.setAttribute('data-theme', th);
		document.querySelector('meta[name="theme-color"]')?.setAttribute('content', th === 'light' ? '#F4F2EE' : '#050506');
		try {
			localStorage.setItem('enigma.theme', th);
		} catch {
			/* storage blocked */
		}
	}

	/** Progress for one label in one phase (or null). */
	prog(phase: Phase, label: string): Progress | null {
		return this.progress[`${phase}:${label}`] ?? null;
	}

	#applyState(s: AppState) {
		this.state = s;
		if (s.progress) this.progress[`${s.progress.phase}:${s.progress.label}`] = s.progress;
	}

	async refresh() {
		try {
			this.#applyState(await api.state());
			this.online = true;
		} catch {
			this.online = false;
		}
	}

	connect() {
		clearTimeout(this.#retry);
		this.#es?.close();
		const es = new EventSource('/api/events');
		this.#es = es;
		es.addEventListener('open', () => {
			this.online = true;
			void this.refresh();
		});
		es.addEventListener('state', (e) => {
			const s = parse<AppState>(e);
			if (s) this.#applyState(s);
		});
		es.addEventListener('progress', (e) => {
			const p = parse<Progress>(e);
			if (p && typeof p.label === 'string') this.progress[`${p.phase}:${p.label}`] = p;
		});
		es.addEventListener('log', (e) => {
			const l = parse<LogLine>(e);
			if (!l || typeof l.msg !== 'string') return;
			this.logs.push(l);
			if (this.logs.length > MAX_LOG) this.logs.splice(0, this.logs.length - MAX_LOG);
		});
		es.addEventListener('error', () => {
			// EventSource retries on its own while CONNECTING; once CLOSED we reconnect ourselves.
			this.online = false;
			if (es.readyState === EventSource.CLOSED) this.#retry = window.setTimeout(() => this.connect(), 3000);
		});
	}
}

function parse<T>(e: Event): T | null {
	if (!(e instanceof MessageEvent) || typeof e.data !== 'string') return null;
	try {
		return JSON.parse(e.data) as T;
	} catch {
		return null;
	}
}

export const store = new Store();
