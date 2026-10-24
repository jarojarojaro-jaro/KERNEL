/**
 * UI copy, Polish first, English written idiomatically (design/DESIGN.md §9). Numbers go through
 * `num()` so Polish gets a decimal comma and English a dot.
 */
import type { Phase } from '../../shared/types';

export type Lang = 'pl' | 'en';

export type Step = Exclude<Phase, 'error'>;
export const STEPS: readonly Step[] = ['license', 'scan', 'recommend', 'download', 'baseline', 'optimize', 'ready'];

const pl = {
	skip: 'Przejdź do treści',
	brandSub: 'silnik lokalny',
	langLabel: 'Język',
	themeToLight: 'Włącz jasny motyw',
	themeToDark: 'Włącz ciemny motyw',
	stepsLabel: 'Etapy',
	steps: {
		license: 'Subskrypcja',
		scan: 'Twój sprzęt',
		recommend: 'Rekomendacja',
		download: 'Pobieranie',
		baseline: 'Benchmark startowy',
		optimize: 'Optymalizacja',
		ready: 'Gotowe'
	} satisfies Record<Step, string>,
	stepDone: 'ukończony',
	stepCurrent: 'bieżący',
	backToCurrent: 'Wróć do bieżącego etapu',
	viewingPast: 'Podgląd ukończonego etapu.',
	connecting: 'Łączę z silnikiem Enigma…',
	offline: 'Brak połączenia z silnikiem Enigma. Ponawiam co kilka sekund.',
	offlineTitle: 'Silnik Enigma nie odpowiada',
	offlineBody: 'Interfejs działa, ale proces enigma na tym komputerze nie odpowiada. Uruchom go ponownie i odśwież stronę.',
	retryNow: 'Połącz teraz',
	cancel: 'Przerwij',
	cancelling: 'Przerywam…',
	working: 'Pracuję…',
	gb: 'GB',
	tps: 't/s',
	tokens: 'tokenów',
	seconds: 's',

	license: {
		overline: '01 · Subskrypcja',
		title: 'Podłącz',
		titleAccent: 'subskrypcję.',
		lead: 'Wklej klucz licencji z konta Enigma LABZ. Sprawdzamy go na tym komputerze, bez wysyłania gdziekolwiek.',
		activeTitle: 'Subskrypcja',
		activeAccent: 'aktywna.',
		activeLead: 'Klucz jest zapisany na tym komputerze. Pobieranie i optymalizacja są odblokowane.',
		label: 'Klucz licencji',
		hint: 'Zaczyna się od ENIGMA-. Znajdziesz go na koncie w enigmalabz.com.',
		placeholder: 'ENIGMA-…',
		submit: 'Sprawdź klucz',
		checking: 'Sprawdzam…',
		empty: 'Wklej klucz.',
		badPrefix: 'Klucz zaczyna się od ENIGMA-.',
		valid: 'Klucz ważny',
		invalid: 'Klucz nieważny',
		reasons: {
			format: 'To nie wygląda na klucz Enigmy. Skopiuj go w całości, razem z ENIGMA-.',
			signature: 'Podpis klucza się nie zgadza. Skopiuj klucz ponownie z konta.',
			expired: 'Subskrypcja wygasła. Odnów ją na koncie i wklej nowy klucz.',
			features: 'Ten plan nie obejmuje pobierania modeli i optymalizacji.'
		} as Record<string, string>,
		plan: 'Plan',
		expires: 'Ważny do',
		account: 'Konto',
		daysLeft: (n: number) => `${n} ${plural(n, ['dzień', 'dni', 'dni'], 'pl')} do końca`,
		plans: { pro: 'Pro', team: 'Team', trial: 'Wersja próbna' } as Record<string, string>,
		buy: 'Kup subskrypcję',
		buyHref: 'https://enigmalabz.com/pl/',
		noKey: 'Nie masz klucza?',
		scanFirst: 'Najpierw sprawdź sprzęt',
		scanFirstHint: 'Skan i rekomendacja działają bez klucza. Pobieranie i optymalizacja wymagają subskrypcji.',
		change: 'Zmień klucz',
		next: 'Dalej'
	},

	welcome: {
		eyebrow: 'Enigma LABZ · silnik lokalny',
		title: 'Gotowy, żeby przyspieszyć?',
		accent: 'Twój sprzęt. Szybciej.',
		lead: 'Skanujemy komputer, dobieramy najlepszy model z największym kontekstem (co najmniej 131 tys. tokenów), pobieramy go, mierzymy i podkręcamy. Ten sam sprzęt, ten sam model. Po prostu szybciej.',
		go: 'Zaczynamy',
		keyLabel: 'Masz klucz? Wklej go',
		keyPlaceholder: 'ENIGMA-…',
		keyCheck: 'Sprawdź',
		keyHint: 'Sprawdzamy go od razu po wklejeniu, na tym komputerze.',
		validUntil: 'ważny do',
		buy: 'Nie masz klucza? Kup na enigmalabz.com',
		noKeyNote: 'Skan i dobór modelu działają bez klucza.',
		changeKey: 'Zmień klucz',
		stepsTitle: 'Co się wydarzy',
		steps: [
			{ t: 'Skan sprzętu', d: 'Karta, pamięć, procesor, dysk. Lokalnie, bez wysyłania.' },
			{ t: 'Model i kontekst', d: 'Najlepszy model, który się mieści, z kontekstem od 131 tys. tokenów.' },
			{ t: 'Benchmark', d: 'Pomiar na oficjalnym llama.cpp: czytanie, pisanie, długi kontekst.' },
			{ t: 'Optymalizacja', d: 'Szukamy szybszej konfiguracji i zostawiamy tylko to, co zmierzone.' }
		],
		duel: {
			title: 'Zmierzone w naszym labie',
			typical: 'Typowa aplikacja',
			typicalSub: 'oficjalny llama.cpp, ustawienia domyślne',
			ours: 'Enigma',
			oursSub: 'nasz silnik + spekulacja MTP',
			faster: 'szybciej',
			measured: 'Zmierzone',
			note: 'Radeon RX 7900 XTX · Qwen3.8-27B UD-Q4_K_XL · pisanie, ten sam skrypt (spec_sweep: 6 promptów × 3 seedy, mediana) · 19.10.2026',
			sr: (a: string, b: string, x: string) => `Typowa aplikacja: ${a} tokenów na sekundę. Enigma: ${b} tokenów na sekundę, ${x} szybciej.`
		}
	},

	hi: {
		decode: 'Pisanie',
		faster: 'szybciej niż na starcie',
		same: 'tyle samo co na starcie',
		slower: 'wolniej niż na starcie'
	},

	hw: {
		overline: '02 · Twój sprzęt',
		title: 'Najpierw czytamy',
		titleAccent: 'Twój sprzęt.',
		lead: 'Lokalnie, bez uprawnień administratora i bez wysyłania czegokolwiek. Z tego dobieramy model.',
		scanning: 'Czytam kartę graficzną, procesor, pamięć i dysk…',
		gpu: 'Karta',
		vram: 'Pamięć karty',
		unified: 'pamięć wspólna z procesorem',
		arch: 'Architektura',
		driver: 'Sterownik',
		backends: 'Napędy',
		cpu: 'Procesor',
		cores: (c: number, t: number) => `${c} rdzeni · ${t} wątków`,
		ram: 'RAM',
		disk: 'Wolne miejsce',
		system: 'System',
		noGpu: 'Nie wykryto karty graficznej. Model pobiegnie na procesorze; będzie wolniej.',
		rescan: 'Skanuj ponownie',
		scannedAt: 'Skan',
		next: 'Pokaż rekomendację',
		gpuN: (i: number) => `Karta ${i}`
	},

	rec: {
		overline: '03 · Rekomendacja',
		title: 'Największy kontekst, który',
		titleAccent: 'naprawdę się mieści.',
		thinking: 'Dobieram model do Twojej pamięci…',
		pick: 'Nasz wybór',
		ctx: 'kontekst w tokenach',
		ctxMin: (min: string) => `minimum ${min}`,
		ctxMax: (max: string) => `model obsługuje do ${max}`,
		mem: 'Pamięć karty',
		memRam: 'Pamięć RAM',
		memOf: (used: string, budget: string) => `${used} z ${budget} GB`,
		weights: 'Wagi modelu',
		kv: 'Pamięć kontekstu (KV)',
		compute: 'Bufory obliczeń',
		overhead: 'Zapas systemowy',
		free: 'Wolne',
		over: 'Brakuje',
		why: 'Dlaczego ten',
		spec: 'Konfiguracja',
		file: 'Plik',
		size: 'Rozmiar',
		kvType: 'Kompresja KV',
		ub: 'Paczka prefill (ub)',
		backend: 'Napęd',
		quant: 'Kwantyzacja',
		featuresLabel: 'Cechy modelu',
		features: {
			mtp: 'MTP: zgaduje kilka tokenów naprzód',
			tools: 'Narzędzia',
			reasoning: 'Rozumowanie',
			vision: 'Obrazy'
		} as Record<string, string>,
		alternatives: 'Inne modele, które się mieszczą',
		choose: 'Wybierz model',
		chosen: 'Wybrany',
		score: 'Ocena',
		rejected: (n: number) => `Odrzucone (${n})`,
		rejectedHint: 'Te warianty nie spełniły warunków na tym sprzęcie.',
		none: 'Żaden model z katalogu nie mieści kontekstu ',
		noneTail: ' tokenów na tym sprzęcie.',
		start: 'Pobierz i zoptymalizuj',
		starting: 'Uruchamiam…',
		needLicense: 'Pobieranie i optymalizacja wymagają aktywnej subskrypcji.',
		goLicense: 'Podłącz subskrypcję',
		recompute: 'Przelicz ponownie'
	},

	dl: {
		overline: '04 · Pobieranie',
		title: 'Pobieram',
		titleAccent: 'silnik i model.',
		lead: 'Pliki trafiają do katalogu Enigmy na tym komputerze. Przerwane pobieranie wznowi się od miejsca, w którym stanęło.',
		engine: 'Silnik',
		model: 'Model',
		verify: 'Suma kontrolna SHA-256',
		extract: 'Rozpakowanie silnika',
		reused: 'Znaleziono na dysku — pomijam pobieranie',
		waiting: 'Czeka',
		done: 'Gotowe',
		verifying: 'Sprawdzam',
		eta: 'zostało',
		speed: 'prędkość'
	},

	base: {
		overline: '05 · Benchmark startowy',
		title: 'Punkt wyjścia:',
		titleAccent: 'oficjalny llama.cpp.',
		lead: 'Ten sam model na oficjalnym wydaniu llama.cpp, z ustawieniami dobranymi tylko pod mieszczenie się w pamięci. To jest „przed”.',
		running: 'Mierzę',
		phases: {
			'bench:start': 'Start serwera z pełnym kontekstem',
			'bench:prefill': 'Czytanie: długi prompt naraz (prefill)',
			'bench:decode': 'Pisanie: odpowiedź token po tokenie (decode)',
			'bench:deep': 'Długi kontekst: to samo przy zapełnionej pamięci'
		} as Record<string, string>,
		engine: 'Silnik',
		official: 'llama.cpp (oficjalny)',
		prefill: 'Czytanie (prefill)',
		decode: 'Pisanie (decode)',
		ttft: 'Pierwszy token',
		ctx: 'Kontekst',
		ctxOk: 'zweryfikowany: serwer wstał z pełnym kontekstem',
		ctxBad: 'nie zmieścił się',
		deep: (k: string) => `Przy ${k} tokenów w kontekście`,
		deepPrefill: 'czytanie',
		deepDecode: 'pisanie',
		measured: 'Zmierzone na tym komputerze'
	},

	opt: {
		overline: '06 · Optymalizacja',
		title: 'Szukam szybszej konfiguracji.',
		titleAccent: 'Każdą mierzę.',
		lead: 'Każdy kandydat przechodzi ten sam benchmark co punkt wyjścia. Zostaje najszybsze pisanie: czytanie może spaść najwyżej o 5% (o 15%, gdy pisanie przyspiesza o 20%+), a zmiana tekstu odpowiedzi musi dać co najmniej +3%.',
		headline: 'Wynik',
		metric: 'Pomiar',
		baseline: 'Punkt wyjścia',
		now: 'Teraz',
		gain: 'Przyrost',
		prefill: 'Czytanie (prefill)',
		decode: 'Pisanie (decode)',
		deep: (k: string) => `Pisanie przy ${k}`,
		ctx: 'Kontekst',
		noChange: 'bez zmian',
		prefillShort: 'Czytanie',
		decodeShort: 'Pisanie',
		candidates: 'Kandydaci',
		status: {
			pending: 'w kolejce',
			running: 'mierzę',
			kept: 'zostaje',
			rejected: 'odrzucony',
			failed: 'błąd'
		},
		measured: 'zmierzony, czeka na porównanie',
		same: 'ta sama odpowiedź',
		diff: 'inna odpowiedź',
		diffHint: 'Spekulacja może zmienić pojedyncze bity wyniku. Pokazujemy to otwarcie.',
		empty: 'Kandydaci pojawią się po benchmarku startowym.'
	},

	ready: {
		overline: '07 · Gotowe',
		title: 'Gotowe.',
		titleAccent: 'Model działa lokalnie.',
		titleGain: 'Gotowe. Twój model pisze',
		titleGainAccent: (p: string) => `szybciej o ${p}.`,
		lead: 'Endpoint jest zgodny z API OpenAI. Każdy program, który umie rozmawiać z OpenAI, umie rozmawiać z Enigmą.',
		endpoint: 'Endpoint',
		model: 'Model',
		ctx: 'Kontekst',
		running: 'Serwer modelu działa',
		stopped: 'Serwer modelu zatrzymany',
		start: 'Uruchom model',
		stop: 'Zatrzymaj model',
		snippets: 'Podłącz swoje narzędzia',
		snippetsLabel: 'Przykłady połączenia',
		copy: 'Kopiuj',
		copied: 'Skopiowano',
		copyFailed: 'Nie udało się skopiować',
		chat: 'Sprawdź na żywo',
		chatLabel: 'Wiadomość',
		chatPlaceholder: 'Napisz coś i wyślij…',
		send: 'Wyślij',
		stopGen: 'Zatrzymaj',
		you: 'Ty',
		assistant: 'Model',
		chatOff: 'Uruchom model, żeby porozmawiać.',
		chatSample: 'Opisz w trzech zdaniach, czym jest kwantyzacja modelu językowego.',
		reasoning: 'Rozumowanie modelu',
		gains: 'Zysk z optymalizacji'
	},

	err: {
		title: 'Coś poszło nie tak',
		cancelledTitle: 'Przerwano.',
		cancelledBody: 'Zatrzymałeś ten etap. Pobrane pliki i zmierzone wyniki zostają; „Wznów” zaczyna od miejsca, w którym stanęło.',
		resume: 'Wznów',
		inPhase: 'Etap',
		retry: 'Spróbuj ponownie',
		retrying: 'Ponawiam…',
		showLog: 'Pokaż dziennik',
		backToRec: 'Wróć do rekomendacji'
	},

	log: {
		title: 'Dziennik',
		open: 'Pokaż dziennik',
		close: 'Ukryj dziennik',
		empty: 'Brak wpisów.',
		levels: { debug: 'DEBUG', info: 'INFO', warn: 'UWAGA', error: 'BŁĄD' } as Record<string, string>
	}
};

