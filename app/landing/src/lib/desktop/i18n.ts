/**
 * Strings of the desktop-app prototype (`/[lang]/app/…`). Polish is primary; `en` is typed against
 * `pl`, so a missing key is a compile error. Functions take already formatted numbers (see
 * `num()` in `$lib/i18n`) so that decimal separators follow the language.
 */
import { BRAND } from '$lib/brand';
import { plural, type Lang } from '$lib/i18n';

const pl = {
	shell: {
		skip: 'Przejdź do treści',
		title: (screen: string) => `${screen} · ${BRAND.name} (prototyp)`,
		protoLong: 'Prototyp UI — dane z pomiarów RX 7900 XTX, bez działającego silnika',
		protoShort: 'Prototyp UI',
		protoTitle: 'Klikalna makieta aplikacji. Liczby pochodzą z pomiarów na RX 7900 XTX w naszym labie; silnik nie działa.',
		navLabel: 'Ekrany aplikacji',
		menuOpen: 'Pokaż menu',
		menuClose: 'Ukryj menu',
		themeToLight: 'Włącz jasny motyw',
		themeToDark: 'Włącz ciemny motyw',
		langLabel: 'Język',
		machine: 'Ten komputer',
		machineGpu: 'Radeon RX 7900 XTX',
		machineMem: (vram: string, ram: string) => `${vram} GiB VRAM · ${ram} GiB RAM`,
		backToSite: 'Wróć na stronę',
		statusLabel: 'Stan silnika',
		backend: 'Backend',
		gpu: 'GPU',
		gpuOk: 'liczy na GPU ✓',
		model: 'Model',
		api: 'API',
		engine: 'Silnik',
		engineProto: 'makieta, nie działa'
	},
	nav: {
		overview: 'Przegląd ekranów',
		wizard: 'Kreator',
		chat: 'Czat',
		computer: 'Mój komputer',
		result: 'Wynik',
		night: 'Optymalizacja nocna',
		models: 'Modele',
		developers: 'Dla programistów'
	},
	common: {
		source: 'źródło',
		measured: 'zmierzone',
		estimate: 'szacunek',
		soon: 'wkrótce',
		example: 'przykład',
		layoutExample: (section: string) => `przykład układu (raport 06 ${section})`,
		uxExample: (section: string) => `tekst przykładowy z raportu 06 ${section}`,
		protoAction: 'prototyp: przycisk zmienia tylko stan ekranu',
		back: 'Wstecz',
		next: 'Dalej',
		copy: 'Kopiuj',
		copied: 'Skopiowano',
		copyFailed: 'Nie udało się skopiować',
		estSrc: 'estymator, raport 04 §2.2.4',
		sizeSrc: 'rozmiary GGUF: raport 04 §2.3.1 (API Hugging Face, 2026-10-15)',
		tps: 't/s',
		gib: 'GiB',
		gb: 'GB',
		harness: 'harness',
		method: 'metoda',
		build: 'build',
		backend: 'backend',
		config: 'konfiguracja',
		words: (n: number) => plural(n, ['słowo', 'słowa', 'słów'], 'pl'),
		wordsPerSec: (v: string, n: number) => `${v} ${plural(n, ['słowo', 'słowa', 'słów'], 'pl')}/s`,
		seconds: (v: string) => `${v} s`,
		minutes: (v: string) => `${v} min`
	},
	send: {
		show: 'Pokaż, co wysłalibyśmy',
		hide: 'Ukryj podgląd',
		title: 'Podgląd danych do wysłania',
		empty: 'Nic. Telemetria jest wyłączona, więc nie wysyłamy żadnych danych. Skan zostaje na tym komputerze.',
		full: 'Dokładnie ten JSON wyślemy po kalibracji. Bez ID instalacji, bez nazwy komputera, bez treści rozmów. Adres IP serwer odrzuca przy odbiorze (raport 06 §2.2.2).',
		resultsNote: 'Lista „results” wypełni się liczbami z kalibracji; w prototypie jest pusta.'
	},
	scan: {
		title: 'Co wiemy o Twoim komputerze',
		read: 'Odczytujemy lokalnie',
		never: 'Nigdy nie zbieramy',
		readItems: [
			'system i jego wersja',
			'procesor: model, liczba wątków, instrukcje (AVX2, AVX-512)',
			'RAM łącznie',
			'GPU: producent, model, VRAM, sterownik, złącze PCIe',
			'dostępne backendy (CUDA, ROCm, Vulkan, Metal)',
			'wolne miejsce na wybranym dysku',
			'zasilanie i temperatury — tylko na żywo, lokalnie'
		],
		neverItems: [
			'nazwa komputera i użytkownika, ścieżki domowe',
			'numery seryjne, UUID karty, adres MAC, numery dysków',
			'logi systemowe, /proc/cmdline, dmesg',
			'lista plików, zainstalowanych aplikacji, historia',
			'lokalizacja, adres IP, treść rozmów'
		],
		sourceNote: 'Zakres skanu: raport 06 §2.2.1'
	},
	spec: {
		gpu: 'Karta graficzna',
		vram: 'Pamięć karty (VRAM)',
		ram: 'Pamięć RAM',
		cpu: 'Procesor',
		threads: (n: number) => `${n} ${plural(n, ['wątek', 'wątki', 'wątków'], 'pl')}`,
		driver: 'Sterownik',
		driverValue: (kernel: string) => `amdgpu (jądro ${kernel})`,
		pcie: 'Złącze',
		os: 'System',
		power: 'Usypianie karty',
		powerValue: 'wyłączone (runtime PM: on)'
	},
	overview: {
		overline: 'Prototyp aplikacji desktopowej',
		title: `${BRAND.name}: wszystkie ekrany`,
		lead: 'Klikalna makieta aplikacji (docelowo Tauri 2 + Svelte). Liczby pochodzą z pomiarów na RX 7900 XTX w naszym labie albo z estymatora, każda z przypisem źródła. Silnik w tym prototypie nie działa.',
		startWizard: 'Zacznij od kreatora',
		openChat: 'Otwórz czat',
		screensTitle: 'Ekrany',
		desc: {
			wizard: 'Pierwsze uruchomienie w 4 krokach: język i zgoda, skan, rekomendacja modelu, szybka kalibracja.',
			chat: 'Czat na bazie web UI z llama.cpp w naszych kolorach. Wybór „mózgu”, wskaźnik GPU, informacja „rozmawiasz z AI”.',
			computer: 'Co wykrył skan: GPU, pamięć, sterownik, backendy. Ostrzeżenia i naprawy.',
			result: 'Przed → po: słupki, wkład każdej warstwy, jakość odpowiedzi, raport JSON i Cofnij.',
			night: 'Strojenie pod Twój komputer, kiedy śpisz: warunki, postęp, temperatury, historia i Cofnij.',
			models: 'Katalog z etykietami Pasuje / Będzie wolno / Nie zmieści się i licencją przy każdym modelu.',
			developers: 'Lokalne API zgodne z OpenAI, Anthropic i Ollamą: adres, token, przykłady, CLI.'
		},
		rulesTitle: 'Zasady tego prototypu',
		rules: [
			'Każda zmierzona liczba ma przypis: plik i linię w notatkach labu.',
			'Teksty i liczby przykładowe z raportu 06 są oznaczone jako przykład układu.',
			'Czego nie zmierzyliśmy, pokazujemy jako „wkrótce” albo „brak danych”.',
			'Nie porównujemy się z Ollamą ani LM Studio: nie zmierzyliśmy ich tą samą procedurą.'
		]
	},
	wizard: {
		overline: 'Pierwsze uruchomienie',
		title: 'Kreator',
		stepperLabel: 'Kroki kreatora',
		stepOf: (i: number, n: number) => `Krok ${i} z ${n}`,
		steps: ['Język i zgoda', 'Skan sprzętu', 'Rekomendacja', 'Kalibracja'],
		done: 'ukończony',
		current: 'bieżący',
		finish: 'Zakończ i przejdź do czatu',
		s1: {
			langTitle: 'Język aplikacji',
			langHint: 'Zmienisz go później w ustawieniach.',
			consentTitle: 'Zgoda: co dzieje się z danymi',
			scanTitle: 'Skanujemy tylko specyfikację',
			scanBody: 'GPU, pamięć, procesor, sterownik i dostępne backendy. Skan działa na tym komputerze i sam niczego nie wysyła. Bez niego nie dobierzemy modelu.',
			telemetry: 'Wysyłaj anonimowe wyniki pomiarów',
			telemetryHint: 'Tylko liczby: karta, sterownik, model, szybkość. Pomaga dobrać ustawienia innym osobom z tą samą kartą. Domyślnie wyłączone; zmienisz w każdej chwili.',
			crash: 'Wysyłaj raporty awarii silnika',
			crashHint: 'Wersja, kod błędu i model karty, gdy silnik się wyłoży. Domyślnie wyłączone.',
			privacy: 'Polityka prywatności (projekt)'
		},
		s2: {
			title: 'Skan sprzętu',
			lead: 'Skan trwa krócej niż sekundę (cel z PLAN §3.2). Potem silnik uruchamia się na próbę w osobnym procesie.',
			done: 'Skan gotowy',
			selfTest: 'Test silnika w osobnym procesie',
			selfTestNote: 'Przykładowy wynik: w prototypie silnik nie działa.',
			checks: [
				'GPU widoczne dla ROCm (HIP)',
				'GPU widoczne dla Vulkana (RADV)',
				'Mały model testowy ładuje się do VRAM',
				'Odpowiedź testowa zgodna ze wzorcem (greedy md5)'
			],
			problem: 'Gdyby coś było nie tak (np. brak sterownika albo karta niewidoczna), zobaczysz tu jasną instrukcję naprawy albo tryb CPU (PLAN §3.2).'
		},
		s3: {
			title: 'Rekomendacja',
			lead: (vram: string, ctx: string) => `Dobraliśmy model do ${vram} GiB pamięci karty i kontekstu ${ctx} tokenów.`,
			primary: 'Polecamy',
			alternatives: 'Alternatywy',
			roles: { fast: 'Szybszy', polish: 'Po polsku', code: 'Do kodu' },
			choose: 'Wybierz',
			chosen: 'Wybrany',
			size: 'Pobranie',
			time: 'Czas pobierania',
			timeAt: (mbps: number) => `przy ${mbps} Mb/s`,
			link: 'Twoje łącze',
			linkHint: 'Czas to dzielenie rozmiaru przez prędkość łącza, nie pomiar.',
			license: 'Licencja',
			speed: 'Szybkość na tej karcie',
			speedMeasured: (v: string) => `${v} t/s zmierzone (nasz silnik)`,
			speedEstimate: (lo: string, hi: string) => `${lo}–${hi} t/s szacunek bez optymalizacji`,
			download: 'Pobierz i przejdź dalej',
			downloadNote: 'Pobieranie z Hugging Face jest wznawiane i sprawdzane sumą sha256 (PLAN §3.2). W prototypie nic się nie pobiera.'
		},
		s4: {
			title: 'Szybka kalibracja',
			lead: 'Trwa zwykle 1–5 minut (PLAN §4.3). Sprawdzamy, czy wszystko działa poprawnie, i mierzymy punkt wyjścia.',
			start: 'Uruchom kalibrację (symulacja)',
			restart: 'Uruchom jeszcze raz',
			simNote: 'Symulacja: kroki przechodzą same co pół sekundy, żeby pokazać układ. Wyniki w krokach pochodzą z labu albo mówią wprost, że danych jeszcze nie ma.',
			stepNames: [
				'Naprawy L0',
				'Dopasowanie pamięci',
				'Backend i paczka silnika',
				'Koszt kroku spekulacji',
				'Self-test logitów',
				'Punkt wyjścia z testem A/A'
			],
			state: { wait: 'czeka', run: 'trwa', ok: 'gotowe', none: 'brak danych' },
			r: {
				l0: (a: string, b: string) => `Karta nie usypia się w trakcie pracy. Bez tej naprawy model pisał ${a} zamiast ${b} t/s.`,
				mem: (lo: string, hi: string, vram: string, ctx: string) =>
					`Kontekst ${ctx} mieści się: potrzeba ${lo}–${hi} GiB z ${vram} GiB (z zapasem 1 GiB).`,
				backend: 'ROCm (HIP) z paczką silnika amd-opt (70 łatek) z bazy przepisów dla gfx1100.',
				spec: 'MTP włączone. Koszt kroku zmierzymy na Twoim komputerze na syntetycznym tekście, bez Twoich treści.',
				logits: (md5: string) => `Greedy md5 zgodne ze wzorcem (${md5}…).`,
				aa: 'Punkt wyjścia i przedział ufności pojawią się po pomiarze ABBA. W prototypie brak danych.',
				noLab: 'Brak danych z labu dla tego modelu. Zmierzymy na Twoim komputerze.',
				specNone: 'Ten model nie ma zmierzonej głowicy MTP, więc spekulację pomijamy.',
				model: 'Kalibrujemy model'
			},
			src: {
				mem: 'estymator pamięci, raport 04 §2.2.4',
				spec: 'PLAN §4.3 pkt 4'
			},
			ready: 'Gotowe. Możesz rozmawiać.',
			firstChat: 'Pierwsza rozmowa',
			seeResult: 'Zobacz wynik'
		}
	},
	computer: {
		overline: 'Skan sprzętu',
		title: 'Mój komputer',
		lead: 'To odczytał skan na tym komputerze: maszyna labu z Radeonem RX 7900 XTX.',
		specTitle: 'Specyfikacja',
		backendsTitle: 'Backendy',
		backendsCaption: 'Silniki obliczeń dostępne na tym komputerze',
		bkCol: { name: 'Backend', state: 'Stan', note: 'Uwagi' },
		bk: {
			rocm: ['dostępny', 'zmierzony w labie; najszybszy dla Qwen z MTP'],
			vulkan: ['dostępny', 'zmierzony w labie (upstream llama.cpp)'],
			cpu: ['dostępny', 'tryb awaryjny, gdy GPU zawiedzie'],
			cuda: ['nie dotyczy', 'karta AMD'],
			metal: ['nie dotyczy', 'tylko macOS']
		},
		warningsTitle: 'Ostrzeżenia i naprawy',
		baco: {
			title: 'Karta się usypiała (BACO) — naprawiliśmy',
			body: 'Po 5 s bezczynności sterownik usypiał kartę i przenosił całą pamięć modelu do RAM. Model liczył wtedy przez złącze PCIe, wielokrotnie wolniej.',
			asleep: 'karta uśpiona',
			awake: 'po naprawie',
			fix: 'Naprawa: gdy model jest załadowany, karta zostaje aktywna. Działa bez uprawnień administratora.',
			fixed: 'naprawione'
		},
		thermal: {
			title: 'Temperatura pod pełnym obciążeniem',
			body: (w: string, j: string, e: string, f: string) =>
				`Podczas generowania w labie (limit mocy 285 W): ${w} W, hotspot ${j} °C, krawędź ${e} °C, wentylatory ok. ${f} RPM.`,
			note: 'To odczyt z labu, nie z Twojej karty. W aplikacji temperatury czytamy na żywo i tylko lokalnie.'
		},
		srcScan: 'odczyt /proc i /sys tej maszyny, 2026-10-16'
	},
	result: {
		overline: 'Przed → po',
		title: 'Wynik',
		lead: 'Ten sam model (Qwen3.8-27B UD-Q4_K_XL), ta sama karta (RX 7900 XTX). Tak szybko pisze po kolejnych warstwach optymalizacji.',
		barsTitle: 'Szybkość pisania',
		bars: {
			before: 'upstream llama.cpp, bez spekulacji',
			l1: 'L1 konfiguracja (MTP)',
			l2: 'L2 noc',
			l3: 'L3 przepis z labu'
		},
		l2Empty: 'brak pomiaru — pojawi się po pierwszej nocy',
		harnessWarn: (a: string, b: string, c: string) =>
			`${a} i ${b} zmierzono tym samym narzędziem (serve_bench, Vulkan), a ${c} innym (spec_sweep, ROCm). Porównanie ${a} → ${c} jest orientacyjne, dopóki nie zmierzymy wszystkiego jednym harnessem.`,
		noCompetitor: 'Nie porównujemy z Ollamą ani LM Studio: nie zmierzyliśmy ich tą samą procedurą (raport 06 §2.1.3, pkt 8).',
		wordsTitle: 'W słowach i sekundach',
		wordsPl: 'po polsku',
		wordsEn: 'po angielsku',
		answer: (a: string, b: string) => `Odpowiedź na 500 słów: ${a} s → ${b} s`,
		tokNote: (pl: string, en: string, a: string, c: string) =>
			`Przelicznik: ${pl} tokena na słowo po polsku, ${en} po angielsku (tokenizer Qwen3, raport 06 §2.1.2). Liczymy z ${a} i ${c} t/s.`,
		ciLabel: 'Przedział ufności',
		ciValue: 'po kalibracji ABBA (brak danych w tym prototypie)',
		layersTitle: 'Skąd się wziął zysk',
		layersCaption: 'Wkład każdej warstwy (PLAN §2)',
		lCol: { layer: 'Warstwa', what: 'Co zrobiliśmy', gain: 'Wkład' },
		layers: {
			l0: { name: 'L0 Naprawy', what: (a: string, b: string) => `Usypianie karty wyłączone przed pomiarem, więc w tych słupkach wkład 0. Bez naprawy model pisał ${a} zamiast ${b} t/s.` },
			l1: { name: 'L1 Konfiguracja', what: () => 'Spekulacja MTP włączona w upstream llama.cpp; ten sam harness co punkt wyjścia.' },
			l2: { name: 'L2 Noc', what: () => 'Strojenie pod ten komputer. Jeszcze nie mierzone.' },
			l3: { name: 'L3 Przepis', what: () => '70 łatek silnika (amd-opt) na ROCm. Inny harness i backend niż słupki wyżej.' }
		},
		gainNone: '0 (już naprawione)',
		gainSoon: 'wkrótce',
		qualityTitle: 'Jakość odpowiedzi',
		qualityBadge: 'md5 = wzorzec',
		qualityBody: (a: string, b: string, c: string) =>
			`Po każdej zmianie silnika porównujemy greedy md5 odpowiedzi z wersją bazową. Po instalacji 70 łatek wszystkie są zgodne: Qwen bez spekulacji ${a}…, Qwen z MTP ${b}…, LFM ${c}….`,
		mtpNote:
			'Spekulacja (MTP) daje w llama.cpp inny tekst niż dekodowanie bez niej, także w wersji upstream. Dlatego porównujemy MTP z MTP, nie z trybem bez spekulacji. Tryb spekulacji bit w bit jest w badaniach (raport 12).',
		details: 'Szczegóły techniczne',
		kldIntro: 'Te zmiany nie są bit w bit. Przyjęliśmy je bramką KLD: rozbieżność wobec wersji bazowej mieści się w szumie samego pomiaru.',
		rawTitle: 'Surowe pomiary',
		rawCaption: 'Wpisy z rejestru pomiarów użyte na tym ekranie',
		rawCol: { what: 'Pomiar', value: 'Wartość', harness: 'Harness', build: 'Build i backend', source: 'Źródło' },
		statesTitle: 'Podgląd stanów ekranu',
		states: { result: 'Wynik', nochange: 'Brak istotnej zmiany' },
		nochangeTitle: 'Brak istotnej zmiany',
		nochangeBody:
			'Różnica mieści się w szumie pomiaru (|Δ| ≤ 2σ z testu A/A). Nie pokazujemy wtedy zysku i zostawiamy poprzednie ustawienia.',
		nochangeNote: 'Tak wygląda ekran, gdy optymalizacja nic nie dała (zasada z PLAN §2). Liczb tu celowo nie ma.',
		undo: 'Cofnij optymalizację',
		redo: 'Przywróć optymalizację',
		undone: 'Cofnięto. Silnik wraca do ustawień upstream llama.cpp. W prototypie nic nie zmienia się na dysku.',
		report: 'Raport do pobrania (JSON)',
		reportHint: 'Wpisy z rejestru pomiarów: wartości, harness, metoda, build, źródło, wyjątki KLD i md5.',
		reportFile: 'raport-prototyp',
		reportNote: 'Raport z prototypu: pomiary labu na RX 7900 XTX, nie z Twojego komputera. Przedział ufności i noc (L2): brak danych.',
		otherHarness: 'inny harness',
		sameHarness: 'ten sam harness',
		vsPrev: 'wobec poprzedniego słupka'
	},
	night: {
		overline: 'L2 · strojenie lokalne',
		title: 'Optymalizacja nocna',
		lead: 'Dostrajamy silnik pod Twój komputer, kiedy go nie używasz. Każdy wariant przechodzi bramkę md5, a zysk uznajemy dopiero ponad szum pomiaru.',
		startQuote: 'Zostaw komputer na noc (ok. 3–6 h). Możesz w każdej chwili przerwać; nic nie stracisz.',
		startBtn: 'Zacznij tej nocy',
		stopBtn: 'Zakończ',
		conditionsTitle: 'Warunki',
		acOnly: 'Tylko na zasilaczu',
		acHint: 'Na baterii optymalizacja staje.',
		idleOnly: 'Tylko gdy komputer jest bezczynny',
		idleHint: 'Ruch myszy, klawisz, gra albo inny program na GPU oznaczają natychmiastową pauzę.',
		windowOnly: 'Tylko między 1:00 a 7:00',
		quiet: 'Cichy tryb (niższy limit mocy)',
		tempLimit: 'Limit temperatury hotspot',
		tempHint: 'Domyślna wartość 80 °C to przykład z raportu 06 §2.1.4.',
		tempWarn: (seen: string, limit: string) =>
			`W labie hotspot RX 7900 XTX przy generowaniu sięgał ${seen} °C. Przy limicie ${limit} °C strojenie będzie zwalniać albo czekać.`,
		liveTitle: 'Na żywo',
		liveNote: 'Prototyp: wartości zaobserwowane w labie podczas generowania (limit mocy 285 W), nie odczyt z Twojej karty.',
		progress: 'Krok 3/5: Testuję 42 z 180 wariantów · ~2 h 10 min do końca',
		state: { idle: 'nie uruchomiono', run: 'trwa', pause: 'wstrzymane' },
		pausedByYou: 'Wstrzymane przez Ciebie. Wznowimy, gdy klikniesz „Wznów”.',
		notStarted: 'Optymalizacja nie jest uruchomiona. Panel pokazuje, jak będzie wyglądał w trakcie.',
		pause: 'Wstrzymaj',
		resume: 'Wznów',
		tiles: { power: 'Moc', junction: 'Hotspot', edge: 'Krawędź', mem: 'Pamięć', fans: 'Wentylatory' },
		limitOf: (v: string) => `limit ${v}`,
		overLimit: 'powyżej limitu: zwalniamy',
		historyTitle: 'Historia i Cofnij',
		historyNote: 'Zmiany wprowadzone na tej maszynie w labie. Pierwszej nocy jeszcze nie było.',
		hist: {
			engine: { title: 'Paczka silnika amd-opt @ f61994f58 (70 łatek)', detail: (v: string) => `Qwen3.8-27B z MTP: ${v} t/s` },
			baco: { title: 'Naprawa L0: karta nie usypia się', detail: (a: string, b: string) => `${a} → ${b} t/s` }
		},
		nightEmpty: 'Noc: brak wyników. Pierwsza optymalizacja nocna jeszcze się nie odbyła.',
		undo: 'Cofnij',
		redo: 'Przywróć',
		undone: 'cofnięte',
		safetyTitle: 'Co, jeśli coś pójdzie nie tak',
		safety: [
			['Punkty kontrolne', 'Każdy zmierzony wariant zapisujemy od razu. Po restarcie, aktualizacji systemu albo resecie sterownika wznawiamy od ostatniego punktu.'],
			['Windows i reset sterownika (TDR)', 'Windows resetuje sterownik GPU, gdy jedno zadanie trwa ponad 2 s, a 5 resetów w 60 s kończy się awarią systemu. Dlatego każdy wariant ma twardy limit czasu poniżej 2 s i mniejsze rozmiary testów. Nigdy nie zmieniamy ustawień TDR w rejestrze.'],
			['Czarna lista', 'Wariant, który spowodował reset albo zawieszenie, trafia na czarną listę i nie wraca. Ostatnią zmianę wyłączamy automatycznie.'],
			['Bramka jakości', 'Każdy wariant: najpierw greedy md5 lokalnie, potem pomiar ABBA. Zysk liczymy tylko przy |Δ| > 2σ z testu A/A (PLAN §4.3).']
		] as [string, string][],
		cliTitle: 'To samo w terminalu'
	},
	models: {
		overline: 'Katalog',
		title: 'Modele',
		lead: (vram: string, ram: string) =>
			`Etykiety policzyliśmy dla tego komputera: RX 7900 XTX, ${vram} GiB VRAM, ${ram} GiB RAM, Linux.`,
		ctx: 'Pamięć rozmowy (kontekst)',
		ctxOption: (k: number) => `${k} tys. tokenów`,
		filters: 'Filtry',
		chips: { chat: 'czat', code: 'kod', polish: 'polski', fast: 'szybki' },
		chipHint: '„szybki” = mało aktywnych parametrów na token (MoE) albo model oznaczony jako szybki.',
		count: (n: number) => `${n} ${plural(n, ['model', 'modele', 'modeli'], 'pl')}`,
		empty: 'Żaden model nie spełnia wszystkich filtrów naraz.',
		caption: 'Modele z etykietą dopasowania do tego komputera',
		col: { model: 'Model', size: 'Pobranie', quant: 'Kompresja', license: 'Licencja', fit: 'Na tym komputerze', speed: 'Szybkość' },
		fit: { fits: 'Pasuje', tight: 'Na styk', slow: 'Będzie wolno', no: 'Nie zmieści się' },
		fitHint: {
			fits: 'mieści się w pamięci karty z zapasem',
			tight: 'mieści się bez zapasu; przy długiej rozmowie może zabraknąć miejsca',
			slow: 'część modelu trafi do RAM: działa, ale wolniej',
			no: 'za mało pamięci karty i RAM'
		},
		sizes: { S: 'Mały', M: 'Średni', L: 'Duży', XL: 'Bardzo duży' } as Record<string, string>,
		polish: 'po polsku',
		active: 'aktywny',
		measured: (v: string) => `${v} t/s`,
		estimated: (lo: string, hi: string) => `${lo}–${hi} t/s`,
		quantTitle: 'Kompresja jak JPG',
		quantBody: 'Mniejszy plik = szybciej i lżej, minimalnie słabsza jakość. Q4 to rozsądny środek, Q8 jest prawie bez strat. Szybkość i jakość porównujemy zawsze przy tej samej kompresji.',
		speedNote:
			'Szybkość: „zmierzone” to nasz silnik na RX 7900 XTX; „szacunek” to zakres bez optymalizacji z przepustowości pamięci karty (estymator, raport 04 §2.2.4), tylko gdy model mieści się w VRAM.',
		licenseNoteTitle: 'Licencje',
		llama4: 'Llamy 4 nie ma w katalogu: jej licencja nie daje firmom z UE praw do modeli multimodalnych, a każda Llama 4 jest multimodalna (raport 06 §2.4.2).'
	},
	dev: {
		overline: 'Lokalne API',
		title: 'Dla programistów',
		lead: 'API działa tylko na tym komputerze. Podłącz edytor, agenta albo własny skrypt — zgodne z OpenAI, Anthropic i Ollamą.',
		endpoint: 'Adres',
		compatTitle: 'Zgodność',
		compatCaption: 'Obsługiwane interfejsy',
		compatCol: { api: 'Interfejs', path: 'Ścieżki', note: 'Do czego' },
		compat: {
			openai: 'Chat Completions i Responses; lista modeli',
			anthropic: 'Messages',
			ollama: 'dla narzędzi, które znają tylko Ollamę'
		},
		tokenTitle: 'Token',
		tokenLabel: 'Token API (Authorization: Bearer)',
		show: 'Pokaż',
		hide: 'Ukryj',
		regen: 'Wygeneruj nowy',
		regenDone: 'Nowy token gotowy. Poprzedni przestał działać.',
		tokenNote: 'Prototyp: token losujemy w przeglądarce (crypto.getRandomValues). Nie jest nigdzie zapisany i niczego nie otwiera.',
		examplesTitle: 'Przykłady',
		examplesLabel: 'Język przykładu',
		envNote: (env: string) => `Trzymaj token w zmiennej środowiskowej ${env}, nie w kodzie.`,
		samplePrompt: 'Cześć! Napisz jedno zdanie o sobie.',
		securityTitle: 'Bezpieczeństwo',
		security: [
			'Tylko 127.0.0.1: API nie słucha w sieci lokalnej ani w internecie.',
			'Każde żądanie wymaga tokenu (Authorization: Bearer).',
			'Sprawdzamy nagłówki Host i Origin. To chroni przed atakiem DNS rebinding (CVE-2024-28224).',
			'CORS jest domyślnie zamknięty. Strony, którym ufasz, dodajesz do Zaufanych hostów.',
			'Tryb LAN włączysz tylko świadomie, z osobnym kluczem.',
			`Własny port (domyślnie ${BRAND.apiPort}), inny niż 11434 czy 8080, więc nie koliduje z innymi narzędziami.`
		],
		trustedTitle: 'Zaufane hosty',
		trustedHint: 'Origin, z którego przeglądarka może wołać API, np. http://localhost:5173.',
		trustedLabel: 'Dodaj origin',
		trustedAdd: 'Dodaj',
		trustedRemove: (h: string) => `Usuń ${h}`,
		trustedEmpty: 'Pusto: z przeglądarki nikt nie zawoła API. Aplikacje z tokenem działają normalnie.',
		trustedInvalid: 'Wpisz origin w formie http(s)://host[:port], bez ścieżki.',
		cliTitle: 'To samo z terminala',
		cliNote: 'Nazwy poleceń to propozycja prototypu.',
		cli: {
			status: 'adres, port i stan API',
			show: 'pokaż token',
			rotate: 'nowy token (stary przestaje działać)',
			trust: 'dodaj zaufany origin',
			models: 'modele z etykietami dopasowania',
			chat: 'czat w terminalu',
			tune: 'optymalizacja nocna, wznawiana'
		}
	},
	chat: {
		title: 'Czat',
		newChat: 'Nowa rozmowa',
		aiTitle: 'Rozmawiasz z AI',
		aiBody: 'Odpowiedzi pisze model językowy działający na Twoim komputerze. Może się mylić, więc sprawdzaj ważne informacje.',
		aiLaw: 'AI Act, art. 50 ust. 1',
		aiDismiss: 'Rozumiem',
		picker: 'Mózg',
		pick: { S: 'Mały', M: 'Średni', L: 'Duży', PL: 'Polski' },
		speed: (w: string, n: number) => `pisze ~${w} ${plural(n, ['słowo', 'słowa', 'słów'], 'pl')}/s`,
		speedNone: 'szybkość: brak pomiaru',
		speedSrc: (tps: string, tpw: string) => `${tps} t/s ÷ ${tpw} tokena na słowo`,
		sample: 'Przykładowa rozmowa: tekst napisany ręcznie do makiety, nie przez model.',
		you: 'Ty',
		messages: [
			{ role: 'user', text: 'Wyjaśnij krótko, czym różni się RAM od VRAM.' },
			{
				role: 'assistant',
				text: 'RAM to pamięć operacyjna komputera: trzyma programy i dane, z których korzysta procesor. VRAM to pamięć na karcie graficznej. Karta czyta z niej bardzo szybko, dlatego model językowy działa najszybciej, gdy cały mieści się w VRAM. Gdy się nie mieści, część trafia do RAM i odpowiedzi zwalniają.'
			}
		] as { role: 'user' | 'assistant'; text: string }[],
		composer: 'Wiadomość',
		placeholder: 'Napisz wiadomość…',
		send: 'Wyślij',
		protoReply: 'To makieta: silnik w tym prototypie nie działa, więc naprawdę nie odpowiem.',
		empty: 'Nowa rozmowa. Napisz pierwszą wiadomość.',
		footer: 'Odpowiedzi pisze AI na Twoim komputerze i mogą zawierać błędy.',
		messagesLabel: 'Wiadomości',
		protoLabel: 'odpowiedź makiety',
		panelTitle: 'Jak używamy web UI z llama.cpp',
		panel: [
			'Podstawa: tools/ui z llama.cpp (SvelteKit 2 i Svelte 5), licencja MIT, © 2023-2026 The ggml authors.',
			'Kolory i typografię nadpisuje jeden plik: llama-ui-theme.css mapuje nasze tokeny na zmienne shadcn i jest importowany po app.css.',
			'Pozostałe ekrany (Mój komputer, Wynik, Noc, Modele, Dla programistów) dokładamy jako własne trasy obok czatu.',
			'Informację o prawach autorskich ggml i tekst licencji MIT zachowujemy w oknie „O programie” i w pliku NOTICE.',
			'Poprawki do upstreamu llama.cpp zgłaszają ludzie, nie agenci AI.'
		],
		panelSrc: 'PLAN §3.3 pkt 1; LICENSE w llama.cpp'
	}
};

