import { BRAND } from '$lib/brand';

const N = BRAND.name;

/**
 * Non-breaking spaces where a line must not break: after Polish one-letter words (a, i, o, u,
 * w, z) and between a number and its unit ("16 GB", "78,0 t/s"). Applied to all copy below and
 * to every filled-in string (`fill` in src/lib/home/data.ts).
 */
export const nb = (s: string) =>
	s
		.replace(/(^|[\s(„])([aiouwzAIOUWZ]) /g, '$1$2\u00a0')
		.replace(/(\d) (GB|MB|W|s|ms|t\/s|zł)(?=$|[\s.,;:)])/g, '$1\u00a0$2')
		// a separator dot never starts a line: glue it to the word before
		.replace(/ ·/g, '\u00a0·');

function deepNb<T>(v: T): T {
	if (typeof v === 'string') return nb(v) as T;
	if (Array.isArray(v)) return v.map(deepNb) as T;
	if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, deepNb(x)])) as T;
	return v;
}

/*
 * Home page copy. Numbers are NEVER typed here: `{name}` placeholders are filled by the
 * components with formatted values from src/lib/data/measurements.ts and src/lib/estimator.ts
 * (see `fill` in src/lib/home/data.ts). In headlines, `|` splits a condensed (wdth 75) lead from
 * a wide (wdth 125) payoff (src/lib/home/Duo.svelte).
 */