export type Dict = typeof pl;

const en: Dict = {
	skip: 'Skip to content',
	brandSub: 'local engine',
	langLabel: 'Language',
	themeToLight: 'Switch to light theme',
	themeToDark: 'Switch to dark theme',
	stepsLabel: 'Steps',
	steps: {
		license: 'Subscription',
		scan: 'Your hardware',
		recommend: 'Recommendation',
		download: 'Download',
		baseline: 'Starting benchmark',
		optimize: 'Optimisation',
		ready: 'Ready'
	},
	stepDone: 'done',
	stepCurrent: 'current',
	backToCurrent: 'Back to the current step',
	viewingPast: 'Viewing a finished step.',
	connecting: 'Connecting to the Enigma engine…',
	offline: 'Lost the connection to the Enigma engine. Retrying every few seconds.',
	offlineTitle: 'The Enigma engine is not responding',
	offlineBody: 'The interface is up, but the enigma process on this computer is not answering. Start it again and reload this page.',
	retryNow: 'Connect now',
	cancel: 'Stop',
	cancelling: 'Stopping…',
	working: 'Working…',
	gb: 'GB',
	tps: 't/s',
	tokens: 'tokens',
	seconds: 's',

	license: {
		overline: '01 · Subscription',
		title: 'Connect your',
		titleAccent: 'subscription.',
		lead: 'Paste the licence key from your Enigma LABZ account. We check it on this computer and send it nowhere.',
		activeTitle: 'Subscription',
		activeAccent: 'active.',
		activeLead: 'The key is saved on this computer. Downloads and optimisation are unlocked.',
		label: 'Licence key',
		hint: 'It starts with ENIGMA-. You will find it in your account at enigmalabz.com.',
		placeholder: 'ENIGMA-…',
		submit: 'Check key',
		checking: 'Checking…',
		empty: 'Paste your key.',
		badPrefix: 'The key starts with ENIGMA-.',
		valid: 'Key is valid',
		invalid: 'Key is not valid',
		reasons: {
			format: 'This does not look like an Enigma key. Copy all of it, including ENIGMA-.',
			signature: 'The key signature does not match. Copy the key from your account again.',
			expired: 'The subscription has expired. Renew it in your account and paste the new key.',
			features: 'This plan does not include model downloads and optimisation.'
		},
		plan: 'Plan',
		expires: 'Valid until',
		account: 'Account',
		daysLeft: (n) => `${n} ${n === 1 ? 'day' : 'days'} left`,
		plans: { pro: 'Pro', team: 'Team', trial: 'Trial' },
		buy: 'Get a subscription',
		buyHref: 'https://enigmalabz.com/en/',
		noKey: 'No key yet?',
		scanFirst: 'Check my hardware first',
		scanFirstHint: 'Scanning and the recommendation work without a key. Downloading and optimisation need a subscription.',
		change: 'Change key',
		next: 'Next'
	},

	welcome: {
		eyebrow: 'Enigma LABZ · local engine',
		title: 'Ready to go faster?',
		accent: 'Your hardware. Faster.',
		lead: 'We scan your computer, pick the best model with the largest context (at least 131k tokens), download it, measure it and tune it. Same hardware, same model. Just faster.',
		go: 'Let’s go',
		keyLabel: 'Got a key? Paste it',
		keyPlaceholder: 'ENIGMA-…',
		keyCheck: 'Check',
		keyHint: 'We check it the moment you paste it, on this computer.',
		validUntil: 'valid until',
		buy: 'No key yet? Get one at enigmalabz.com',
		noKeyNote: 'Scanning and the model pick work without a key.',
		changeKey: 'Change key',
		stepsTitle: 'What happens next',
		steps: [
			{ t: 'Hardware scan', d: 'Graphics card, memory, processor, disk. Locally, nothing leaves.' },
			{ t: 'Model and context', d: 'The best model that fits, with at least 131k tokens of context.' },
			{ t: 'Benchmark', d: 'Measured on official llama.cpp: reading, writing, long context.' },
			{ t: 'Optimisation', d: 'We look for a faster setup and keep only what we measured.' }
		],
		duel: {
			title: 'Measured in our lab',
			typical: 'Typical app',
			typicalSub: 'official llama.cpp, default settings',
			ours: 'Enigma',
			oursSub: 'our engine + MTP speculation',
			faster: 'faster',
			measured: 'Measured',
			note: 'Radeon RX 7900 XTX · Qwen3.8-27B UD-Q4_K_XL · writing speed, same script (spec_sweep: 6 prompts × 3 seeds, median) · 2026-10-19',
			sr: (a, b, x) => `Typical app: ${a} tokens per second. Enigma: ${b} tokens per second, ${x} faster.`
		}
	},

	hi: {
		decode: 'Writing',
		faster: 'faster than at the start',
		same: 'the same as at the start',
		slower: 'slower than at the start'
	},

	hw: {
		overline: '02 · Your hardware',
		title: 'First we read',
		titleAccent: 'your hardware.',
		lead: 'Locally, without admin rights, and nothing leaves this computer. This is what we pick the model from.',
		scanning: 'Reading the graphics card, processor, memory and disk…',
		gpu: 'Card',
		vram: 'Card memory',
		unified: 'memory shared with the CPU',
		arch: 'Architecture',
		driver: 'Driver',
		backends: 'Backends',
		cpu: 'Processor',
		cores: (c, t) => `${c} cores · ${t} threads`,
		ram: 'RAM',
		disk: 'Free disk',
		system: 'System',
		noGpu: 'No graphics card found. The model will run on the processor, which is slower.',
		rescan: 'Scan again',
		scannedAt: 'Scanned',
		next: 'Show the recommendation',
		gpuN: (i) => `Card ${i}`
	},

	rec: {
		overline: '03 · Recommendation',
		title: 'The largest context that',
		titleAccent: 'actually fits.',
		thinking: 'Matching a model to your memory…',
		pick: 'Our pick',
		ctx: 'tokens of context',
		ctxMin: (min) => `minimum ${min}`,
		ctxMax: (max) => `the model supports up to ${max}`,
		mem: 'Card memory',
		memRam: 'System memory',
		memOf: (used, budget) => `${used} of ${budget} GB`,
		weights: 'Model weights',
		kv: 'Context memory (KV)',
		compute: 'Compute buffers',
		overhead: 'System headroom',
		free: 'Free',
		over: 'Short by',
		why: 'Why this one',
		spec: 'Configuration',
		file: 'File',
		size: 'Size',
		kvType: 'KV compression',
		ub: 'Prefill batch (ub)',
		backend: 'Backend',
		quant: 'Quantisation',
		featuresLabel: 'Model features',
		features: {
			mtp: 'MTP: drafts a few tokens ahead',
			tools: 'Tools',
			reasoning: 'Reasoning',
			vision: 'Images'
		},
		alternatives: 'Other models that fit',
		choose: 'Choose a model',
		chosen: 'Selected',
		score: 'Score',
		rejected: (n) => `Rejected (${n})`,
		rejectedHint: 'These variants did not meet the requirements on this hardware.',
		none: 'No model in the catalogue fits a context of ',
		noneTail: ' tokens on this hardware.',
		start: 'Download and optimise',
		starting: 'Starting…',
		needLicense: 'Downloading and optimisation need an active subscription.',
		goLicense: 'Connect a subscription',
		recompute: 'Recalculate'
	},

	dl: {
		overline: '04 · Download',
		title: 'Downloading',
		titleAccent: 'the engine and the model.',
		lead: 'Files go to the Enigma folder on this computer. An interrupted download resumes where it stopped.',
		engine: 'Engine',
		model: 'Model',
		verify: 'SHA-256 checksum',
		extract: 'Unpacking the engine',
		reused: 'Found on disk — skipping the download',
		waiting: 'Waiting',
		done: 'Done',
		verifying: 'Checking',
		eta: 'left',
		speed: 'speed'
	},

	base: {
		overline: '05 · Starting benchmark',
		title: 'The starting point:',
		titleAccent: 'official llama.cpp.',
		lead: 'The same model on the official llama.cpp release, with settings chosen only so that it fits in memory. This is the “before”.',
		running: 'Measuring',
		phases: {
			'bench:start': 'Starting the server with the full context',
			'bench:prefill': 'Reading: a long prompt in one go (prefill)',
			'bench:decode': 'Writing: the answer token by token (decode)',
			'bench:deep': 'Long context: the same with memory filled up'
		},
		engine: 'Engine',
		official: 'llama.cpp (official)',
		prefill: 'Reading (prefill)',
		decode: 'Writing (decode)',
		ttft: 'First token',
		ctx: 'Context',
		ctxOk: 'verified: the server started with the full context',
		ctxBad: 'did not fit',
		deep: (k) => `With ${k} tokens in context`,
		deepPrefill: 'reading',
		deepDecode: 'writing',
		measured: 'Measured on this computer'
	},

	opt: {
		overline: '06 · Optimisation',
		title: 'Looking for a faster setup.',
		titleAccent: 'Measuring every one.',
		lead: 'Every candidate runs the same benchmark as the starting point. The fastest writing speed wins: reading may drop by at most 5% (15% when writing gets 20%+ faster), and changing the answer text must gain at least 3%.',
		headline: 'Result',
		metric: 'Metric',
		baseline: 'Starting point',
		now: 'Now',
		gain: 'Gain',
		prefill: 'Reading (prefill)',
		decode: 'Writing (decode)',
		deep: (k) => `Writing at ${k}`,
		ctx: 'Context',
		noChange: 'no change',
		prefillShort: 'Reading',
		decodeShort: 'Writing',
		candidates: 'Candidates',
		status: {
			pending: 'queued',
			running: 'measuring',
			kept: 'kept',
			rejected: 'rejected',
			failed: 'failed'
		},
		measured: 'measured, awaiting comparison',
		same: 'same output',
		diff: 'different output',
		diffHint: 'Speculation can flip individual bits of the output. We show it openly.',
		empty: 'Candidates appear after the starting benchmark.'
	},

	ready: {
		overline: '07 · Ready',
		title: 'Ready.',
		titleAccent: 'The model runs locally.',
		titleGain: 'Ready. Your model now writes',
		titleGainAccent: (p) => `${p} faster.`,
		lead: 'The endpoint speaks the OpenAI API. Anything that can talk to OpenAI can talk to Enigma.',
		endpoint: 'Endpoint',
		model: 'Model',
		ctx: 'Context',
		running: 'Model server is running',
		stopped: 'Model server is stopped',
		start: 'Start the model',
		stop: 'Stop the model',
		snippets: 'Connect your tools',
		snippetsLabel: 'Connection examples',
		copy: 'Copy',
		copied: 'Copied',
		copyFailed: 'Could not copy',
		chat: 'Try it live',
		chatLabel: 'Message',
		chatPlaceholder: 'Type something and send…',
		send: 'Send',
		stopGen: 'Stop',
		you: 'You',
		assistant: 'Model',
		chatOff: 'Start the model to chat.',
		chatSample: 'Explain in three sentences what quantising a language model means.',
		reasoning: 'Model reasoning',
		gains: 'Gain from optimisation'
	},

	err: {
		title: 'Something went wrong',
		cancelledTitle: 'Stopped.',
		cancelledBody: 'You stopped this step. Downloaded files and measured results stay; “Resume” picks up where it stopped.',
		resume: 'Resume',
		inPhase: 'Step',
		retry: 'Try again',
		retrying: 'Retrying…',
		showLog: 'Show the log',
		backToRec: 'Back to the recommendation'
	},

	log: {
		title: 'Log',
		open: 'Show the log',
		close: 'Hide the log',
		empty: 'No entries yet.',
		levels: { debug: 'DEBUG', info: 'INFO', warn: 'WARN', error: 'ERROR' }
	}
};

