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
				text: 'Rano kawa na Kazimierzu, zanim zrobi się tłoczno, potem bulwarami pod Wawel; dziedziniec jest bezpłatny. Na obiad pierogi w barze mlecznym przy Starym Mieście. Po południu Sukiennice i Rynek, a jeśli pada, Muzeum pod Rynkiem. Wieczorem kolacja na Podgórzu, zarezerwowana dzień wcześniej. Wygodne buty obowiązkowo.',
				summary: 'Animacja: {card}, {model} {quant}. Ta sama odpowiedź pisana w zmierzonym tempie: typowa aplikacja {a0} tokenu na sekundę, nasz silnik {a2} tokenu na sekundę. Ten sam skrypt pomiarowy po obu stronach.',
				burstNote: 'Paczka = tokeny przyjęte w jednym kroku MTP (zmierzone: {burst} na krok); średnie tempo = zmierzone t/s',
				msNote: 'czas kroku {a} → {b} ms (zmierzone)',
				liveNote: 'Tokeny pojawiają się dokładnie w zmierzonym tempie (mediana: nasz silnik {a2} t/s, typowa aplikacja {a0} t/s); czas odpowiedzi = tokeny ÷ mediana. Cyfry na zegarze to zawsze zmierzona mediana; wskazówka podczas pisania waha się o ±3% wokół niej, a w przerwie między odpowiedziami opada do zera',
				stripNote: 'Animacja się zapętla: w jednym cyklu wolniejsza strona pisze odpowiedź raz, a szybsza tyle pełnych odpowiedzi, ile mieści jej zmierzone tempo (każda z krótką przerwą); kropki przy nazwie to ukończone odpowiedzi w cyklu',
				textNote: 'Tekst jest przykładem; tempo słów z pomiaru (t/s ÷ {tpw} tokenu na słowo).'
			}
		},
		how: {
			title: 'Trzy kroki.|Każdy zmierzony.',
			scan: {
				k: '01',
				title: 'Skan',
				head: 'Najpierw czytamy|Twoją kartę.',
				body: 'Model, pamięć, przepustowość, moc. Lokalnie, bez uprawnień administratora i bez wysyłania czegokolwiek.',
				detected: 'wykryto',
				lab: 'karta z naszego labu',
				vram: 'pamięć VRAM',
				bw: 'przepustowość pamięci',
				power: 'moc karty (TBP)',
				arch: 'układ',
				note: 'Nasza karta testowa. Pamięć, szyna, prędkość pamięci, moc (Total Board Power) i złącza: specyfikacja Sapphire. Navi 31: vulkaninfo na maszynie labu. Domyślny limit mocy w sterowniku tej karty: {w} W.'
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
				head: 'Trzy ustawienia.|Nasz silnik najszybszy.',
				body: 'Ten sam model, ta sama karta, ten sam skrypt pomiaru. Każdy słupek to osobny pomiar.',
				layers: ['Typowa aplikacja', 'Najlepsze flagi + MTP', 'Nasz silnik'],
				subs: ['llama.cpp z ustawieniami domyślnymi', 'upstream llama.cpp, spekulacja MTP', 'lżejszy draft i własne kernele'],
				vs: 'wobec typowej aplikacji',
				over: 'szybciej niż najlepsze flagi upstreamu',
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
				unit: 't/s · typowa aplikacja → nasz silnik · paski: przyspieszenie (typowa = 1×)'
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
			pick: 'Warstwy silnika',
			zoom: 'z bliska',
			zooms: [
				{
					metric: 'tokenów na sekundę · sam GPU, bez samplera',
					lanes: ['upstream', 'nasz silnik'],
					lane: 'kreska = gotowy token · ten sam odcinek czasu',
					note: 'llama-bench tg128, więc liczy się tylko praca GPU. Upstream z najlepszymi flagami wobec naszego silnika z tymi samymi flagami.',
					extra: []
				},
				{
					metric: 'uruchomień kerneli na token',
					lanes: ['upstream', 'nasz silnik'],
					lane: 'kreska = kernel, przerwa = GPU czeka · ułamek jednego tokenu',
					note: 'Profil kroku (nsys): łączymy kernele, więc GPU rzadziej czeka na kolejne polecenie.',
					extra: ['przerwy', 'praca GPU']
				},
				{
					metric: 'tokenów na sekundę · serwer',
					lanes: ['sampler upstream', 'nasz sampler'],
					lane: 'kreska = gotowy token · ten sam odcinek czasu',
					note: 'Ten sam silnik z sześcioma przełącznikami samplera wyłączonymi i włączonymi. Upstream przy każdym tokenie sortuje na CPU wszystkich 65 tys. kandydatów.',
					extra: []
				},
				{
					metric: 'ms na krok spekulacji',
					lanes: ['pełny draft', 'lżejszy draft'],
					lane: 'blok = krok: draft i weryfikacja · ten sam odcinek czasu',
					note: 'Słownik draftu 64k i głowica MTP w IQ4_XS: krok jest krótszy, a tokenów przyjętych na krok prawie tyle samo.',
					extra: ['tokenów na sekundę', 'tokenów na krok']
				},
				{
					metric: 'tokenów na sekundę',
					lanes: ['karta uśpiona', 'karta czuwa'],
					lane: 'kreska = gotowy token · ten sam odcinek czasu',
					note: 'Bez monitora sterownik usypia kartę po 5 s i przenosi VRAM do RAM, a model działa wtedy przez PCIe. Nasz silnik nie pozwala karcie zasnąć. Notatki nie podają skryptu tego pomiaru: to ilustracja skali.',
					extra: []
				},
				{
					metric: 'tokenów na sekundę · serwer',
					lanes: ['bez profilu', 'profil Ampere'],
					lane: 'kreska = gotowy token · ten sam odcinek czasu',
					note: 'Ustawienia zmierzone dla tej architektury (dwa wiersze na blok w MMVQ, bez fuzji gate/up), teraz domyślne na kartach Ampere.',
					extra: ['sam GPU (tg128)']
				}
			] as { metric: string; lanes: [string, string]; lane: string; note: string; extra: string[] }[]
		},
		quality: {
			title: 'Ten sam model, ta sama jakość — zmierzone.',
			gapLabel: 'Różnica jakości',
			gapOurs: 'nasz silnik wobec upstreamu (gorszy z dwóch modeli)',
			gapFmt: 'najmniejsza zmiana formatu (inny model)',
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
				kldPending: 'w toku'
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
				text: 'Start with coffee in Kazimierz before it gets busy, then walk the boulevards up to Wawel; the courtyard is free. Lunch: pierogi at a milk bar near the Old Town. In the afternoon, the Cloth Hall and the Main Square, or the Rynek Underground if it rains. Dinner in Podgórze, booked a day ahead. Comfortable shoes are a must.',
				summary: 'Animation: {card}, {model} {quant}. The same answer written at the measured pace: the typical app at {a0} tokens per second, our engine at {a2} tokens per second. The same measurement script on both sides.',
				burstNote: 'Burst = tokens accepted in one MTP step (measured: {burst} per step); the average pace = the measured t/s',
				msNote: 'step time {a} → {b} ms (measured)',
				liveNote: 'Tokens appear at exactly the measured pace (median: our engine {a2} t/s, typical app {a0} t/s); answer time = tokens ÷ median. The digits on the dial are always the measured median; while writing, the needle moves within ±3% of it, and between answers it falls back to zero',
				stripNote: 'The animation loops: in one cycle the slower side writes the answer once and the faster side writes as many full answers as its measured pace fits (each with a short pause); the dots next to the name are the answers finished in the cycle',
				textNote: 'The text is an example; the word pace comes from the measurement (t/s ÷ {tpw} tokens per word).'
			}
		},
		how: {
			title: 'Three steps.|Each one measured.',
			scan: {
				k: '01',
				title: 'Scan',
				head: 'First, we read|your card.',
				body: 'Model, memory, bandwidth, power. Locally, without admin rights, without sending anything.',
				detected: 'detected',
				lab: 'the card in our lab',
				vram: 'VRAM',
				bw: 'memory bandwidth',
				power: 'board power (TBP)',
				arch: 'chip',
				note: 'Our test card. Memory, bus, memory speed, power (Total Board Power) and connectors: Sapphire spec sheet. Navi 31: vulkaninfo on the lab machine. Default driver power limit on this card: {w} W.'
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
				head: 'Three setups.|Our engine is fastest.',
				body: 'Same model, same card, same measuring script. Every bar is a separate measurement.',
				layers: ['Typical app', 'Best flags + MTP', 'Our engine'],
				subs: ['llama.cpp with default settings', 'upstream llama.cpp, MTP speculation', 'lighter draft and our own kernels'],
				vs: 'vs the typical app',
				over: 'faster than the best upstream flags',
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
				unit: 't/s · typical app → our engine · bars: speed-up (typical = 1×)'
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
			pick: 'Engine layers',
			zoom: 'up close',
			zooms: [
				{
					metric: 'tokens per second · GPU only, no sampler',
					lanes: ['upstream', 'our engine'],
					lane: 'mark = a finished token · the same stretch of time',
					note: 'llama-bench tg128, so only the GPU work counts. Upstream with the best flags vs our engine with the same flags.',
					extra: []
				},
				{
					metric: 'kernel launches per token',
					lanes: ['upstream', 'our engine'],
					lane: 'bar = a kernel, gap = the GPU waiting · a fraction of one token',
					note: 'Step profile (nsys): we merge kernels, so the GPU waits for its next command less often.',
					extra: ['gaps', 'GPU work']
				},
				{
					metric: 'tokens per second · server',
					lanes: ['upstream sampler', 'our sampler'],
					lane: 'mark = a finished token · the same stretch of time',
					note: 'The same engine with its six sampler switches off and on. For every token, upstream sorts all 65k candidates on the CPU.',
					extra: []
				},
				{
					metric: 'ms per speculation step',
					lanes: ['full draft', 'lighter draft'],
					lane: 'block = a step: draft and verification · the same stretch of time',
					note: 'A 64k draft vocabulary and the MTP head in IQ4_XS: each step is shorter, and almost as many tokens are accepted per step.',
					extra: ['tokens per second', 'tokens per step']
				},
				{
					metric: 'tokens per second',
					lanes: ['card asleep', 'card awake'],
					lane: 'mark = a finished token · the same stretch of time',
					note: 'With no monitor attached, the driver puts the card to sleep after 5 s and moves VRAM to system RAM; the model then runs over PCIe. Our engine keeps the card awake. The notes do not name the script of this measurement: it shows the scale only.',
					extra: []
				},
				{
					metric: 'tokens per second · server',
					lanes: ['no profile', 'Ampere profile'],
					lane: 'mark = a finished token · the same stretch of time',
					note: 'Settings measured for this architecture (two rows per block in MMVQ, no gate/up fusion), now the default on Ampere cards.',
					extra: ['GPU only (tg128)']
				}
			] as { metric: string; lanes: [string, string]; lane: string; note: string; extra: string[] }[]
		},
		quality: {
			title: 'Same model, same quality — measured.',
			gapLabel: 'Quality difference',
			gapOurs: 'our engine vs upstream (the worse of two models)',
			gapFmt: 'the smallest format change (another model)',
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
				kldPending: 'in progress'
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
