import { BRAND } from '$lib/brand';

const N = BRAND.name;

export const copy = {
	pl: {
		meta: {
			title: `${N} — Ten sam sprzęt. Ten sam model. Po prostu szybciej.`,
			description: `${N} dobiera model AI do Twojej karty graficznej, mierzy go uczciwie i przyspiesza silnik. Lokalnie, bez wysyłania rozmów. Każda liczba ze źródłem.`
		},
		nav: {
			how: 'Jak to działa',
			results: 'Wyniki',
			bits: 'Bit w bit',
			hardware: 'Sprzęt',
			privacy: 'Prywatność',
			pricing: 'Cennik',
			faq: 'FAQ',
			methodology: 'Metodologia',
			start: 'Zacznij',
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
			overline: 'Lokalne AI · zmierzone na Twoim komputerze',
			title: ['Ten sam sprzęt.', 'Ten sam model.', 'Po prostu szybciej.'],
			lead: `${N} dobiera model do Twojej karty, mierzy, ile naprawdę daje, i przyspiesza silnik pod spodem. Model zostaje ten sam, rozmowy nie opuszczają komputera.`,
			cta: 'Sprawdź swój sprzęt',
			ctaSecondary: 'Jak mierzymy',
			chips: ['Działa lokalnie', 'Open core', 'Źródło przy każdej liczbie']
		},
		duel: {
			label: 'Porównanie tempa generowania',
			prompt: 'Pytanie: Jak działa spekulacja MTP?',
			left: 'llama.cpp upstream',
			leftSub: 'Vulkan · bez spekulacji',
			right: `Silnik ${N}`,
			rightSub: 'ROCm · MTP · 70 łatek',
			done: 'gotowe',
			tokens: 'tok',
			wps: 'słów/s',
			pause: 'Wstrzymaj animację',
			play: 'Odtwórz animację',
			replay: 'Odtwórz ponownie',
			caption:
				'RX 7900 XTX · Qwen3.8-27B UD-Q4_K_XL. Tempo odtworzone z naszych pomiarów (38,8 i 109,0 tokenu/s), słowa przeliczone 2,69 tokenu na słowo. Tekst jest przykładem; oba pomiary pochodzą z różnych skryptów, a spekulacja może zmienić tekst względem trybu bez niej.',
			srSummary:
				'Animacja pokazuje ten sam tekst pisany w tempie 38,8 tokenu na sekundę (llama.cpp upstream bez spekulacji) i 109,0 tokenu na sekundę (nasz silnik ze spekulacją MTP) na karcie RX 7900 XTX.',
			text: 'MTP to wbudowana w model mała głowica, która zgaduje kilka następnych tokenów naraz. Duży model sprawdza je jednym przebiegiem: trafione przyjmuje, a od pierwszego chybionego liczy dalej sam. Wagi czytane są z pamięci raz na kilka tokenów zamiast raz na każdy, więc karta pisze szybciej, a o każdym słowie nadal decyduje ten sam model. Najwięcej zyskuje kod i powtarzalny tekst, najmniej swobodna proza.'
		},
		proof: {
			title: 'Liczby z naszego labu',
			items: [
				{ id: 'qwenOursMtp', label: 'Qwen3.8-27B, nasz silnik (MTP)' },
				{ id: 'qwenUpstreamVulkanPlain', label: 'ten sam model, upstream bez spekulacji' },
				{ id: 'lfmOursServer', label: 'LFM2.5-24B-A2B, nasz silnik' }
			],
			patches: 'łatek silnika, każda z wyłącznikiem',
			note: 'RX 7900 XTX, Linux. Szczegóły i surowe dane w metodologii.'
		},
		how: {
			overline: 'Jak to działa',
			title: 'Trzy kroki. Pierwsza rozmowa w kilka minut.',
			lead: 'Większość zysku nie wymaga nocy. Bierze się z poprawnej konfiguracji i przepisów, które przygotowujemy w labie dla konkretnej karty i rodziny modeli.',
			steps: [
				{
					k: '01',
					title: 'Skan',
					body: 'Odczytujemy specyfikację: kartę, pamięć, sterownik, procesor. Lokalnie, w mniej niż sekundę, bez uprawnień administratora. Nic nie jest wysyłane.'
				},
				{
					k: '02',
					title: 'Dobór',
					body: 'Polecamy jeden model, który zmieści się w pamięci z zapasem, i dwie alternatywy: szybszą i po polsku. Rozmiar i licencję widzisz przed pobraniem.'
				},
				{
					k: '03',
					title: 'Przyspieszenie',
					body: 'Naprawiamy pułapki (L0), ustawiamy silnik i spekulację (L1), wgrywamy przepis z labu dla Twojej karty (L3). Opcjonalnie noc dostraja resztę (L2).'
				}
			],
			layers: {
				title: 'Skąd bierze się zysk',
				head: ['Warstwa', 'Co robi', 'Czas u Ciebie', 'Dowód'],
				rows: [
					['L0 Naprawy', 'usypianie karty, model na CPU zamiast GPU, wylewanie VRAM do RAM', 'sekundy', 'u nas karta uśpiona: 4,4 zamiast 92 t/s'],
					['L1 Konfiguracja', 'backend, dopasowanie pamięci, spekulacja MTP', '1–5 min', 'Qwen na Vulkanie: 38,8 → 85,6 t/s samym włączeniem MTP'],
					['L2 Noc', 'wybór wariantów kerneli, długość draftu na Twoich tekstach', 'godziny', 'jeszcze nie zmierzone na komputerach użytkowników'],
					['L3 Przepis', 'nowe kernele i fuzje dla pary karta × model, z labu', '0 (aktualizacja)', 'Qwen na RX 7900 XTX: 85,6 → 109,0 t/s']
				],
				note: 'Liczby L0, L1 i L3 pochodzą z różnych dni i skryptów pomiarowych na tej samej karcie. Zob. metodologię.'
			}
		},
		results: {
			overline: 'Wyniki',
			title: 'Co zmierzyliśmy, dokładnie tak, jak zmierzyliśmy',
			lead: 'Każdy wiersz to para pomiarów z podanym skryptem, wersją silnika i plikiem źródłowym. Nie pokazujemy porównań z Ollamą ani LM Studio, bo jeszcze ich nie zmierzyliśmy tym samym narzędziem.',
			caption: 'Generowanie tekstu (tokeny/s, wyżej = lepiej) na RX 7900 XTX, Linux.',
			head: ['Model', 'Punkt startowy', 'Nasz silnik', 'Jak mierzone'],
			sameHarness: 'ten sam skrypt pomiarowy',
			diffHarness: 'różne skrypty pomiarowe: porównanie orientacyjne',
			cloudTitle: 'Karty NVIDIA: pomiar w toku',
			cloudLead: 'Kampania w chmurze ruszyła 16.10.2026. Pokazujemy tylko karty z gotowym zestawieniem (scorecard), dokładnie z jego statusem md5. Karty bez zestawienia nie mają liczb.',
			cloudNone: 'brak opublikowanych wyników',
			cloudPrelim: 'wstępne: kampania trwa',
			cloudVariant: 'Wariant',
			cloudMethod: 'spec_sweep, 6 promptów × 2 seedy, T=1; zakres = rozrzut między promptami; md5 „DIFF” = wyjście różni się od upstream, trwa wyjaśnianie',
			more: 'Pełna metodologia i surowe liczby'
		},
		bits: {
			overline: 'Bit w bit',
			title: 'Szybciej nie może znaczyć „trochę inaczej”.',
			lead: 'Przyspieszenie, które zmienia odpowiedzi, to w praktyce inny model. Dlatego każdą zmianę w silniku sprawdzamy, zanim trafi do Ciebie.',
			how: [
				{
					title: 'Greedy md5',
					body: 'Ten sam prompt, dekodowanie zachłanne, świeży serwer. Skrót md5 odpowiedzi musi być identyczny przed i po łatce.'
				},
				{
					title: 'Hash logitów',
					body: 'Dla zmian w kernelach porównujemy pełne logity kolejnych kroków. Identyczne bajty znaczą identyczną numerykę.'
				},
				{
					title: 'Bramka KLD',
					body: 'Gdy zmiana z założenia rusza numerykę, mierzymy dywergencję KL wobec bazy i porównujemy z szumem samej bazy. Tylko za zgodą, nigdy po cichu.'
				}
			],
			statusTitle: 'Stan na dziś, uczciwie',
			status: [
				'Większość z 70 łatek jest bitowo identyczna: md5 odpowiedzi nie zmienia się po ich włączeniu.',
				'Trzy zmiany przeszły bramkę KLD zamiast md5. Każda ma wynik w metodologii, np. KLD 0,0067 przy szumie bazy 0,0098.',
				'W llama.cpp spekulacja (MTP) daje inny tekst zachłanny niż dekodowanie bez niej, także w wersji upstream. Tryb bitowo identycznej spekulacji jest w badaniach.'
			],
			cudaDiff: 'Pierwsze pomiary na kartach NVIDIA (CUDA) pokazały różnicę md5 naszego silnika względem upstream. Szukamy łatki, która ją powoduje; do tego czasu nie twierdzimy, że na NVIDIA jest bit w bit.',
			promise: 'Obietnica brzmi więc: ten sam model, ta sama jakość, a nasze przyspieszenia nie zmieniają odpowiedzi względem tego samego trybu bez nich.',
			badge: 'odpowiedzi identyczne · md5'
		},
		hardware: {
			overline: 'Sprzęt',
			title: 'Gdzie mamy pomiary, a gdzie dopiero będą',
			lead: 'Rozwijamy i mierzymy na Linuksie. Na Windowsie obiecujemy dziś naprawy, konfigurację i przenośne łatki, dopóki tam nie zmierzymy więcej.',
			measured: 'zmierzone',
			progress: 'pomiar w toku',
			soon: 'wkrótce',
			groups: { measured: 'Zmierzone', progress: 'Pomiar w toku', soon: 'Na liście labu' },
			platforms: [
				{ os: 'Linux', state: 'measured', body: 'AMD ROCm i Vulkan, pełny stos łatek. Tu powstały wszystkie liczby z tej strony.' },
				{ os: 'Windows', state: 'soon', body: 'Naprawy L0, konfiguracja L1 i łatki niezależne od ROCr. Część zysku AMD (PM4) wymaga Linuksa.' },
				{ os: 'macOS', state: 'soon', body: 'Metal, później MLX. W planie po wersji na Windows i Linux.' }
			]
		},
		privacy: {
			overline: 'Prywatność',
			title: 'Skan czyta specyfikację. Twoje rozmowy zostają u Ciebie.',
			lead: 'Skan działa lokalnie i sam niczego nie wysyła. Wypisuje dane na ekranie i krótki kod, który możesz wkleić w formularz. Kod to zwykły tekst: widzisz każde pole.',
			reads: 'Odczytujemy',
			never: 'Nigdy nie odczytujemy',
			readList: ['system i jego wersję', 'procesor: model, liczba wątków, AVX2/AVX-512', 'pamięć RAM łącznie', 'kartę: producent, model, VRAM, sterownik', 'łącze PCIe karty'],
			neverList: ['nazwy komputera ani użytkownika', 'numerów seryjnych, UUID karty, adresów MAC', 'listy plików i programów', 'treści promptów i rozmów', 'lokalizacji'],
			telemetry: 'Telemetria w aplikacji jest domyślnie wyłączona. Każde udostępnienie danych to osobny przełącznik z podglądem dokładnego JSON-a przed wysłaniem.',
			code: 'Zobacz kod skryptów skanu',
			scanLink: 'Komendy skanu'
		},
		pricing: {
			overline: 'Cennik (hipoteza)',
			title: 'Darmowy rdzeń. Płatne strojenie, jeśli okaże się warte swojej ceny.',
			lead: 'Nic jeszcze nie sprzedajemy. Zapisz się na listę i wybierz cenę, którą uważasz za uczciwą. To pomaga nam sprawdzić, czy płatna wersja w ogóle ma sens.',
			plans: [
				{
					id: 'free',
					name: 'Free',
					price: '0 zł',
					per: 'na zawsze',
					items: ['skan i rekomendacja modelu', 'pobieranie z weryfikacją sha256', 'naprawy L0 i konfiguracja L1', 'gotowe przepisy L3 z bazy dla popularnych kart', 'czat i lokalne API']
				},
				{
					id: 'turbo',
					name: 'Turbo',
					price: '149 zł',
					per: 'rocznie · lub 299 zł dożywotnio (pierwsze osoby)',
					items: ['noc L2: strojenie pod Twój komputer', 'ponowne strojenie po aktualizacjach', 'Tryb maksymalny z bramką KLD (za zgodą)', 'priorytet Twojej karty w kolejce labu', 'nowe modele w dniu premiery'],
					featured: true
				}
			],
			hypothesis: 'Ceny to hipoteza do sprawdzenia (PLAN §8), nie oferta.',
			form: {
				title: 'Lista oczekujących',
				email: 'E-mail',
				emailHint: 'Wyślemy jedną wiadomość z linkiem potwierdzającym (podwójne opt-in), gdy ruszy zapis.',
				choice: 'Która opcja byłaby dla Ciebie w porządku?',
				choices: [
					['free', 'Zostanę przy Free'],
					['yearly', 'Turbo 149 zł / rok'],
					['lifetime', 'Turbo 299 zł dożywotnio'],
					['monthly', 'Wolał(a)bym 19 zł / miesiąc']
				],
				gpu: 'Twoja karta (opcjonalnie)',
				gpuPh: 'np. RTX 4070',
				consent: 'Zgadzam się na jedną wiadomość e-mail o starcie zapisów. Mogę cofnąć zgodę w każdej chwili.',
				privacyLink: 'Polityka prywatności',
				submit: 'Zapisz mnie',
				errEmail: 'Podaj poprawny adres e-mail.',
				errConsent: 'Bez tej zgody nie możemy do Ciebie napisać.',
				thanksTitle: 'Dziękujemy. Twój wybór się liczy.',
				thanksBody: 'Uczciwie: zapis jeszcze nie działa. Backend listy nie jest uruchomiony, więc ten formularz niczego nie wysłał ani nie zapisał. Twój adres nie opuścił przeglądarki.',
				again: 'Wróć do formularza'
			}
		},
		faq: {
			overline: 'FAQ',
			title: 'Częste pytania',
			items: [
				['Czy to inny model niż ten, który znam?', 'Nie. Używamy tych samych plików modelu (GGUF) co inne aplikacje. Przyspieszamy silnik, który go uruchamia, a każdą zmianę sprawdzamy testem md5 albo bramką KLD.'],
				['Czy muszę mieć kartę AMD?', 'Nie. Nasze najlepsze wyniki są dziś z karty AMD RX 7900 XTX, bo na niej pracujemy. Karty NVIDIA mierzymy właśnie w chmurze; liczby pokażemy, gdy będą kompletne.'],
				['Ile to przyspiesza na moim komputerze?', 'Tego nie wiemy, dopóki nie zmierzymy. Formularz sprzętu pokaże przedział z naszego estymatora i to, co zmierzyliśmy dla podobnej karty. Aplikacja zmierzy Twój komputer na miejscu.'],
				['Co wysyłacie na swój serwer?', 'Domyślnie nic. Skan i rozmowy działają lokalnie. Udostępnienie wyniku do bazy profili to osobna, wyłączona domyślnie zgoda z podglądem danych.'],
				['Dlaczego tokeny, a nie słowa?', 'Silniki liczą tokeny. Po polsku jedno słowo to średnio około 2,7 tokenu, po angielsku około 1,2, więc pokazujemy obie miary.'],
				['Czy to działa na Windowsie?', 'Projektujemy od początku na Windows, Linux i macOS, ale mierzymy na razie na Linuksie. Na Windowsie część łatek AMD nie działa, bo wymaga sterownika ROCr dostępnego tylko na Linuksie.'],
				['Czy kod jest otwarty?', 'Łatki silnika są otwarte i zgłaszamy je do llama.cpp. Zamknięte zostają baza profili i orkiestrator strojenia.'],
				['Kiedy premiera?', 'Najpierw kończymy pomiary na kolejnych kartach. Zapisz się na listę, a damy znać jedną wiadomością.']
			]
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
			bits: 'Bit for bit',
			hardware: 'Hardware',
			privacy: 'Privacy',
			pricing: 'Pricing',
			faq: 'FAQ',
			methodology: 'Methodology',
			start: 'Get started',
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
			overline: 'Local AI · measured on your computer',
			title: ['Same hardware.', 'Same model.', 'Just faster.'],
			lead: `${N} picks the model that fits your graphics card, measures what it really delivers, and speeds up the engine underneath. The model stays the same, your chats stay on your machine.`,
			cta: 'Check your hardware',
			ctaSecondary: 'How we measure',
			chips: ['Runs locally', 'Open core', 'A source for every number']
		},
		duel: {
			label: 'Generation speed comparison',
			prompt: 'Question: How does MTP speculation work?',
			left: 'llama.cpp upstream',
			leftSub: 'Vulkan · no speculation',
			right: `${N} engine`,
			rightSub: 'ROCm · MTP · 70 patches',
			done: 'done',
			tokens: 'tok',
			wps: 'words/s',
			pause: 'Pause animation',
			play: 'Play animation',
			replay: 'Play again',
			caption:
				'RX 7900 XTX · Qwen3.8-27B UD-Q4_K_XL. Pace replayed from our measurements (38.8 and 109.0 tokens/s), words converted at 1.17 tokens per word. The text is an example; the two measurements come from different scripts, and speculation can change the text compared with plain decoding.',
			srSummary:
				'The animation shows the same text written at 38.8 tokens per second (upstream llama.cpp, no speculation) and at 109.0 tokens per second (our engine with MTP speculation) on an RX 7900 XTX.',
			text: "MTP is a small head built into the model that guesses the next few tokens at once. The big model checks them in a single pass: it keeps the ones it agrees with and continues on its own from the first miss. The weights are read from memory once per several tokens instead of once per token, so the card writes faster while the same model still decides every word. Code and repetitive text gain the most, free-form prose the least."
		},
		proof: {
			title: 'Numbers from our lab',
			items: [
				{ id: 'qwenOursMtp', label: 'Qwen3.8-27B, our engine (MTP)' },
				{ id: 'qwenUpstreamVulkanPlain', label: 'same model, upstream, no speculation' },
				{ id: 'lfmOursServer', label: 'LFM2.5-24B-A2B, our engine' }
			],
			patches: 'engine patches, each with an off switch',
			note: 'RX 7900 XTX, Linux. Details and raw data in the methodology.'
		},
		how: {
			overline: 'How it works',
			title: 'Three steps. Your first chat in minutes.',
			lead: 'Most of the gain does not need an overnight run. It comes from correct configuration and recipes we build in our lab for a specific card and model family.',
			steps: [
				{ k: '01', title: 'Scan', body: 'We read the spec sheet: card, memory, driver, CPU. Locally, in under a second, no admin rights. Nothing is sent.' },
				{ k: '02', title: 'Pick', body: 'One model that fits your memory with headroom, plus two alternatives: a faster one and a Polish-language one. Size and license shown before download.' },
				{ k: '03', title: 'Accelerate', body: 'We fix the traps (L0), configure the engine and speculation (L1), and install the lab recipe for your card (L3). Optionally, a night run tunes the rest (L2).' }
			],
			layers: {
				title: 'Where the gain comes from',
				head: ['Layer', 'What it does', 'Time on your PC', 'Evidence'],
				rows: [
					['L0 Fixes', 'GPU falling asleep, model on CPU instead of GPU, VRAM spilling to RAM', 'seconds', 'our card asleep: 4.4 instead of 92 t/s'],
					['L1 Configuration', 'backend, memory fit, MTP speculation', '1–5 min', 'Qwen on Vulkan: 38.8 → 85.6 t/s just by enabling MTP'],
					['L2 Night', 'choosing kernel variants, draft length on your own texts', 'hours', 'not yet measured on user machines'],
					['L3 Recipe', 'new kernels and fusions for a card × model pair, from the lab', '0 (an update)', 'Qwen on RX 7900 XTX: 85.6 → 109.0 t/s']
				],
				note: 'The L0, L1 and L3 numbers come from different days and measurement scripts on the same card. See the methodology.'
			}
		},
		results: {
			overline: 'Results',
			title: 'What we measured, exactly as we measured it',
			lead: 'Each row is a pair of measurements with its script, engine version and source file. We do not show comparisons with Ollama or LM Studio because we have not measured them with the same tool yet.',
			caption: 'Text generation (tokens/s, higher is better) on an RX 7900 XTX, Linux.',
			head: ['Model', 'Starting point', 'Our engine', 'How measured'],
			sameHarness: 'same measurement script',
			diffHarness: 'different measurement scripts: indicative comparison',
			cloudTitle: 'NVIDIA cards: measurement in progress',
			cloudLead: 'The cloud campaign started on 16 Oct 2026. We only show cards with a finished scorecard, exactly with its md5 status. Cards without one show no numbers.',
			cloudNone: 'no published results',
			cloudPrelim: 'preliminary: campaign running',
			cloudVariant: 'Variant',
			cloudMethod: 'spec_sweep, 6 prompts × 2 seeds, T=1; range = spread across prompts; md5 “DIFF” = output differs from upstream, under investigation',
			more: 'Full methodology and raw numbers'
		},
		bits: {
			overline: 'Bit for bit',
			title: 'Faster must not mean “slightly different”.',
			lead: 'A speed-up that changes the answers is, in practice, a different model. So every engine change is checked before it reaches you.',
			how: [
				{ title: 'Greedy md5', body: 'Same prompt, greedy decoding, fresh server. The md5 hash of the answer must be identical before and after the patch.' },
				{ title: 'Logit hash', body: 'For kernel changes we compare the full logits of successive steps. Identical bytes mean identical numerics.' },
				{ title: 'KLD gate', body: 'When a change is meant to touch numerics, we measure KL divergence against the base and compare it with the base’s own noise. Only with your consent, never silently.' }
			],
			statusTitle: 'Where we stand today, honestly',
			status: [
				'Most of the 70 patches are bit-identical: the answer md5 does not change when they are enabled.',
				'Three changes passed the KLD gate instead of md5. Each result is in the methodology, e.g. KLD 0.0067 with base noise of 0.0098.',
				'In llama.cpp, speculation (MTP) yields different greedy text than plain decoding, upstream included. A bit-exact speculation mode is in research.'
			],
			cudaDiff: 'The first measurements on NVIDIA cards (CUDA) showed an md5 difference between our engine and upstream. We are tracking down the patch responsible; until then we do not claim bit-for-bit on NVIDIA.',
			promise: 'So the promise is: same model, same quality, and our speed-ups do not change the answers compared with the same mode without them.',
			badge: 'identical answers · md5'
		},
		hardware: {
			overline: 'Hardware',
			title: 'Where we have measurements, and where they are coming',
			lead: 'We develop and measure on Linux. On Windows we currently promise fixes, configuration and portable patches until we measure more there.',
			measured: 'measured',
			progress: 'in progress',
			soon: 'soon',
			groups: { measured: 'Measured', progress: 'Measurement in progress', soon: 'On the lab list' },
			platforms: [
				{ os: 'Linux', state: 'measured', body: 'AMD ROCm and Vulkan, full patch stack. Every number on this page was produced here.' },
				{ os: 'Windows', state: 'soon', body: 'L0 fixes, L1 configuration and patches that do not depend on ROCr. Part of the AMD gain (PM4) needs Linux.' },
				{ os: 'macOS', state: 'soon', body: 'Metal, later MLX. Planned after the Windows and Linux versions.' }
			]
		},
		privacy: {
			overline: 'Privacy',
			title: 'The scan reads a spec sheet. Your chats stay with you.',
			lead: 'The scan runs locally and sends nothing by itself. It prints the data on screen and a short code you can paste into the form. The code is plain text: you can read every field.',
			reads: 'We read',
			never: 'We never read',
			readList: ['your OS and its version', 'CPU: model, threads, AVX2/AVX-512', 'total RAM', 'graphics card: vendor, model, VRAM, driver', 'the card’s PCIe link'],
			neverList: ['computer or user names', 'serial numbers, GPU UUIDs, MAC addresses', 'lists of files or programs', 'your prompts and chats', 'your location'],
			telemetry: 'Telemetry in the app is off by default. Every kind of sharing is a separate switch with a preview of the exact JSON before anything is sent.',
			code: 'Read the scan scripts',
			scanLink: 'Scan commands'
		},
		pricing: {
			overline: 'Pricing (hypothesis)',
			title: 'A free core. Paid tuning, if it proves worth the price.',
			lead: 'We are not selling anything yet. Join the list and pick the price you would consider fair. It tells us whether a paid edition makes sense at all.',
			plans: [
				{
					id: 'free',
					name: 'Free',
					price: '€0',
					per: 'forever',
					items: ['scan and model recommendation', 'downloads verified with sha256', 'L0 fixes and L1 configuration', 'ready L3 recipes for popular cards', 'chat and local API']
				},
				{
					id: 'turbo',
					name: 'Turbo',
					price: '€39',
					per: 'per year · or €79 lifetime (early birds)',
					items: ['L2 night: tuning for your machine', 're-tuning after updates', 'Max mode with a KLD gate (opt-in)', 'priority for your card in the lab queue', 'new models on launch day'],
					featured: true
				}
			],
			hypothesis: 'Prices are a hypothesis to test (PLAN §8), not an offer.',
			form: {
				title: 'Waitlist',
				email: 'Email',
				emailHint: 'We will send one message with a confirmation link (double opt-in) when sign-ups open.',
				choice: 'Which option would feel fair to you?',
				choices: [
					['free', 'I’d stay on Free'],
					['yearly', 'Turbo €39 / year'],
					['lifetime', 'Turbo €79 lifetime'],
					['monthly', 'I’d prefer a monthly plan']
				],
				gpu: 'Your graphics card (optional)',
				gpuPh: 'e.g. RTX 4070',
				consent: 'I agree to receive one email about the launch of sign-ups. I can withdraw at any time.',
				privacyLink: 'Privacy policy',
				submit: 'Add me',
				errEmail: 'Enter a valid email address.',
				errConsent: 'Without this consent we cannot write to you.',
				thanksTitle: 'Thank you. Your choice counts.',
				thanksBody: 'To be honest: sign-up is not live yet. The waitlist backend is not running, so this form sent and stored nothing. Your address never left your browser.',
				again: 'Back to the form'
			}
		},
		faq: {
			overline: 'FAQ',
			title: 'Frequently asked questions',
			items: [
				['Is this a different model from the one I know?', 'No. We use the same model files (GGUF) as other apps. We speed up the engine that runs it, and every change is checked with an md5 test or a KLD gate.'],
				['Do I need an AMD card?', 'No. Our best results today are from an AMD RX 7900 XTX because that is the card we work on. NVIDIA cards are being measured in the cloud right now; we will publish numbers when they are complete.'],
				['How much faster will it be on my computer?', 'We do not know until we measure. The hardware form shows a range from our estimator and what we measured on a similar card. The app measures your machine on the spot.'],
				['What do you send to your servers?', 'Nothing by default. The scan and your chats run locally. Sharing a result with the profile database is a separate opt-in, off by default, with a data preview.'],
				['Why tokens and not words?', 'Engines count tokens. In English a word is about 1.2 tokens, in Polish about 2.7, so we show both measures.'],
				['Does it work on Windows?', 'We design for Windows, Linux and macOS from day one, but for now we measure on Linux. On Windows some AMD patches do not apply because they need the ROCr runtime, which only exists on Linux.'],
				['Is it open source?', 'The engine patches are open and we contribute them to llama.cpp. The profile database and the tuning orchestrator stay closed.'],
				['When is the launch?', 'First we finish measuring more cards. Join the list and we will tell you with a single email.']
			]
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

export type Copy = (typeof copy)['pl'];
