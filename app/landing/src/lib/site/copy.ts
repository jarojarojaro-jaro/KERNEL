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
			faq: 'FAQ',
			methodology: 'Metodologia',
			contact: 'Kontakt',
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
			race: {
				/** The hero duel's answer (an example text; the pace is measured). */
				stream: 'Kraków najlepiej poznawać bez pośpiechu, choć jeden weekend wystarczy, żeby złapać jego rytm. Zacznij wcześnie rano na Kazimierzu, kiedy kawiarnie dopiero wystawiają stoliki, a na Placu Nowym przy Okrąglaku sprzedawcy szykują pierwsze zapiekanki. Ulice Szeroka, Józefa i Miodowa są wtedy prawie puste i można spokojnie zajrzeć w podwórka, do synagog i małych galerii, zanim pojawią się wycieczki. Na Kazimierzu warto zatrzymać się dłużej. Przez stulecia było to osobne miasto, a od końca piętnastego wieku centrum życia krakowskich Żydów. Przy ulicy Szerokiej stoi Stara Synagoga, dziś oddział Muzeum Krakowa, a kilka kroków dalej synagoga Remuh i przylegający do niej stary cmentarz z renesansowymi macewami. Wieczorem te same ulice wypełniają się muzyką i rozmowami z ogródków, ale rano słychać tylko kroki i dzwonki rowerów. Z Kazimierza dobrze zejść nad Wisłę i bulwarami ruszyć w stronę Wawelu. Spacer zajmuje kwadrans, a po drodze mija się barki, rowerzystów i wędkarzy, którzy siedzą tu bez względu na pogodę. Pod samym wzgórzem stoi smok wawelski z brązu, który co kilka minut zieje ogniem, ku radości dzieci i zaskoczeniu dorosłych. Na wzgórze wchodzi się przez Bramę Herbową. Dziedziniec zamku jest dostępny bez biletu, a już sam widok arkadowych krużganków wynagradza wspinaczkę. Bilety do komnat i skarbca lepiej kupić wcześniej, bo w sezonie szybko znikają. Katedra wawelska była miejscem koronacji i pochówku polskich królów. Warto wspiąć się na wieżę Zygmuntowską, gdzie wisi dzwon Zygmunt, w który bije się tylko w najważniejsze święta i przy wyjątkowych okazjach. Schody są wąskie i strome, ale z góry widać całe Stare Miasto i szerokie zakole Wisły. W kryptach spoczywają królowie, a także poeci i bohaterowie narodowi, co dobrze pokazuje, jak ważne jest to wzgórze dla polskiej pamięci.',
				text: 'Rano kawa na Kazimierzu, zanim zrobi się tłoczno, potem bulwarami pod Wawel; dziedziniec jest bezpłatny. Na obiad pierogi w barze mlecznym przy Starym Mieście. Po południu Sukiennice i Rynek, a jeśli pada, Muzeum pod Rynkiem. Wieczorem kolacja na Podgórzu, zarezerwowana dzień wcześniej. Wygodne buty obowiązkowo.',
				summary: 'Animacja: {card}, {model} {quant}. Ten sam tekst pisany bez przerwy w zmierzonym tempie: typowa aplikacja {a0} tokenu na sekundę, nasz silnik {a2} tokenu na sekundę. Ten sam skrypt pomiarowy po obu stronach.'
			}
		},
		how: {
			title: 'Trzy kroki.|Każdy zmierzony.',
			scan: {
				k: '01',
				title: 'Skan',
				head: 'Najpierw czytamy|Twoją kartę.',
				body: 'Lokalnie, bez uprawnień administratora i bez wysyłania czegokolwiek. Z tego dobieramy model.',
				lab: 'karta z naszego labu',
				gpu: 'GPU',
				driver: 'Sterownik',
				vram: 'VRAM',
				bw: 'Przepustowość',
				power: 'Limit mocy',
				powerSub: 'domyślny w sterowniku',
				model: 'Polecany model',
				reading: 'Czytam…',
				done: 'Gotowe',
				sr: 'Skan karty z naszego labu, {card}: układ {chip} ({gfx}), sterownik {driver}, {vram} pamięci {mem} na szynie {bus}, przepustowość {bw}, domyślny limit mocy {w}. Polecany model: {model}.'
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
				ghost: 'ten sam model w Q8_0'
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
			title: 'Ten sam model, ta sama karta.|Ponad trzy razy szybciej.',
			meta: 'czat · tokeny na sekundę · każdy krok tym samym skryptem pomiaru',
			vs: 'wobec typowej aplikacji',
			did: 'co zrobiliśmy',
			steps: [
				{ name: 'Typowa aplikacja', sub: 'upstream llama.cpp, ustawienia domyślne', did: [] },
				{ name: 'Najlepsze flagi + MTP', sub: 'upstream llama.cpp z własną spekulacją', did: [] },
				{ name: 'Nasz silnik, 12.10', sub: 'pierwsza wersja', did: ['Własne kernele pod RDNA3'] },
				{ name: 'Nasz silnik, 15.10', sub: 'wydanie produkcyjne', did: ['Mniej uruchomień i fuzje', 'Szybszy sampler i host', 'Sprytniejsza spekulacja MTP'] },
				{ name: 'Nasz silnik dziś', sub: '19.10', did: ['Stabilny replay poleceń PM4', 'Weryfikacja na GPU'] }
			] as { name: string; sub: string; did: string[] }[],
			code: 'Edycja kodu',
			codeNote: 'ta sama karta i model, zadanie edycji plików: typowa aplikacja wobec naszego silnika dziś'
		},
		quality: {
			title: 'Ten sam model,|ta sama jakość.',
			lede: 'Mierzymy, o ile nasz silnik zmienia odpowiedzi modelu względem zwykłego llama.cpp. Wychodzi mniej więcej tyle, ile sam llama.cpp zmienia je przy innym ustawieniu, czyli szum. Zmiana formatu modelu to różnica ok. {x}× większa.',
			ours: 'nasz silnik wobec llama.cpp',
			noise: 'llama.cpp wobec samego siebie',
			here: 'tu, ledwie nad zerem',
			tinyLabel: 'nasz silnik i szum llama.cpp',
			fmtBar: 'zmiana formatu modelu',
			fmtSub: 'LFM2.5: {fmt} wobec Q8_0',
			times: 'większa różnica',
			zoomTitle: 'to samo miejsce w powiększeniu',
			verdict: 'Podobne słupki: nasz silnik zmienia odpowiedzi mniej więcej tyle, co szum samego llama.cpp.',
			caption: 'Skala liniowa. Miara: KLD, czyli o ile różnią się prawdopodobieństwa kolejnego słowa (0 = identycznie). Szum llama.cpp: ten sam llama.cpp z inną wielkością paczki (ubatch 256 i 512). Saluki i Bonsai mierzone na {card}; zmiana formatu to inny model (LFM2.5 na {card2}), pokazany dla skali.',
			same: {
				title: 'Przyspieszenia nie zmieniają tekstu',
				note: 'Włączone czy wyłączone, spekulacja, weryfikacja na GPU i odtwarzanie PM4 dają przy wyborze zachłannym ten sam tekst, bit w bit; pilnują tego testy sum md5. Sama nasza kompilacja liczy część mnożeń w innej kolejności, więc od llama.cpp różni się na poziomie szumu. Dlatego mierzymy KLD.',
				items: ['spekulacja', 'weryfikacja na GPU', 'odtwarzanie PM4'],
				ok: 'ten sam tekst'
			}
		},
		cards: {
			title: 'Zmierzone,|karta po karcie.',
			lede: 'Każda karta ma swoją stronę: modele, które się mieszczą, wyniki i warunki pomiaru.',
			faster: 'szybciej',
			diff: 'różne skrypty: porównanie orientacyjne',
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
		/** The two-terminal stream duel (fx/StreamDuel): hero and final CTA. */
		duel: {
			without: 'Bez Podkrętu',
			with: 'Z Podkrętem',
			faster: 'szybciej',
			tokens: 'tokenów',
			pause: 'Wstrzymaj strumień',
			resume: 'Wznów strumień'
		},
		final: {
			title: 'Twoja karta|może więcej.',
			lede: 'Sprawdź, ile z niej wyciśniemy. Bez zmiany modelu.',
			cards: 'Sprawdź swoją kartę',
			method: 'Metodologia',
			note: 'tekst przykładowy, tempo zmierzone',
			summary: '{card}, {model} {quant}: ta sama odpowiedź płynie bez Podkrętu z prędkością {a0} tokenu na sekundę, a z Podkrętem {a2} tokenu na sekundę.',
			text: 'Cześć! Przesuwam jutrzejsze spotkanie zespołu z rana na popołudnie, bo wypadła mi wizyta u klienta. Sala i link do rozmowy zostają te same. Jeśli komuś nie pasuje nowa pora, dajcie znać do wieczora, a poszukam innego terminu. Przygotujcie proszę krótkie podsumowanie tygodnia, po dwa zdania na osobę. Dzięki i do jutra!'
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
			aiMedia: 'Część grafik i wideo dekoracyjnych oraz zdjęcia sprzętu w katalogu kart wygenerowano AI (Higgsfield, OpenAI).',
			name: `Nazwa „${N}” jest robocza.`
		},
		cookies: {
			title: 'Prywatność na tej stronie',
			body: 'Bez śledzenia i reklam. Zapisujemy tylko motyw i ten wybór.',
			accept: 'Akceptuję',
			necessaryOnly: 'Tylko niezbędne',
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
			faq: 'FAQ',
			methodology: 'Methodology',
			contact: 'Contact',
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
			race: {
				/** The hero duel's answer (an example text; the pace is measured). */
				stream: 'Kraków is best explored without hurrying, although a single weekend is enough to catch its rhythm. Start early in the morning in Kazimierz, when the cafés are only just setting out their tables and the vendors at the Okrąglak on Plac Nowy are getting the first zapiekanki ready. Szeroka, Józefa and Miodowa streets are almost empty then, so you can take your time looking into courtyards, synagogues and small galleries before the tour groups arrive. Kazimierz deserves more than a quick look. For centuries it was a separate town, and from the end of the fifteenth century it was the heart of Jewish life in Kraków. On Szeroka Street stands the Old Synagogue, now a branch of the Museum of Kraków, and a few steps away the Remuh Synagogue with its old cemetery of Renaissance headstones. In the evening the same streets fill with music and the chatter of beer gardens, but in the morning all you hear is footsteps and bicycle bells. From Kazimierz, head down to the Vistula and follow the riverside boulevards towards Wawel. The walk takes a quarter of an hour, past barges, cyclists and anglers who sit here whatever the weather. At the foot of the hill stands the bronze Wawel Dragon, which breathes fire every few minutes, to the delight of children and the surprise of their parents. You enter the hill through the Heraldic Gate. The castle courtyard is free, and the arcaded galleries alone are worth the climb. Tickets for the state rooms and the treasury are best bought in advance, as they sell out quickly in season. Wawel Cathedral was where Polish kings were crowned and buried. It is worth climbing the Sigismund Tower, home of the Sigismund Bell, which rings only on the most important holidays and on exceptional occasions. The stairs are narrow and steep, but from the top you can see the whole Old Town and the wide bend of the Vistula. The crypts hold kings as well as poets and national heroes, which says a lot about what this hill means to Polish memory.',
				text: 'Start with coffee in Kazimierz before it gets busy, then walk the boulevards up to Wawel; the courtyard is free. Lunch: pierogi at a milk bar near the Old Town. In the afternoon, the Cloth Hall and the Main Square, or the Rynek Underground if it rains. Dinner in Podgórze, booked a day ahead. Comfortable shoes are a must.',
				summary: 'Animation: {card}, {model} {quant}. The same text written nonstop at the measured pace: the typical app at {a0} tokens per second, our engine at {a2} tokens per second. The same measurement script on both sides.'
			}
		},
		how: {
			title: 'Three steps.|Each one measured.',
			scan: {
				k: '01',
				title: 'Scan',
				head: 'First, we read|your card.',
				body: 'Locally, without admin rights, without sending anything. This is what we pick the model from.',
				lab: 'the card in our lab',
				gpu: 'GPU',
				driver: 'Driver',
				vram: 'VRAM',
				bw: 'Bandwidth',
				power: 'Power limit',
				powerSub: 'driver default',
				model: 'Recommended model',
				reading: 'Reading…',
				done: 'Done',
				sr: 'Scan of the card in our lab, {card}: {chip} chip ({gfx}), {driver} driver, {vram} of {mem} on a {bus} bus, {bw} bandwidth, default power limit {w}. Recommended model: {model}.'
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
				ghost: 'the same model in Q8_0'
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
			title: 'Same model, same card.|More than three times faster.',
			meta: 'chat · tokens per second · every step measured with the same script',
			vs: 'vs the typical app',
			did: 'what we did',
			steps: [
				{ name: 'Typical app', sub: 'upstream llama.cpp, default settings', did: [] },
				{ name: 'Best flags + MTP', sub: 'upstream llama.cpp with its own speculation', did: [] },
				{ name: 'Our engine, Oct 12', sub: 'first version', did: ['Our own kernels for RDNA3'] },
				{ name: 'Our engine, Oct 15', sub: 'production release', did: ['Fewer launches and fusions', 'A faster sampler and host', 'Smarter MTP speculation'] },
				{ name: 'Our engine today', sub: 'Oct 19', did: ['Stable PM4 command replay', 'Verification on the GPU'] }
			] as { name: string; sub: string; did: string[] }[],
			code: 'Code editing',
			codeNote: 'the same card and model, a file-editing task: the typical app vs our engine today'
		},
		quality: {
			title: 'Same model,|same quality.',
			lede: 'We measure how much our engine changes the model’s answers compared with plain llama.cpp. The change is about as large as llama.cpp’s own under a different setting: noise. Changing the model format makes a difference about {x}× bigger.',
			ours: 'our engine vs llama.cpp',
			noise: 'llama.cpp vs itself',
			here: 'here, just above zero',
			tinyLabel: 'our engine and llama.cpp noise',
			fmtBar: 'a model format change',
			fmtSub: 'LFM2.5: {fmt} vs Q8_0',
			times: 'bigger difference',
			zoomTitle: 'the same spot, magnified',
			verdict: 'Similar bars: our engine changes the answers about as much as llama.cpp’s own noise.',
			caption: 'Linear scale. Metric: KLD, how much the next-word probabilities differ (0 = identical). llama.cpp noise: the same llama.cpp with a different batch size (ubatch 256 vs 512). Saluki and Bonsai measured on the {card}; the format change is another model (LFM2.5 on the {card2}), shown for scale.',
			same: {
				title: 'Speed-ups don’t change the text',
				note: 'On or off, speculation, GPU verification and PM4 replay give the same greedy text, bit for bit; md5 checks guard it. Our build itself computes some multiplications in a different order, so it differs from llama.cpp at noise level. That is why we measure KLD.',
				items: ['speculation', 'GPU verification', 'PM4 replay'],
				ok: 'same text'
			}
		},
		cards: {
			title: 'Measured,|card by card.',
			lede: 'Every card has its own page: the models that fit, the results and the measurement conditions.',
			faster: 'faster',
			diff: 'different scripts: indicative comparison',
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
		/** The two-terminal stream duel (fx/StreamDuel): hero and final CTA. */
		duel: {
			without: 'Without Podkręt',
			with: 'With Podkręt',
			faster: 'faster',
			tokens: 'tokens',
			pause: 'Pause the stream',
			resume: 'Resume the stream'
		},
		final: {
			title: 'Your card|can do more.',
			lede: 'See how much we can get out of it. Without changing the model.',
			cards: 'Check your card',
			method: 'Methodology',
			note: 'example text, measured pace',
			summary: '{card}, {model} {quant}: the same answer streams at {a0} tokens per second without Podkręt and at {a2} tokens per second with Podkręt.',
			text: 'Hi all! I’m moving tomorrow’s team meeting from the morning to the afternoon, because a client visit came up. The room and the call link stay the same. If the new time doesn’t work for you, let me know by tonight and I’ll find another slot. Please bring a short summary of your week, two sentences each. Thanks, and see you tomorrow!'
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
			aiMedia: 'Some decorative images and videos, and the hardware photos in the card catalogue, were generated with AI (Higgsfield, OpenAI).',
			name: `“${N}” is a working name.`
		},
		cookies: {
			title: 'Privacy on this site',
			body: 'No tracking, no ads. We only store your theme and this choice.',
			accept: 'Accept',
			necessaryOnly: 'Necessary only',
			policy: 'Cookie policy'
		}
	}
};

export const copy = { pl: deepNb(raw.pl), en: deepNb(raw.en) };

export type Copy = (typeof copy)['pl'];