export type DesktopDict = typeof pl;

const en: DesktopDict = {
	shell: {
		skip: 'Skip to content',
		title: (screen: string) => `${screen} · ${BRAND.name} (prototype)`,
		protoLong: 'UI prototype — data from RX 7900 XTX measurements, no running engine',
		protoShort: 'UI prototype',
		protoTitle: 'Clickable app mock-up. Numbers come from RX 7900 XTX measurements in our lab; the engine does not run.',
		navLabel: 'App screens',
		menuOpen: 'Show menu',
		menuClose: 'Hide menu',
		themeToLight: 'Switch to light theme',
		themeToDark: 'Switch to dark theme',
		langLabel: 'Language',
		machine: 'This computer',
		machineGpu: 'Radeon RX 7900 XTX',
		machineMem: (vram: string, ram: string) => `${vram} GiB VRAM · ${ram} GiB RAM`,
		backToSite: 'Back to the website',
		statusLabel: 'Engine status',
		backend: 'Backend',
		gpu: 'GPU',
		gpuOk: 'runs on the GPU ✓',
		model: 'Model',
		api: 'API',
		engine: 'Engine',
		engineProto: 'mock-up, not running'
	},
	nav: {
		overview: 'All screens',
		wizard: 'Setup',
		chat: 'Chat',
		computer: 'My computer',
		result: 'Result',
		night: 'Overnight tuning',
		models: 'Models',
		developers: 'For developers'
	},
	common: {
		source: 'source',
		measured: 'measured',
		estimate: 'estimate',
		soon: 'soon',
		example: 'example',
		layoutExample: (section: string) => `layout example (report 06 ${section})`,
		uxExample: (section: string) => `sample copy from report 06 ${section}`,
		protoAction: 'prototype: the button only changes what the screen shows',
		back: 'Back',
		next: 'Next',
		copy: 'Copy',
		copied: 'Copied',
		copyFailed: 'Could not copy',
		estSrc: 'estimator, report 04 §2.2.4',
		sizeSrc: 'GGUF sizes: report 04 §2.3.1 (Hugging Face API, 2026-10-15)',
		tps: 't/s',
		gib: 'GiB',
		gb: 'GB',
		harness: 'harness',
		method: 'method',
		build: 'build',
		backend: 'backend',
		config: 'configuration',
		words: (n: number) => plural(n, ['word', 'words', 'words'], 'en'),
		wordsPerSec: (v: string, n: number) => `${v} ${plural(n, ['word', 'words', 'words'], 'en')}/s`,
		seconds: (v: string) => `${v} s`,
		minutes: (v: string) => `${v} min`
	},
	send: {
		show: 'Show what we would send',
		hide: 'Hide preview',
		title: 'Preview of outgoing data',
		empty: 'Nothing. Telemetry is off, so we send no data at all. The scan stays on this computer.',
		full: 'This exact JSON is what we would send after calibration. No install ID, no computer name, no chat content. The server drops the IP address on receipt (report 06 §2.2.2).',
		resultsNote: 'The "results" list fills with numbers from calibration; in the prototype it is empty.'
	},
	scan: {
		title: 'What we know about your computer',
		read: 'Read locally',
		never: 'Never collected',
		readItems: [
			'operating system and version',
			'CPU: model, thread count, instruction sets (AVX2, AVX-512)',
			'total RAM',
			'GPU: vendor, model, VRAM, driver, PCIe link',
			'available backends (CUDA, ROCm, Vulkan, Metal)',
			'free space on the chosen drive',
			'power source and temperatures — live and local only'
		],
		neverItems: [
			'computer name, user name, home paths',
			'serial numbers, GPU UUID, MAC address, disk serials',
			'system logs, /proc/cmdline, dmesg',
			'file lists, installed apps, history',
			'location, IP address, chat content'
		],
		sourceNote: 'Scan scope: report 06 §2.2.1'
	},
	spec: {
		gpu: 'Graphics card',
		vram: 'Graphics memory (VRAM)',
		ram: 'System memory (RAM)',
		cpu: 'Processor',
		threads: (n: number) => `${n} ${plural(n, ['thread', 'threads', 'threads'], 'en')}`,
		driver: 'Driver',
		driverValue: (kernel: string) => `amdgpu (kernel ${kernel})`,
		pcie: 'Link',
		os: 'System',
		power: 'GPU sleep',
		powerValue: 'disabled (runtime PM: on)'
	},
	overview: {
		overline: 'Desktop app prototype',
		title: `${BRAND.name}: every screen`,
		lead: 'A clickable mock-up of the app (target: Tauri 2 + Svelte). Numbers come from RX 7900 XTX measurements in our lab or from the estimator, each with a source footnote. The engine does not run in this prototype.',
		startWizard: 'Start with the setup',
		openChat: 'Open the chat',
		screensTitle: 'Screens',
		desc: {
			wizard: 'First run in 4 steps: language and consent, scan, model recommendation, quick calibration.',
			chat: 'Chat built on the llama.cpp web UI in our colours. "Brain" picker, GPU indicator, the "you are talking to an AI" notice.',
			computer: 'What the scan found: GPU, memory, driver, backends. Warnings and fixes.',
			result: 'Before → after: bars, each layer’s contribution, answer quality, JSON report and Undo.',
			night: 'Tuning for your computer while you sleep: conditions, progress, temperatures, history and Undo.',
			models: 'Catalogue labelled Fits / May be slow / Won’t fit, with the licence next to every model.',
			developers: 'Local API compatible with OpenAI, Anthropic and Ollama: address, token, examples, CLI.'
		},
		rulesTitle: 'Rules of this prototype',
		rules: [
			'Every measured number has a footnote: file and line in the lab notes.',
			'Sample copy and numbers from report 06 are labelled as layout examples.',
			'Anything we have not measured is shown as "soon" or "no data".',
			'No comparisons with Ollama or LM Studio: we have not measured them with the same procedure.'
		]
	},
	wizard: {
		overline: 'First run',
		title: 'Setup',
		stepperLabel: 'Setup steps',
		stepOf: (i: number, n: number) => `Step ${i} of ${n}`,
		steps: ['Language and consent', 'Hardware scan', 'Recommendation', 'Calibration'],
		done: 'completed',
		current: 'current',
		finish: 'Finish and open the chat',
		s1: {
			langTitle: 'App language',
			langHint: 'You can change it later in settings.',
			consentTitle: 'Consent: what happens to data',
			scanTitle: 'We only scan the specs',
			scanBody: 'GPU, memory, CPU, driver and available backends. The scan runs on this computer and sends nothing by itself. Without it we cannot pick a model.',
			telemetry: 'Send anonymous measurement results',
			telemetryHint: 'Numbers only: card, driver, model, speed. Helps tune settings for other people with the same card. Off by default; change it any time.',
			crash: 'Send engine crash reports',
			crashHint: 'Version, error code and card model when the engine crashes. Off by default.',
			privacy: 'Privacy policy (draft)'
		},
		s2: {
			title: 'Hardware scan',
			lead: 'The scan takes under a second (target from PLAN §3.2). Then the engine starts once as a test in a separate process.',
			done: 'Scan complete',
			selfTest: 'Engine test in a separate process',
			selfTestNote: 'Sample result: the engine does not run in the prototype.',
			checks: [
				'GPU visible to ROCm (HIP)',
				'GPU visible to Vulkan (RADV)',
				'Small test model loads into VRAM',
				'Test answer matches the reference (greedy md5)'
			],
			problem: 'If something were wrong (e.g. no driver or an invisible card), you would see clear repair steps here, or CPU mode (PLAN §3.2).'
		},
		s3: {
			title: 'Recommendation',
			lead: (vram: string, ctx: string) => `We matched a model to ${vram} GiB of graphics memory and a ${ctx}-token context.`,
			primary: 'Recommended',
			alternatives: 'Alternatives',
			roles: { fast: 'Faster', polish: 'Polish', code: 'For code' },
			choose: 'Choose',
			chosen: 'Chosen',
			size: 'Download',
			time: 'Download time',
			timeAt: (mbps: number) => `at ${mbps} Mb/s`,
			link: 'Your connection',
			linkHint: 'The time is size divided by connection speed, not a measurement.',
			license: 'Licence',
			speed: 'Speed on this card',
			speedMeasured: (v: string) => `${v} t/s measured (our engine)`,
			speedEstimate: (lo: string, hi: string) => `${lo}–${hi} t/s estimate before tuning`,
			download: 'Download and continue',
			downloadNote: 'Downloads from Hugging Face resume and are checked with sha256 (PLAN §3.2). Nothing is downloaded in the prototype.'
		},
		s4: {
			title: 'Quick calibration',
			lead: 'Usually takes 1–5 minutes (PLAN §4.3). We check that everything works correctly and measure the starting point.',
			start: 'Run calibration (simulation)',
			restart: 'Run again',
			simNote: 'Simulation: steps advance every half second to show the layout. Results come from the lab or say plainly that there is no data yet.',
			stepNames: [
				'L0 fixes',
				'Memory fit',
				'Backend and engine package',
				'Speculation step cost',
				'Logit self-test',
				'Baseline with an A/A test'
			],
			state: { wait: 'waiting', run: 'running', ok: 'done', none: 'no data' },
			r: {
				l0: (a: string, b: string) => `The card no longer sleeps while working. Without this fix the model wrote ${a} instead of ${b} t/s.`,
				mem: (lo: string, hi: string, vram: string, ctx: string) =>
					`A ${ctx} context fits: needs ${lo}–${hi} GiB of ${vram} GiB (with a 1 GiB margin).`,
				backend: 'ROCm (HIP) with the amd-opt engine package (70 patches) from the recipe database for gfx1100.',
				spec: 'MTP on. We will measure the step cost on your computer with synthetic text, never your content.',
				logits: (md5: string) => `Greedy md5 matches the reference (${md5}…).`,
				aa: 'The baseline and confidence interval appear after the ABBA run. No data in the prototype.',
				noLab: 'No lab data for this model. We will measure it on your computer.',
				specNone: 'This model has no measured MTP head, so speculation is skipped.',
				model: 'Calibrating model'
			},
			src: {
				mem: 'memory estimator, report 04 §2.2.4',
				spec: 'PLAN §4.3 item 4'
			},
			ready: 'Done. You can start chatting.',
			firstChat: 'First chat',
			seeResult: 'See the result'
		}
	},
	computer: {
		overline: 'Hardware scan',
		title: 'My computer',
		lead: 'This is what the scan read on this computer: our lab machine with a Radeon RX 7900 XTX.',
		specTitle: 'Specs',
		backendsTitle: 'Backends',
		backendsCaption: 'Compute backends available on this computer',
		bkCol: { name: 'Backend', state: 'State', note: 'Notes' },
		bk: {
			rocm: ['available', 'measured in the lab; fastest for Qwen with MTP'],
			vulkan: ['available', 'measured in the lab (upstream llama.cpp)'],
			cpu: ['available', 'fallback if the GPU fails'],
			cuda: ['not applicable', 'AMD card'],
			metal: ['not applicable', 'macOS only']
		},
		warningsTitle: 'Warnings and fixes',
		baco: {
			title: 'Your card was going to sleep (BACO) — fixed',
			body: 'After 5 s idle the driver put the card to sleep and moved the whole model memory to system RAM. The model then ran over the PCIe link, many times slower.',
			asleep: 'card asleep',
			awake: 'after the fix',
			fix: 'Fix: while a model is loaded, the card stays awake. Works without administrator rights.',
			fixed: 'fixed'
		},
		thermal: {
			title: 'Temperature under full load',
			body: (w: string, j: string, e: string, f: string) =>
				`While generating in the lab (285 W power limit): ${w} W, hotspot ${j} °C, edge ${e} °C, fans about ${f} RPM.`,
			note: 'This is a lab reading, not your card. The app reads temperatures live and only locally.'
		},
		srcScan: '/proc and /sys of this machine, read 2026-10-16'
	},
	result: {
		overline: 'Before → after',
		title: 'Result',
		lead: 'Same model (Qwen3.8-27B UD-Q4_K_XL), same card (RX 7900 XTX). How fast it writes after each optimisation layer.',
		barsTitle: 'Writing speed',
		bars: {
			before: 'upstream llama.cpp, no speculation',
			l1: 'L1 configuration (MTP)',
			l2: 'L2 overnight',
			l3: 'L3 lab recipe'
		},
		l2Empty: 'not measured — appears after the first night',
		harnessWarn: (a: string, b: string, c: string) =>
			`${a} and ${b} were measured with the same tool (serve_bench, Vulkan); ${c} with another (spec_sweep, ROCm). The ${a} → ${c} comparison is indicative until everything is measured with one harness.`,
		noCompetitor: 'No comparison with Ollama or LM Studio: we have not measured them with the same procedure (report 06 §2.1.3, item 8).',
		wordsTitle: 'In words and seconds',
		wordsPl: 'in Polish',
		wordsEn: 'in English',
		answer: (a: string, b: string) => `A 500-word answer: ${a} s → ${b} s`,
		tokNote: (pl: string, en: string, a: string, c: string) =>
			`Conversion: ${pl} tokens per word in Polish, ${en} in English (Qwen3 tokenizer, report 06 §2.1.2). Computed from ${a} and ${c} t/s.`,
		ciLabel: 'Confidence interval',
		ciValue: 'after ABBA calibration (no data in this prototype)',
		layersTitle: 'Where the gain came from',
		layersCaption: 'Contribution of each layer (PLAN §2)',
		lCol: { layer: 'Layer', what: 'What we did', gain: 'Contribution' },
		layers: {
			l0: { name: 'L0 Fixes', what: (a: string, b: string) => `GPU sleep was already disabled before measuring, so 0 in these bars. Without the fix the model wrote ${a} instead of ${b} t/s.` },
			l1: { name: 'L1 Configuration', what: () => 'MTP speculation turned on in upstream llama.cpp; same harness as the starting point.' },
			l2: { name: 'L2 Overnight', what: () => 'Tuning for this computer. Not measured yet.' },
			l3: { name: 'L3 Recipe', what: () => '70 engine patches (amd-opt) on ROCm. Different harness and backend from the bars above.' }
		},
		gainNone: '0 (already fixed)',
		gainSoon: 'soon',
		qualityTitle: 'Answer quality',
		qualityBadge: 'md5 = reference',
		qualityBody: (a: string, b: string, c: string) =>
			`After every engine change we compare the greedy md5 of answers with the base version. After installing the 70 patches all of them match: Qwen without speculation ${a}…, Qwen with MTP ${b}…, LFM ${c}….`,
		mtpNote:
			'In llama.cpp, speculation (MTP) produces different text than plain decoding, upstream too. So we compare MTP with MTP, not with plain decoding. A bit-exact speculation mode is being researched (report 12).',
		details: 'Technical details',
		kldIntro: 'These changes are not bit-identical. We accepted them through a KLD gate: the divergence from the base version is within the noise of the measurement itself.',
		rawTitle: 'Raw measurements',
		rawCaption: 'Measurement registry entries used on this screen',
		rawCol: { what: 'Measurement', value: 'Value', harness: 'Harness', build: 'Build and backend', source: 'Source' },
		statesTitle: 'Screen state preview',
		states: { result: 'Result', nochange: 'No significant change' },
		nochangeTitle: 'No significant change',
		nochangeBody:
			'The difference is within measurement noise (|Δ| ≤ 2σ from the A/A test). In that case we show no gain and keep the previous settings.',
		nochangeNote: 'This is the screen when tuning achieved nothing (rule from PLAN §2). It deliberately shows no numbers.',
		undo: 'Undo optimisation',
		redo: 'Restore optimisation',
		undone: 'Undone. The engine goes back to upstream llama.cpp settings. Nothing changes on disk in the prototype.',
		report: 'Download report (JSON)',
		reportHint: 'Measurement registry entries: values, harness, method, build, source, KLD exceptions and md5.',
		reportFile: 'report-prototype',
		reportNote: 'Prototype report: lab measurements on an RX 7900 XTX, not from your computer. Confidence interval and overnight (L2): no data.',
		otherHarness: 'different harness',
		sameHarness: 'same harness',
		vsPrev: 'vs the previous bar'
	},
	night: {
		overline: 'L2 · local tuning',
		title: 'Overnight tuning',
		lead: 'We tune the engine for your computer while you are not using it. Every variant passes an md5 gate, and a gain only counts above measurement noise.',
		startQuote: 'Leave your computer on overnight (about 3–6 h). You can stop at any time; you lose nothing.',
		startBtn: 'Start tonight',
		stopBtn: 'Stop',
		conditionsTitle: 'Conditions',
		acOnly: 'Only on mains power',
		acHint: 'On battery, tuning stops.',
		idleOnly: 'Only while the computer is idle',
		idleHint: 'Mouse movement, a key press, a game or another program on the GPU pause it immediately.',
		windowOnly: 'Only between 1:00 and 7:00',
		quiet: 'Quiet mode (lower power limit)',
		tempLimit: 'Hotspot temperature limit',
		tempHint: 'The 80 °C default is the example from report 06 §2.1.4.',
		tempWarn: (seen: string, limit: string) =>
			`In the lab the RX 7900 XTX hotspot reached ${seen} °C while generating. With a ${limit} °C limit, tuning will slow down or wait.`,
		liveTitle: 'Live',
		liveNote: 'Prototype: values observed in the lab while generating (285 W power limit), not a reading from your card.',
		progress: 'Step 3/5: Testing 42 of 180 variants · ~2 h 10 min left',
		state: { idle: 'not started', run: 'running', pause: 'paused' },
		pausedByYou: 'Paused by you. We resume when you press "Resume".',
		notStarted: 'Tuning is not running. The panel shows what it will look like while it runs.',
		pause: 'Pause',
		resume: 'Resume',
		tiles: { power: 'Power', junction: 'Hotspot', edge: 'Edge', mem: 'Memory', fans: 'Fans' },
		limitOf: (v: string) => `limit ${v}`,
		overLimit: 'above the limit: slowing down',
		historyTitle: 'History and Undo',
		historyNote: 'Changes applied to this lab machine. There has been no night run yet.',
		hist: {
			engine: { title: 'Engine package amd-opt @ f61994f58 (70 patches)', detail: (v: string) => `Qwen3.8-27B with MTP: ${v} t/s` },
			baco: { title: 'L0 fix: the card no longer sleeps', detail: (a: string, b: string) => `${a} → ${b} t/s` }
		},
		nightEmpty: 'Overnight: no results. The first overnight run has not happened yet.',
		undo: 'Undo',
		redo: 'Restore',
		undone: 'undone',
		safetyTitle: 'What if something goes wrong',
		safety: [
			['Checkpoints', 'Every measured variant is saved immediately. After a restart, a system update or a driver reset we resume from the last checkpoint.'],
			['Windows and driver reset (TDR)', 'Windows resets the GPU driver when a single job runs longer than 2 s, and 5 resets within 60 s crash the system. So every variant has a hard time limit under 2 s and smaller test sizes. We never change TDR settings in the registry.'],
			['Blacklist', 'A variant that caused a reset or a hang goes on a blacklist and never returns. The last change is switched off automatically.'],
			['Quality gate', 'Every variant: greedy md5 locally first, then an ABBA measurement. A gain counts only if |Δ| > 2σ from the A/A test (PLAN §4.3).']
		] as [string, string][],
		cliTitle: 'Same in the terminal'
	},
	models: {
		overline: 'Catalogue',
		title: 'Models',
		lead: (vram: string, ram: string) =>
			`Labels computed for this computer: RX 7900 XTX, ${vram} GiB VRAM, ${ram} GiB RAM, Linux.`,
		ctx: 'Conversation memory (context)',
		ctxOption: (k: number) => `${k}k tokens`,
		filters: 'Filters',
		chips: { chat: 'chat', code: 'code', polish: 'Polish', fast: 'fast' },
		chipHint: '"fast" = few active parameters per token (MoE) or a model flagged as fast.',
		count: (n: number) => `${n} ${plural(n, ['model', 'models', 'models'], 'en')}`,
		empty: 'No model matches all filters at once.',
		caption: 'Models with a fit label for this computer',
		col: { model: 'Model', size: 'Download', quant: 'Compression', license: 'Licence', fit: 'On this computer', speed: 'Speed' },
		fit: { fits: 'Fits', tight: 'Tight fit', slow: 'May be slow', no: 'Won’t fit' },
		fitHint: {
			fits: 'fits in graphics memory with room to spare',
			tight: 'fits without a margin; a long conversation may run out of room',
			slow: 'part of the model goes to system RAM: works, but slower',
			no: 'not enough graphics memory and RAM'
		},
		sizes: { S: 'Small', M: 'Medium', L: 'Large', XL: 'Extra large' } as Record<string, string>,
		polish: 'Polish',
		active: 'active',
		measured: (v: string) => `${v} t/s`,
		estimated: (lo: string, hi: string) => `${lo}–${hi} t/s`,
		quantTitle: 'Compression, like JPEG quality',
		quantBody: 'A smaller file = faster and lighter, marginally lower quality. Q4 is a sensible middle, Q8 is almost lossless. We always compare speed and quality at the same compression.',
		speedNote:
			'Speed: "measured" is our engine on the RX 7900 XTX; "estimate" is the untuned range from the card’s memory bandwidth (estimator, report 04 §2.2.4), shown only when the model fits in VRAM.',
		licenseNoteTitle: 'Licences',
		llama4: 'Llama 4 is not in the catalogue: its licence grants EU-based companies no rights to multimodal models, and every Llama 4 is multimodal (report 06 §2.4.2).'
	},
	dev: {
		overline: 'Local API',
		title: 'For developers',
		lead: 'The API runs only on this computer. Connect your editor, an agent or your own script — compatible with OpenAI, Anthropic and Ollama.',
		endpoint: 'Address',
		compatTitle: 'Compatibility',
		compatCaption: 'Supported interfaces',
		compatCol: { api: 'Interface', path: 'Paths', note: 'What for' },
		compat: {
			openai: 'Chat Completions and Responses; model list',
			anthropic: 'Messages',
			ollama: 'for tools that only know Ollama'
		},
		tokenTitle: 'Token',
		tokenLabel: 'API token (Authorization: Bearer)',
		show: 'Show',
		hide: 'Hide',
		regen: 'Generate new',
		regenDone: 'New token ready. The previous one stopped working.',
		tokenNote: 'Prototype: the token is generated in your browser (crypto.getRandomValues). It is not stored anywhere and unlocks nothing.',
		examplesTitle: 'Examples',
		examplesLabel: 'Example language',
		envNote: (env: string) => `Keep the token in the ${env} environment variable, not in code.`,
		samplePrompt: 'Hi! Describe yourself in one sentence.',
		securityTitle: 'Security',
		security: [
			'127.0.0.1 only: the API does not listen on your local network or the internet.',
			'Every request needs the token (Authorization: Bearer).',
			'We validate the Host and Origin headers. This blocks DNS rebinding attacks (CVE-2024-28224).',
			'CORS is closed by default. Add sites you trust to Trusted hosts.',
			'LAN mode only on purpose, with a separate key.',
			`Own port (default ${BRAND.apiPort}), not 11434 or 8080, so it does not clash with other tools.`
		],
		trustedTitle: 'Trusted hosts',
		trustedHint: 'An origin allowed to call the API from a browser, e.g. http://localhost:5173.',
		trustedLabel: 'Add an origin',
		trustedAdd: 'Add',
		trustedRemove: (h: string) => `Remove ${h}`,
		trustedEmpty: 'Empty: no browser page can call the API. Apps with the token work as usual.',
		trustedInvalid: 'Enter an origin as http(s)://host[:port], without a path.',
		cliTitle: 'Same from the terminal',
		cliNote: 'Command names are a prototype proposal.',
		cli: {
			status: 'address, port and API status',
			show: 'show the token',
			rotate: 'new token (the old one stops working)',
			trust: 'add a trusted origin',
			models: 'models with fit labels',
			chat: 'chat in the terminal',
			tune: 'overnight tuning, resumable'
		}
	},
	chat: {
		title: 'Chat',
		newChat: 'New chat',
		aiTitle: 'You are talking to an AI',
		aiBody: 'Answers are written by a language model running on your computer. It can be wrong, so check important information.',
		aiLaw: 'AI Act, Art. 50(1)',
		aiDismiss: 'Got it',
		picker: 'Brain',
		pick: { S: 'Small', M: 'Medium', L: 'Large', PL: 'Polish' },
		speed: (w: string, n: number) => `writes ~${w} ${plural(n, ['word', 'words', 'words'], 'en')}/s`,
		speedNone: 'speed: not measured',
		speedSrc: (tps: string, tpw: string) => `${tps} t/s ÷ ${tpw} tokens per word`,
		sample: 'Sample conversation: text written by hand for the mock-up, not by a model.',
		you: 'You',
		messages: [
			{ role: 'user', text: 'Briefly explain the difference between RAM and VRAM.' },
			{
				role: 'assistant',
				text: 'RAM is your computer’s working memory: it holds the programs and data the processor uses. VRAM is the memory on the graphics card. The card reads it very fast, so a language model runs fastest when it fits entirely in VRAM. When it does not, part of it moves to RAM and answers slow down.'
			}
		] as { role: 'user' | 'assistant'; text: string }[],
		composer: 'Message',
		placeholder: 'Write a message…',
		send: 'Send',
		protoReply: 'This is a mock-up: the engine does not run in this prototype, so I cannot really answer.',
		empty: 'New chat. Write the first message.',
		footer: 'Answers are written by an AI on your computer and may contain mistakes.',
		messagesLabel: 'Messages',
		protoLabel: 'mock-up reply',
		panelTitle: 'How we use the llama.cpp web UI',
		panel: [
			'Base: tools/ui from llama.cpp (SvelteKit 2 and Svelte 5), MIT licence, © 2023-2026 The ggml authors.',
			'One file overrides colours and type: llama-ui-theme.css maps our tokens onto the shadcn variables and is imported after app.css.',
			'The other screens (My computer, Result, Overnight, Models, For developers) are added as our own routes next to the chat.',
			'We keep the ggml copyright notice and the MIT licence text in the About window and in the NOTICE file.',
			'Fixes to upstream llama.cpp are contributed by humans, not AI agents.'
		],
		panelSrc: 'PLAN §3.3 item 1; LICENSE in llama.cpp'
	}
};

export const T: Record<Lang, DesktopDict> = { pl, en };