export const DICT: Record<Lang, Dict> = { pl, en };

const LOCALE: Record<Lang, string> = { pl: 'pl-PL', en: 'en-GB' };

/** Locale number: "109,0" in Polish, "109.0" in English; thousands grouped ("131 072" / "131,072"). */
export function num(v: number, lang: Lang, digits = 1): string {
	return new Intl.NumberFormat(LOCALE[lang], { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v);
}

/** Integer with grouping that always groups (Polish CLDR skips 4-digit groups; we want "4 096" too). */
export function int(v: number, lang: Lang): string {
	const s = Math.round(v).toString();
	const sep = lang === 'pl' ? '\u202f' : ',';
	return s.replace(/\B(?=(\d{3})+(?!\d))/g, sep);
}

/** Context sizes read better as "131k" in tight spots. */
export function kTokens(v: number): string {
	return `${Math.round(v / 1024)}k`;
}

/** Signed percentage: "+12,4 %" / "+12.4%". */
export function pct(v: number, lang: Lang): string {
	const s = `${v > 0 ? '+' : v < 0 ? '−' : '±'}${num(Math.abs(v), lang, 1)}`;
	return lang === 'pl' ? `${s}\u00a0%` : `${s}%`;
}

export function date(unixS: number, lang: Lang): string {
	return new Intl.DateTimeFormat(LOCALE[lang], { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(unixS * 1000));
}

/** Clock time from a Unix timestamp in seconds or milliseconds (values below 1e12 are seconds). */
export function time(ts: number, lang: Lang): string {
	return new Intl.DateTimeFormat(LOCALE[lang], { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(ts < 1e12 ? ts * 1000 : ts));
}

/** Seconds as "1 min 20 s" / "45 s". */
export function duration(s: number): string {
	const t = Math.max(0, Math.round(s));
	const h = Math.floor(t / 3600);
	const m = Math.floor((t % 3600) / 60);
	const r = t % 60;
	const parts: string[] = [];
	if (h) parts.push(`${h}\u00a0h`);
	if (m) parts.push(`${m}\u00a0min`);
	if (!h && (r || !m)) parts.push(`${r}\u00a0s`);
	return parts.join(' ');
}

/** Polish plural categories (CLDR one / few / many); English callers pass their own forms. */
export function plural(n: number, forms: [string, string, string], lang: Lang): string {
	if (lang === 'en') return n === 1 ? forms[0] : forms[2];
	if (n === 1) return forms[0];
	const d = n % 10;
	const h = n % 100;
	return d >= 2 && d <= 4 && !(h >= 12 && h <= 14) ? forms[1] : forms[2];
}

/** Bytes → GB with one decimal ("17,6"). Vendors label VRAM in GB meaning GiB; we do the same. */
export function gb(bytes: number, lang: Lang): string {
	return num(bytes / 1024 ** 3, lang, 1);
}