const raw = {
	pl: {
		meta: {
			title: `${N} — Ten sam sprzęt. Ten sam model. Po prostu szybciej.`,
			description: `${N} dobiera model AI do Twojej karty graficznej, mierzy go uczciwie i przyspiesza silnik. Lokalnie, bez wysyłania rozmów. Każda liczba ze źródłem.`
		},
		nav: {
			how: 'Jak to działa',
			results: 'Wyniki',
			cards: 'Twoja karta',
			quality: 'Jakość',
			faq: 'FAQ',
			methodology: 'Metodologia',
			start: 'Sprawdź swój sprzęt',
			menu: 'Menu',
			close: 'Zamknij menu',
			main: 'Główna nawigacja',
			skip: 'Przejdź do treści',
			lang: 'English',
			langLabel: 'Zmień język na angielski',
			themeToDark: 'Włącz ciemny motyw',
			themeToLight: 'Włącz jasny motyw'
		},
		hero: {
			title: ['Ten sam sprzęt. Ten sam model.', 'Po prostu szybciej.'],
			cta: 'Sprawdź swoją kartę',
			ctaSecondary: 'Jak mierzymy',
			answer: 'Ta przykładowa odpowiedź: {words} słów ≈ {tok} tokenów (po polsku {tpw} tokenu na słowo). W zmierzonym tempie nasz silnik pisze ją w ≈ {t2} s, typowa aplikacja w ≈ {t0} s; samo tempo zmierzono w warunkach poniżej',
			race: {
				coldSub: 'llama.cpp · ustawienia domyślne',
				hotSub: 'ten sam plik · nasz silnik',
				prompt: 'Zaplanuj mi sobotę w Krakowie',
				text: 'Rano zacznij od kawy na Kazimierzu, zanim zrobi się tłoczno, a potem przejdź bulwarami nad Wisłą pod Wawel. Dziedziniec zamku jest bezpłatny, więc na komnaty kup bilet tylko wtedy, gdy masz ochotę. Na obiad wybierz pierogi albo zupę w barze mlecznym przy Starym Mieście: szybko, tanio i po krakowsku. Po południu Sukiennice i Rynek, a jeśli pada, Muzeum pod Rynkiem. Wieczorem wróć na Kazimierz albo przejdź kładką na Podgórze, gdzie jest spokojniej. Kolację zarezerwuj dzień wcześniej, bo w sobotę miejsca szybko znikają. Wygodne buty obowiązkowo: wszystko jest blisko, a najlepiej zwiedza się pieszo.',
				summary: 'Animacja: {card}, {model} {quant}. Ta sama odpowiedź pisana w zmierzonym tempie: typowa aplikacja {a0} tokenu na sekundę, nasz silnik {a2} tokenu na sekundę. Ten sam skrypt pomiarowy po obu stronach.',
				burstNote: 'Paczka = tokeny przyjęte w jednym kroku MTP (zmierzone: {burst} na krok); średnie tempo = zmierzone t/s',
				msNote: 'czas kroku {a} → {b} ms (zmierzone)',
				liveNote: 'Nasz silnik: średnio {a2} t/s (mediana); wahania w granicach zmierzonego zakresu {lo}–{hi}. Typowa aplikacja: {a0} t/s, arkusz nie podaje zakresu, wahania najwyżej ±1%',
				stripNote: 'Pasek pod tekstem: każdy krok z ostatnich 1,6 s, wysokość = liczba tokenów w kroku',
				textNote: 'Tekst jest przykładem; tempo słów z pomiaru (t/s ÷ {tpw} tokenu na słowo).'
			}
		},
		how: {
			title: 'Trzy kroki.|Każdy zmierzony.',
			scan: {
				k: '01',
				title: 'Skan',
				head: 'Najpierw czytamy|Twoją kartę.',
				body: 'Model, pamięć, przepustowość, limit mocy. Lokalnie, bez uprawnień administratora i bez wysyłania czegokolwiek.',
				vram: 'pamięci VRAM',
				bw: 'przepustowość pamięci',
				power: 'limit mocy',
				arch: 'architektura'
			},
			fit: {
				k: '02',
				title: 'Dobór',
				head: 'Model, który|naprawdę się mieści.',
				body: 'Liczymy pamięć z kontekstem i buforami, nie tylko rozmiar pliku. Za duży model odpada od razu.',
				vram: 'VRAM',
				file: 'plik modelu',
				used: 'nasz silnik zajmuje',
				free: 'zapasu',
				extra: 'kontekst, KV i bufory silnika',
				fits: 'pasuje',
				nofit: 'nie pasuje',
				ghost: 'ten sam model w Q8_0',
				ghostNote: 'Q8_0: rozmiar pliku z naszego estymatora. Sam plik jest większy niż cała pamięć karty.',
				usedNote: 'Zajętość VRAM przez nasz silnik przy kontekście z warunków pomiaru.'
			},
			boost: {
				k: '03',
				title: 'Przyspieszenie',
				head: 'Warstwa po warstwie,|aż\u00a0w czerwone pole.',
				body: 'Ten sam model, ta sama karta. Każda warstwa to osobny pomiar tym samym skryptem.',
				layers: ['Typowa aplikacja', 'Najlepsze flagi + MTP', 'Nasz silnik'],
				subs: ['llama.cpp z ustawieniami domyślnymi', 'upstream llama.cpp, spekulacja MTP', 'lżejszy draft i własne kernele'],
				total: 'łącznie',
				unit: 'tokenów na sekundę'
			}
		},
		results: {
			meta: {
				title: `Wyniki — ${N}`,
				description: 'Zmierzone przyspieszenie na każdej karcie i każdym modelu: typowa aplikacja, najlepsze flagi i nasz silnik, z warunkami i źródłem każdej liczby.'
			},
			teaser: {
				title: 'Każda para zmierzona tym samym skryptem.',
				lede: 'Typowa aplikacja i nasz silnik, ta sama karta i ten sam plik modelu.',
				link: 'Wszystkie wyniki i szczegóły',
				unit: 't/s · typowa aplikacja → nasz silnik'
			},
			title: 'Wybierz kartę.|Zobacz różnicę.',
			gpu: 'Karta graficzna',
			model: 'Model',
			gainOf: 'nasz silnik wobec: {before}',
			race: 'Ta sama odpowiedź, zmierzone tempo',
			words: 'Odpowiedź na 500 słów',
			lengths: 'Długości: czas odpowiedzi na 500 słów (≈ {t500} tokenów) jest wyliczony z tempa. Wyścig to przykładowa odpowiedź na {words} słów (≈ {tok} tokenów) w tym samym tempie. Samo tempo zmierzono w warunkach podanych pod paskami.',
			derived: 'wyliczone z t/s',
			done: 'gotowe',
			gap: '{s} s szybciej',
			diffTitle: 'Uwaga: różne skrypty pomiarowe',
			noRace: 'Wyścig i stopery pokazujemy tylko wtedy, gdy obie strony zmierzył ten sam skrypt.',
			conditions: 'Warunki',
			more: 'Zobacz wszystko o swojej karcie',
			summary: '{card}, {model}: {cold} {a} tokenu na sekundę, {hot} {b} tokenu na sekundę.'
		},
		engine: {
			title: 'Przyspieszamy cały stos.|Każdą warstwę mierzymy.',
			model: 'model',
			card: 'karta graficzna',
			layers: [
				['Własne kernele GPU', 'matmul · atencja · MoE'],
				['Mniej przestojów GPU', 'mniej uruchomień · PM4'],
				['Szybszy sampler i host', 'krótsza droga CPU'],
				['Sprytniejsza spekulacja', 'MTP · DFlash'],
				['Pamięć i sterowniki', 'dopasowanie do VRAM'],
				['Profil pod kartę', 'zmierzony dla GPU']
			] as [string, string][],
			zoom: 'Warstwa 02 z bliska',
			zoomNote: 'Kreska = kernel, przerwa = GPU czeka. Zbliżenie na ułamek jednego tokenu.',
			kernels: 'uruchomień na token',
			gaps: 'przerwy',
			gpu: 'praca GPU',
			up: 'upstream',
			ours: 'nasz silnik',
			split: 'Skąd zysk',
			flags: 'flagi MTP (upstream)',
			mine: 'nasz silnik',
			allOurs: 'cały zysk to nasz silnik'
		},
		quality: {
			title: 'Ten sam model, ta sama jakość — zmierzone.',
			less: '≈ {x}× mniej',
			lessNote: 'tyle mniejsza jest różnica, którą wprowadza nasz silnik, niż najmniejsza zmiana formatu kwantyzacji na tej linijce',
			kld: 'KLD',
			kldDef: 'Dywergencja Kullbacka–Leiblera: o ile rozkład kolejnego tokenu różni się od wzorca. Zero znaczy: identycznie.',
			zone: 'rząd szumu samego upstreamu',
			zoneNote: 'Wniosek raportu: KLD naszego silnika „mieści się w szumie samego upstreamu”. Wszystkie cztery wartości leżą w tym samym rzędzie wielkości (10⁻⁴–10⁻³).',
			ours: 'nasz silnik',
			noise: 'szum upstreamu',
			fmt: 'zmiana formatu (inny model: LFM2.5 na {card}, wobec Q8_0)',
			bad: 'zła jakość',
			axis: 'KLD, skala logarytmiczna',
			where: 'Pomiar na {card}.',
			body: 'Nasze domyślne wyjście zachłanne nie jest bit w bit identyczne z upstream (łatki 0001, 0002 i 0013). Dlatego mierzymy KLD.',
			link: 'Jak mierzymy jakość',
			qwen: {
				same: 'ten sam skrypt',
				cross: 'orientacyjnie: różne skrypty',
				kld: 'KLD na NVIDIA',
				kldPending: 'w toku',
				valTag: 'w walidacji · jeszcze nie w produkcie',
				valTitle: 'Tryb bit-exact na {card}',
				valChecks: [
					'MTP = zwykłe dekodowanie, bajt w bajt (n_max {nmax})',
					'długie prompty {long} tokenów: identycznie',
					'powtórne zapytania: identycznie ({det} scenariuszy)',
					'testy kerneli: {ops}'
				],
				valSpeed: 'MTP w tym trybie: {a} t/s wobec {b} t/s silnika produkcyjnego',
				valSpeedNote: 'Ten sam skrypt ({script}). Liczby szybkości pochodzą z pliku podsumowania przebiegu; notatka badawcza jeszcze ich nie zawiera.'
			}
		},
		cards: {
			title: 'Zmierzone,|karta po karcie.',
			lede: 'Każda karta ma swoją stronę: modele, które się mieszczą, wyniki i warunki pomiaru.',
			faster: 'szybciej',
			diff: 'różne skrypty: porównanie orientacyjne',
			queue: 'W kolejce pomiarów',
			note: 'Na kafelkach: polecany model karty albo, gdy nie ma dla niego porównania tym samym skryptem, pierwszy model, który je ma. Nasz silnik wobec typowej aplikacji; warunki są na stronach kart.',
			open: 'Otwórz eksplorator kart'
		},
		privacy: {
			overline: 'Prywatność',
			title: 'Skan działa na Twoim komputerze.|Rozmowy nigdy go nie opuszczają.',
			lede: 'Skan czyta tylko specyfikację sprzętu i sam niczego nie wysyła. Wynik to zwykły tekst: widzisz każde pole.',
			link: 'Zobacz, co czyta skan',
			scanLink: 'Komendy skanu',
			diagram: ['skan', 'Twój komputer', 'internet'],
			never: 'Nigdy nie odczytujemy',
			neverList: ['nazwy komputera ani użytkownika', 'numerów seryjnych, UUID karty, adresów MAC', 'listy plików i programów', 'treści promptów i rozmów', 'lokalizacji']
		},
		faq: {
			title: 'Zanim|zapytasz.',
			items: [
				[
					'Czy to inny model niż ten, który znam?',
					'Nie. Używamy tych samych plików modelu (GGUF) co inne aplikacje i przyspieszamy silnik, który je uruchamia. Nasze wyjście nie jest bit w bit identyczne z upstream, dlatego jakość sprawdzamy miarą KLD; mieści się w szumie samego upstreamu.'
				],
				[
					'Czy działa na kartach NVIDIA?',
					'Tak. Mamy pomiary na kartach NVIDIA i AMD, każdy z warunkami i źródłem. Lista kart z wynikami jest w eksploratorze kart, a kolejne czekają w kolejce pomiarów.'
				],
				[
					'Ile przyspieszy na moim komputerze?',
					'To zależy od karty i modelu. Na {card} z {model} zmierzyliśmy {total}; na słabszych kartach z małymi modelami zysk bywa niewielki. Dla kart bez pomiaru pokazujemy szacunek z naszego wzoru, zawsze oznaczony jako szacunek.'
				],
				[
					'Co wysyłacie na swój serwer?',
					'Domyślnie nic. Skan i rozmowy działają lokalnie. Udostępnienie wyniku do bazy profili to osobna zgoda, domyślnie wyłączona, z podglądem danych.'
				],
				[
					'Dlaczego tokeny, a nie słowa?',
					'Silniki liczą tokeny. Po polsku jedno słowo to średnio {pl} tokenu, po angielsku {en}, dlatego przy czasie odpowiedzi podajemy też słowa.'
				],
				[
					'Czy to działa na Windowsie?',
					'Projektujemy na Windows, Linux i macOS, ale dziś mierzymy na Linuksie. Na Windowsie wyniki mogą się różnić; pokażemy je, gdy je zmierzymy.'
				]
			]
		},
		final: {
			title: 'Twoja karta|może więcej.',
			lede: 'Sprawdź, ile z niej wyciśniemy. Bez zmiany modelu.',
			cards: 'Sprawdź swoją kartę',
			method: 'Metodologia',
			tacho: '{card}, nasz silnik: {v} tokenu na sekundę'
		},
		footer: {
			tagline: 'Lokalne AI, które samo się przyspiesza. Bez zmiany modelu.',
			product: 'Produkt',
			legal: 'Prawne',
			legalLinks: { terms: 'Regulamin', privacy: 'Polityka prywatności', cookies: 'Polityka cookies', ai: 'Informacja o AI', imprint: 'Dane firmy' },
			cookieSettings: 'Ustawienia cookies',
			prototype: 'Prototyp aplikacji',
			draftNote: 'Dokumenty prawne to projekty do weryfikacji przez prawnika.',
			company: 'Dane firmy zostaną uzupełnione po rejestracji spółki.',
			credit: 'Silnik oparty na llama.cpp i ggml (MIT, © The ggml authors).',
			name: `Nazwa „${N}” jest robocza.`
		},
		cookies: {
			title: 'Prywatność na tej stronie',
			body: 'Nie używamy śledzenia ani reklam. Zapisujemy w przeglądarce tylko to, co niezbędne: motyw, jeśli go zmienisz, i ten wybór. Kategoria „Analityka” jest wyłączona i pusta: nie mamy zainstalowanego żadnego narzędzia.',
			accept: 'Akceptuję',
			reject: 'Odrzucam',
			settings: 'Ustawienia',
			save: 'Zapisz wybór',
			necessary: 'Niezbędne',
			necessaryHint: 'Motyw i zapis tego wyboru. Zawsze włączone.',
			analytics: 'Analityka',
			analyticsHint: 'Obecnie żadne narzędzie nie jest zainstalowane. Nic się nie załaduje, nawet po zgodzie.',
			policy: 'Polityka cookies'
		}
	},
	en: {
		meta: {
			title: `${N} — Same hardware. Same model. Just faster.`,
			description: `${N} picks the right AI model for your graphics card, measures it honestly and speeds up the engine. Local, your chats never leave your PC. Every number has a source.`
		},
		nav: {
			how: 'How it works',
			results: 'Results',
			cards: 'Your card',
			quality: 'Quality',
			faq: 'FAQ',
			methodology: 'Methodology',
			start: 'Check your hardware',
			menu: 'Menu',
			close: 'Close menu',
			main: 'Main navigation',
			skip: 'Skip to content',
			lang: 'Polski',
			langLabel: 'Switch language to Polish',
			themeToDark: 'Switch to dark theme',
			themeToLight: 'Switch to light theme'
		},
		hero: {
			title: ['Same hardware. Same model.', 'Just faster.'],
			cta: 'Check your card',
			ctaSecondary: 'How we measure',
			answer: 'This example answer: {words} words ≈ {tok} tokens (in English {tpw} tokens per word). At the measured pace our engine writes it in ≈ {t2} s, the typical app in ≈ {t0} s; the pace itself was measured under the conditions below',
			race: {
				coldSub: 'llama.cpp · default settings',
				hotSub: 'same file · our engine',
				prompt: 'Plan me a Saturday in Kraków',
				text: 'Start the morning with coffee in Kazimierz before it gets busy, then walk along the Vistula boulevards up to Wawel. The castle courtyard is free, so only buy a ticket for the chambers if you feel like it. For lunch, have pierogi or soup at a milk bar near the Old Town: quick, cheap and very local. In the afternoon see the Cloth Hall and the Main Square, and if it rains, the Rynek Underground museum. In the evening head back to Kazimierz or cross the footbridge to Podgórze, where it is calmer. Book dinner a day ahead, because on Saturdays tables go fast. Comfortable shoes are a must: everything is close and the city is best seen on foot.',
				summary: 'Animation: {card}, {model} {quant}. The same answer written at the measured pace: the typical app at {a0} tokens per second, our engine at {a2} tokens per second. The same measurement script on both sides.',
				burstNote: 'Burst = tokens accepted in one MTP step (measured: {burst} per step); the average pace = the measured t/s',
				msNote: 'step time {a} → {b} ms (measured)',
				liveNote: 'Our engine: {a2} t/s on average (median); fluctuations stay within the measured range {lo}–{hi}. Typical app: {a0} t/s, the sheet gives no range, fluctuations at most ±1%',
				stripNote: 'Strip under the text: every step of the last 1.6 s, height = tokens in the step',
				textNote: 'The text is an example; the word pace comes from the measurement (t/s ÷ {tpw} tokens per word).'
			}
		},
		how: {
			title: 'Three steps.|Each one measured.',
			scan: {
				k: '01',
				title: 'Scan',
				head: 'First, we read|your card.',
				body: 'Model, memory, bandwidth, power limit. Locally, without admin rights, without sending anything.',
				vram: 'of VRAM',
				bw: 'memory bandwidth',
				power: 'power limit',
				arch: 'architecture'
			},
			fit: {
				k: '02',
				title: 'Pick',
				head: 'A model that|really fits.',
				body: 'We count memory with context and buffers, not just the file size. A model that is too big is out straight away.',
				vram: 'VRAM',
				file: 'model file',
				used: 'our engine uses',
				free: 'headroom',
				extra: 'context, KV cache and engine buffers',
				fits: 'fits',
				nofit: 'does not fit',
				ghost: 'the same model in Q8_0',
				ghostNote: 'Q8_0: file size from our estimator. The file alone is larger than the card’s whole memory.',
				usedNote: 'VRAM used by our engine at the context from the measurement conditions.'
			},
			boost: {
				k: '03',
				title: 'Accelerate',
				head: 'Layer by layer,|into the redline.',
				body: 'Same model, same card. Every layer is a separate measurement with the same script.',
				layers: ['Typical app', 'Best flags + MTP', 'Our engine'],
				subs: ['llama.cpp with default settings', 'upstream llama.cpp, MTP speculation', 'lighter draft and our own kernels'],
				total: 'in total',
				unit: 'tokens per second'
			}
		},
		results: {
			meta: {
				title: `Results — ${N}`,
				description: 'Measured speed-ups on every card and model: the typical app, the best flags and our engine, with the conditions and source of every number.'
			},
			teaser: {
				title: 'Every pair measured with the same script.',
				lede: 'The typical app and our engine, on the same card with the same model file.',
				link: 'All results and details',
				unit: 't/s · typical app → our engine'
			},
			title: 'Pick a card.|See the difference.',
			gpu: 'Graphics card',
			model: 'Model',
			gainOf: 'our engine vs: {before}',
			race: 'The same answer, at the measured pace',
			words: 'A 500-word answer',
			lengths: 'Lengths: the time for a 500-word answer (≈ {t500} tokens) is derived from the pace. The race is an example answer of {words} words (≈ {tok} tokens) at the same pace. The pace itself was measured under the conditions given under the bars.',
			derived: 'derived from t/s',
			done: 'done',
			gap: '{s} s faster',
			diffTitle: 'Note: different measurement scripts',
			noRace: 'We only show the race and stopwatches when the same script measured both sides.',
			conditions: 'Conditions',
			more: 'See everything about your card',
			summary: '{card}, {model}: {cold} {a} tokens per second, {hot} {b} tokens per second.'
		},
		engine: {
			title: 'We speed up the whole stack.|We measure every layer.',
			model: 'model',
			card: 'graphics card',
			layers: [
				['Our own GPU kernels', 'matmul · attention · MoE'],
				['Less GPU idle time', 'fewer launches · PM4'],
				['Faster sampler and host', 'a shorter CPU path'],
				['Smarter speculation', 'MTP · DFlash'],
				['Memory and drivers', 'fitting into VRAM'],
				['A profile for your card', 'measured per GPU']
			] as [string, string][],
			zoom: 'Layer 02 up close',
			zoomNote: 'A bar is a kernel, a gap is the GPU waiting. Zoomed into a fraction of one token.',
			kernels: 'launches per token',
			gaps: 'gaps',
			gpu: 'GPU work',
			up: 'upstream',
			ours: 'our engine',
			split: 'Where the gain comes from',
			flags: 'MTP flags (upstream)',
			mine: 'our engine',
			allOurs: 'the whole gain is our engine'
		},
		quality: {
			title: 'Same model, same quality — measured.',
			less: '≈ {x}× smaller',
			lessNote: 'that is how much smaller our engine’s difference is than the smallest quantisation format change on this ruler',
			kld: 'KLD',
			kldDef: 'Kullback–Leibler divergence: how far the next-token distribution is from the reference. Zero means identical.',
			zone: 'the order of upstream’s own noise',
			zoneNote: 'The report’s conclusion: our engine’s KLD “is within upstream’s own noise”. All four values sit in the same order of magnitude (10⁻⁴–10⁻³).',
			ours: 'our engine',
			noise: 'upstream noise',
			fmt: 'a format change (another model: LFM2.5 on the {card}, vs Q8_0)',
			bad: 'poor quality',
			axis: 'KLD, log scale',
			where: 'Measured on the {card}.',
			body: 'Our default greedy output is not bit-identical to upstream (patches 0001, 0002 and 0013). That is why we measure KLD.',
			link: 'How we measure quality',
			qwen: {
				same: 'the same script',
				cross: 'indicative: different scripts',
				kld: 'KLD on NVIDIA',
				kldPending: 'in progress',
				valTag: 'in validation · not in the product yet',
				valTitle: 'Bit-exact mode on the {card}',
				valChecks: [
					'MTP = plain decoding, byte for byte (n_max {nmax})',
					'long prompts of {long} tokens: identical',
					'repeated requests: identical ({det} scenarios)',
					'kernel tests: {ops}'
				],
				valSpeed: 'MTP in this mode: {a} t/s vs {b} t/s for the production engine',
				valSpeedNote: 'The same script ({script}). The speed numbers come from the run’s summary file; the research note does not contain them yet.'
			}
		},
		cards: {
			title: 'Measured,|card by card.',
			lede: 'Every card has its own page: the models that fit, the results and the measurement conditions.',
			faster: 'faster',
			diff: 'different scripts: indicative comparison',
			queue: 'In the measurement queue',
			note: 'On the tiles: the card’s recommended model or, when it has no same-script comparison, the first model that does. Our engine vs the typical app; conditions are on the card pages.',
			open: 'Open the cards explorer'
		},
		privacy: {
			overline: 'Privacy',
			title: 'The scan runs on your computer.|Your chats never leave it.',
			lede: 'The scan reads only your hardware spec and sends nothing by itself. The result is plain text: you can read every field.',
			link: 'See what the scan reads',
			scanLink: 'Scan commands',
			diagram: ['scan', 'your computer', 'internet'],
			never: 'We never read',
			neverList: ['computer or user names', 'serial numbers, GPU UUIDs, MAC addresses', 'lists of files or programs', 'your prompts and chats', 'your location']
		},
		faq: {
			title: 'Before|you ask.',
			items: [
				[
					'Is this a different model from the one I know?',
					'No. We use the same model files (GGUF) as other apps and speed up the engine that runs them. Our output is not bit-identical to upstream, so we check quality with KLD; it stays within upstream’s own noise.'
				],
				[
					'Does it work on NVIDIA cards?',
					'Yes. We have measurements on NVIDIA and AMD cards, each with its conditions and source. The cards with results are in the cards explorer, and more are waiting in the measurement queue.'
				],
				[
					'How much faster will it be on my computer?',
					'It depends on the card and the model. On the {card} with {model} we measured {total}; on weaker cards with small models the gain can be small. For cards we have not measured we show an estimate from our formula, always labelled as an estimate.'
				],
				[
					'What do you send to your servers?',
					'Nothing by default. The scan and your chats run locally. Sharing a result with the profile database is a separate opt-in, off by default, with a data preview.'
				],
				[
					'Why tokens and not words?',
					'Engines count tokens. In English a word is about {en} tokens, in Polish about {pl}, so next to answer times we also give words.'
				],
				[
					'Does it work on Windows?',
					'We design for Windows, Linux and macOS, but today we measure on Linux. Results on Windows may differ; we will show them once we have measured them.'
				]
			]
		},
		final: {
			title: 'Your card|can do more.',
			lede: 'See how much we can get out of it. Without changing the model.',
			cards: 'Check your card',
			method: 'Methodology',
			tacho: '{card}, our engine: {v} tokens per second'
		},
		footer: {
			tagline: 'Local AI that speeds itself up. Without changing the model.',
			product: 'Product',
			legal: 'Legal',
			legalLinks: { terms: 'Terms of service', privacy: 'Privacy policy', cookies: 'Cookie policy', ai: 'AI notice', imprint: 'Company details' },
			cookieSettings: 'Cookie settings',
			prototype: 'App prototype',
			draftNote: 'Legal documents are drafts to be reviewed by a lawyer.',
			company: 'Company details will be added once the company is registered.',
			credit: 'Engine based on llama.cpp and ggml (MIT, © The ggml authors).',
			name: `“${N}” is a working name.`
		},
		cookies: {
			title: 'Privacy on this site',
			body: 'No tracking, no ads. We store only what is strictly necessary in your browser: the theme, if you change it, and this choice. The “Analytics” category is off and empty: no analytics tool is installed.',
			accept: 'Accept',
			reject: 'Reject',
			settings: 'Settings',
			save: 'Save choice',
			necessary: 'Strictly necessary',
			necessaryHint: 'Theme and the record of this choice. Always on.',
			analytics: 'Analytics',
			analyticsHint: 'No tool is installed. Nothing will load, even after consent.',
			policy: 'Cookie policy'
		}
	}
};

export const copy = { pl: deepNb(raw.pl), en: deepNb(raw.en) };

export type Copy = (typeof copy)['pl'];
