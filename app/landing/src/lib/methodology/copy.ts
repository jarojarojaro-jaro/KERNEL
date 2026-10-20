/**
 * Copy of the methodology journey (PL + EN). Numbers are not typed here: components format them
 * from facts.ts / measurements.ts, so the text and the figures cannot drift apart.
 */
import type { Lang } from '$lib/i18n';

const pl = {
	meta: {
		title: 'Metodologia: jak mierzymy i przyspieszamy',
		desc: 'Podróż przez nasz warsztat: uczciwy pomiar ABBA, bramki bezstratności md5 i KLD, profil jednego kroku dekodowania na RX 7900 XTX, spekulacja MTP, błąd PRIV w GFX11 i eksperymenty, które odrzuciliśmy.'
	},
	rail: 'Rozdziały',
	chapter: 'Rozdział',
	sources: 'Źródła',
	illustr: 'ilustracja',
	measured: 'zmierzone',
	replay: 'Odtwórz',
	pause: 'Pauza',
	play: 'Start',
	reset: 'Od nowa',
	step: 'Krok',
	ch: [
		{
			id: 'question',
			nav: 'Pytanie',
			kicker: 'Pytanie',
			title: 'Ta sama karta. Ten sam plik modelu. Ile da samo oprogramowanie?',
			lead: 'Nie zmieniamy kwantyzacji, nie podmieniamy modelu na mniejszy, nie dokupujemy sprzętu. Jedyna zmienna to silnik, który liczy model. I jedna twarda zasada: odpowiedź ma być tak samo dobra.'
		},
		{
			id: 'measure',
			nav: 'Uczciwy pomiar',
			kicker: 'Uczciwy pomiar',
			title: 'Najpierw nauczyliśmy się nie oszukiwać samych siebie.',
			lead: 'Karta się nagrzewa, zegary pływają, a jeden przebieg potrafi skłamać o kilka procent. Zysk z jednej łatki bywa mniejszy niż ten szum. Dlatego każdą zmianę mierzymy tym samym skryptem po obu stronach, na świeżych serwerach, w kolejności ABBA.'
		},
		{
			id: 'quality',
			nav: 'Bezstratnie',
			kicker: 'Bezstratnie albo wcale',
			title: 'Szybciej, ale ani jednego tokenu inaczej.',
			lead: 'Przyspieszenie, które psuje odpowiedź, to nie przyspieszenie. Każda zmiana przechodzi przez bramki: skrót md5 odpowiedzi, testy operacji GPU względem CPU i, gdy kolejność sumowania musi się zmienić, dywergencję KL na tle szumu samego upstreamu.'
		},
		{
			id: 'step',
			nav: 'Gdzie idzie czas',
			kicker: 'Gdzie idzie czas',
			title: 'Jeden krok dekodowania pod mikroskopem.',
			lead: 'Zanim cokolwiek przyspieszymy, rozbieramy krok na kernele. To prawdziwy ślad rocprofv3 z RX 7900 XTX: 946 kerneli, trzy serie i przerwy, w których GPU czeka na procesor.'
		},
		{
			id: 'speculation',
			nav: 'Spekulacja',
			kicker: 'Spekulacja, po ludzku',
			title: 'Zgadnij kilka tokenów naprzód. Sprawdź wszystkie naraz.',
			lead: 'Duży model czyta całe swoje wagi przy każdym kroku, niezależnie od tego, czy liczy jeden token, czy pięć. Mała głowica MTP podsuwa więc kilka tokenów naprzód, a model sprawdza je w jednym kroku. Przyjmuje zgodny początek, resztę odrzuca i dokłada jeden token od siebie. Tekst jest ten, który model napisałby i tak.'
		},
		{
			id: 'metal',
			nav: 'Do metalu',
			kicker: 'Do metalu',
			title: 'Jeden bit w rejestrze, który wywracał kartę.',
			lead: 'Nasz silnik nagrywa sekwencję kerneli i odtwarza ją jako taśmę poleceń PM4, z pominięciem kosztownej ścieżki uruchamiania. Szybko, ale co jakiś czas GPU padało z błędem strony pod adresem 0. Szukaliśmy przyczyny aż do pojedynczego bitu.'
		},
		{
			id: 'negative',
			nav: 'Co odrzuciliśmy',
			kicker: 'Wyniki negatywne',
			title: 'Cmentarzysko pomysłów. Zostawiamy je na widoku.',
			lead: 'Większość pomysłów nie przechodzi. Notujemy każdy: co obiecywał, co zmierzyliśmy i dlaczego go zabiliśmy. Bez tego nie dałoby się ufać liczbom, które zostały.'
		},
		{
			id: 'records',
			nav: 'Tablica wyników',
			kicker: 'Tablica wyników',
			title: 'Przed i po. Ta sama karta, ten sam model, ten sam skrypt.',
			lead: 'Wszystkie pary karta × model, które zmierzyliśmy od początku do końca. „Przed” to typowa aplikacja z ustawieniami domyślnymi, „po” to nasz silnik.'
		}
	],
	q: {
		same: 'Bez zmian',
		card: 'Karta',
		model: 'Model',
		file: 'Plik',
		ctx: 'Jakość',
		ctxV: 'ta sama (bramki w rozdz. 3)',
		upstream: 'Typowa aplikacja',
		ours: 'Nasz silnik',
		live: 'Na żywo, w prawdziwym tempie',
		text: 'Karta graficzna to nie tylko moc obliczeniowa. Przy generowaniu tekstu model czyta wszystkie swoje wagi przy każdym tokenie, więc liczy się każda milisekunda między kernelami, każdy zbędny odczyt pamięci i każdy token, który można zgadnąć wcześniej. ',
		scroll: 'Przewiń, żeby zobaczyć, jak to mierzymy'
	},
	m: {
		rules: [
			['ABBA', 'Warianty przeplatamy A, B, B, A. Dryf karty (temperatura, zegary) rozkłada się wtedy po równo na obie strony.'],
			['Świeży serwer', 'Każde ramię startuje od zera: bez rozgrzanego cache, bez śladów poprzedniego wariantu.'],
			['Seedy i prompty', 'spec_sweep: 6 promptów (PL i EN, proza, technika, kod) × 3 seedy. Mediana, nie najlepszy przebieg.'],
			['ms na krok', 'Decyduje czas jednego kroku, bo przy T=1 liczba tokenów na sekundę zależy też od wylosowanego tekstu.'],
			['Ten sam skrypt', 'Upstream i nasz silnik mierzymy tym samym narzędziem, na tej samej maszynie, z tymi samymi flagami.'],
			['Próg z A/A', 'Dwa przebiegi tego samego wariantu różnią się o 0,09% ms/krok (mediana z 15 par). Mniejszy „zysk” to szum.']
		],
		labTitle: 'Laboratorium dryfu',
		labLead: 'A i B to ten sam program, więc prawdziwa różnica wynosi zero. Karta z każdym przebiegiem trochę zwalnia. Kliknij pola, żeby ułożyć własną kolejność, i zobacz, ile „zysku” zmyśla sam dryf.',
		presets: 'Gotowe układy',
		slot: (i: number, v: string) => `Przebieg ${i}: wariant ${v}. Kliknij, żeby zmienić.`,
		drift: 'dryf karty',
		fake: 'Pozorna różnica B względem A',
		verdictBad: 'Dryf udaje zysk. Taki wynik trafiłby do kosza.',
		verdictOk: 'Dryf znosi się do zera. Zostaje tylko prawdziwa różnica.',
		verdictUneven: 'A i B muszą mieć tyle samo przebiegów.',
		model: 'Model dryfu: każdy kolejny przebieg o 0,4% wolniejszy. Ilustracja zasady, nie pomiar.',
		tTitle: 'T=0 i T=1 w jednym zdaniu',
		t0: 'T=0: model zawsze bierze najbardziej prawdopodobny token. Ten sam prompt daje co do bitu ten sam tekst, więc można porównać skróty md5.',
		t1: 'T=1: model losuje token zgodnie z rozkładem, jak w zwykłej rozmowie. Tekst za każdym razem jest inny, więc porównujemy ms na krok, a nie same tokeny na sekundę.',
		pick: 'Wylosuj następny token',
		next: 'Następny token po „Karta graficzna jest…”'
	},
	l: {
		gates: 'Bramki regresji (greedy md5, świeży serwer)',
		gatesNote: 'Po każdej zmianie, także po poprawce PM4 z rozdziału 6, skróty odpowiedzi są identyczne z zapisanym wzorcem naszego silnika.',
		demoTitle: 'Porównywarka strumieni',
		demoLead: 'Dwa strumienie tokenów: wzorzec i build po zmianie. Porównujemy je token po tokenie, a na końcu skrót całej odpowiedzi. Spróbuj wstrzyknąć błąd.',
		ref: 'Wzorzec',
		cand: 'Po zmianie',
		inject: 'Wstrzyknij błąd zaokrąglenia',
		heal: 'Cofnij błąd',
		hash: 'skrót',
		pass: 'IDENTYCZNE',
		fail: 'ROZJAZD',
		failNote: 'Jeden inny token zmienia wszystko, co po nim. Taka zmiana nie przechodzi bramki md5 i trafia do kosza albo do bramki KLD.',
		demoNote: 'Tekst i skrót (FNV-1a) liczone w przeglądarce, dla ilustracji zasady.',
		tokens: (n: number) => `${n} tokenów`,
		kldTitle: 'KLD: kiedy bit w bit jest niemożliwe',
		kldLead: 'Nasze wielokolumnowe MMVQ sumuje w innej kolejności niż upstream, więc wobec upstreamu nie obiecujemy identycznego tekstu. Mierzymy dywergencję KL rozkładów tokenów i stawiamy ją obok szumu samego upstreamu (RTX 3060).',
		kldOurs: 'nasz vs upstream',
		kldNoise: 'szum upstreamu',
		opsTitle: 'test-backend-ops: każda zmieniona operacja kontra CPU',
		opsNote: 'Każdy przypadek testowy przechodzi. Tryb BITEXACT pozwala sprawdzić weryfikację spekulacji bit w bit.'
	},
	s: {
		modes: ['Krok MTP', 'Krok W16, top-k na CPU', 'Krok W16, top-k na GPU'],
		wall: 'czas kroku',
		busy: 'GPU pracuje',
		idle: 'GPU czeka',
		gaps: 'duże przerwy',
		ms: 'ms',
		timeline: 'Oś czasu jednego kroku (skala rzeczywista)',
		burst: (n: number) => `${n} kerneli`,
		gap: 'przerwa hosta',
		other: 'reszta',
		ops: 'Na co GPU wydaje czas pracy',
		pick: 'Wybierz kernel, żeby zobaczyć jego udział',
		share: (p: string) => `${p} czasu pracy GPU`,
		mmvq5: 'Mnożenie macierz × wektor dla 5 wierszy naraz: token plus 4 tokeny draftu. To czytanie wag z pamięci, czyli fizyczny limit karty.',
		mmvq1: 'To samo dla jednego wiersza naraz.',
		takeaway: 'Ponad 80% czasu pracy GPU (70% całego kroku) to czytanie wag w mmvq n5. Do tego 4 ms, w których GPU czeka na CPU. To tam szukamy kolejnych milisekund.',
		w16Lead: 'Przy edycji kodu weryfikujemy 16 wierszy naraz. Dwie przerwy rosną wtedy do prawie milisekundy: CPU kopiuje 16 MB logitów i przegląda je w poszukiwaniu top-k. Przenieśliśmy top-k na GPU: na host idzie 16 KB zamiast 16 MB.',
		w16Gain: 'Edycja kodu szybsza o 2,2–2,4%, wyjście identyczne bit w bit przy T=0 i T=1.'
	},
	p: {
		chat: 'Czat (MTP)',
		code: 'Edycja kodu (ogon lookup W16)',
		draft: 'draft',
		accepted: 'przyjęte',
		rejected: 'odrzucone',
		bonus: 'od modelu',
		perStep: 'tokenów na krok',
		steps: 'kroków',
		vs: 'kroków bez spekulacji',
		auto: 'Auto',
		chatNote: (x: string) => `Przy czacie wychodzi średnio ${x} tokenu na krok (114,8 t/s × 27,67 ms/krok). Symulacja trafień z tą średnią.`,
		codeNote: (x: string, of: string) => `Przy edycji kodu ogon lookup kopiuje fragmenty z kontekstu: ${x} z ${of} możliwych tokenów na krok. Symulacja trafień z tą średnią.`,
		chatText: 'Model sprawdza propozycje w jednym kroku i przyjmuje tylko te tokeny, które sam by wybrał, więc tekst się nie zmienia.',
		codeText: 'function total(items) { return items.reduce((sum, item) => sum + item.price * item.qty, 0); }',
		speed: 'Prędkość na RX 7900 XTX, Qwen3.8-27B',
		a0: 'Typowa aplikacja',
		a1: 'Upstream + MTP',
		ours: 'Nasz silnik',
		chatRow: 'Czat (spec_sweep, T=1)',
		codeRow: 'Edycja kodu (T=0, 4 pliki)'
	},
	x: {
		storyTitle: 'Śledztwo w pięciu krokach',
		story: [
			['Taśma', 'Nagrywamy ~800 dispatchy kroku i odtwarzamy je pakietami PM4 DISPATCH_DIRECT. Rejestry kernela kopiujemy z jego deskryptora.'],
			['Objaw', 'Raz na jakiś czas: page fault SQC pod adresem 0x0, wiele fal naraz, potem reset GPU. Tylko na taśmie, nigdy na zwykłej ścieżce AQL.'],
			['Wyzwalacz', 'Sterownik w losowych chwilach wywłaszcza kolejki (ewikcja SVM). Fale w trakcie taśmy są zapisywane i przywracane przez CWSR.'],
			['Przyczyna', 'GFX11 wymaga COMPUTE_PGM_RSRC1.PRIV=1 przy każdym dispatchu compute (obejście DEGFX11_12113). Firmware ustawia go sam dla AQL, a nasza taśma brała 0 z deskryptora. Zrzuty faultów to potwierdzają: fale AQL mają priv 1, fale taśmy priv 0.'],
			['Poprawka', 'GGML_HIP_PM4_WA=2: PRIV=1, bez ORDERED_APPEND, RESTART=0. Przed wdrożeniem wymuszaliśmy ewikcje w środku taśmy, żeby sprawdzić, że to naprawdę to.']
		],
		regTitle: 'COMPUTE_PGM_RSRC1',
		regLead: 'Przełącz bit 20 i wywołaj wywłaszczenie w środku taśmy.',
		bit: 'PRIV (bit 20)',
		evict: 'Wywłaszcz kolejkę',
		ok: 'Fale wróciły po wywłaszczeniu. Taśma gra dalej.',
		bad: 'Fale wróciły bez uprawnień: page fault @0x0, reset GPU.',
		idle: 'Taśma gra. Kliknij „Wywłaszcz kolejkę”.',
		resultTitle: 'Po poprawce',
		requests: 'zapytań produkcyjnych',
		faults: 'błędów GPU',
		occTitle: 'Klif obłożenia: VGPR → fale na SIMD',
		occLead: 'Na RDNA3 SIMD ma 1536 rejestrów wektorowych na wątek, przydzielanych blokami po 24. Im więcej rejestrów zjada kernel, tym mniej fal mieści się naraz, a mniej fal to mniej okazji, by ukryć czekanie na pamięć. Przesuń suwak.',
		vgpr: 'VGPR na kernel',
		waves: 'fal na SIMD',
		preset: (v: number) => `Q4_K ncols=5: ${v} VGPR`,
		cliff: 'Kernel Q4_K dla 5 kolumn miał 140 VGPR i 10 fal. Ograniczony do 119 VGPR mieści 12 fal, bez spilla do pamięci.'
	},
	n: {
		killed: 'odrzucone',
		stopped: 'zatrzymane',
		open: 'Pokaż szczegóły',
		promise: 'Obietnica',
		result: 'Wynik',
		why: 'Dlaczego koniec',
		items: [
			{
				id: 'lds',
				name: 'Bariery tylko-LDS',
				fig: '±0,2%',
				tag: 'killed',
				promise: 'Lżejsza synchronizacja w kernelach: czekać tylko na pamięć współdzieloną, nie na całą pamięć.',
				result: 'Średnie z dwóch par ABBA: Qwen pp4096 1130,6 → 1128,8; LFM 6125 → 6139; czat 102,5 → 102,4 t/s. Poprawne bitowo.',
				why: 'Wszystko w szumie. Wąskim gardłem nie są bariery.'
			},
			{
				id: 'oov',
				name: 'Ogon OOV draftu, klastry',
				fig: '−1,5%',
				tag: 'killed',
				promise: 'Głowica draftu zna 64k tokenów z 248k. Dla rzadkich tokenów dołożyć klastry, żeby draft trafiał częściej.',
				result: '111,0 → 109,4 t/s na czacie. Droższa głowica zjada więcej, niż daje trafność.',
				why: 'Ujemny wynik netto. Także wersja z pełnym słownikiem ma ujemny sufit we wszystkich grupach.'
			},
			{
				id: 'router',
				name: 'Router DFlash2 na edycji kodu',
				fig: '+1,1%',
				tag: 'killed',
				promise: 'Drugi drafter, który przejmuje kroki, gdy ogon lookup nie ma czego skopiować.',
				result: 'Sufit wyroczni (idealny wybór w każdym kroku): +1,1% przy T=0, +2,0% przy T=1. Próg opłacalności: +8%.',
				why: 'Ogon W16 bierze już 14,5 z 16 tokenów na krok. Nie ma czego dołożyć. Zabite bez jednej minuty GPU.'
			},
			{
				id: 'wide',
				name: 'MMVQ n=1, szerokie ładowania',
				fig: '−1,0%',
				tag: 'killed',
				promise: 'Mniej instrukcji ładowania na iterację (18 → 12) w mnożeniu dla jednego wiersza.',
				result: 'Qwen tg128 40,86 → 40,41 t/s. md5 identyczne.',
				why: 'Liczba instrukcji ładowania nie jest wąskim gardłem. Mniej instrukcji nie znaczy szybciej.'
			},
			{
				id: 'norm',
				name: 'Fuzja norm w prologu GEMV',
				fig: 'GPU fault',
				tag: 'stopped',
				promise: 'Górny limit zmierzony: pominięcie 129 norm daje +4,6% (1,07 ms na token).',
				result: 'Pierwszy test na GPU zawiesił taśmę PM4: page fault SQC @0x0, reset GPU.',
				why: 'Zasada sprzętowa: po faulcie stop, bez ponawiania. Najpierw przyczyna, potem kolejna próba.'
			}
		]
	},
	r: {
		filterAll: 'Wszystkie',
		before: 'Typowa aplikacja',
		after: 'Nasz silnik',
		speed: 't/s',
		x: 'razy szybciej',
		archive: 'Pełne tabele, skrypty i zasady w archiwum poniżej',
		ctaTitle: 'Sprawdź, ile da Twoja karta.',
		ctaLead: 'Wybierz kartę i model. Pokażemy zmierzony wynik albo uczciwie oznaczony szacunek.',
		cta: 'Znajdź swoją kartę',
		cta2: 'Zacznij instalację'
	}
};

type Copy = typeof pl;

const en: Copy = {
	meta: {
		title: 'Methodology: how we measure and speed things up',
		desc: 'A journey through our workshop: honest ABBA measurement, md5 and KLD losslessness gates, one decode step profiled on the RX 7900 XTX, MTP speculation, the GFX11 PRIV bug and the experiments we killed.'
	},
	rail: 'Chapters',
	chapter: 'Chapter',
	sources: 'Sources',
	illustr: 'illustration',
	measured: 'measured',
	replay: 'Replay',
	pause: 'Pause',
	play: 'Play',
	reset: 'Reset',
	step: 'Step',
	ch: [
		{
			id: 'question',
			nav: 'The question',
			kicker: 'The question',
			title: 'Same card. Same model file. How much can software alone do?',
			lead: 'We do not change the quantisation, swap in a smaller model or buy new hardware. The only variable is the engine that runs the model. And one hard rule: the answer must be just as good.'
		},
		{
			id: 'measure',
			nav: 'Honest measurement',
			kicker: 'Honest measurement',
			title: 'First we learned not to fool ourselves.',
			lead: 'The card heats up, clocks drift, and a single run can lie by a few percent. The gain from one patch is often smaller than that noise. So every change is measured with the same script on both sides, on fresh servers, in ABBA order.'
		},
		{
			id: 'quality',
			nav: 'Lossless',
			kicker: 'Lossless or nothing',
			title: 'Faster, but not a single token different.',
			lead: 'A speed-up that damages the answer is not a speed-up. Every change goes through gates: the md5 of the answer, GPU op tests against the CPU and, when the summation order has to change, KL divergence against upstream’s own noise.'
		},
		{
			id: 'step',
			nav: 'Where the time goes',
			kicker: 'Where the time goes',
			title: 'One decode step under the microscope.',
			lead: 'Before we speed anything up, we take the step apart kernel by kernel. This is a real rocprofv3 trace from the RX 7900 XTX: 946 kernels, three bursts and the gaps where the GPU waits for the CPU.'
		},
		{
			id: 'speculation',
			nav: 'Speculation',
			kicker: 'Speculation, explained',
			title: 'Guess a few tokens ahead. Check them all at once.',
			lead: 'A big model reads all of its weights on every step, whether it computes one token or five. So a small MTP head proposes a few tokens ahead and the model checks them in one step. It keeps the matching prefix, drops the rest and adds one token of its own. The text is exactly what the model would have written anyway.'
		},
		{
			id: 'metal',
			nav: 'Down to the metal',
			kicker: 'Down to the metal',
			title: 'One register bit that kept crashing the card.',
			lead: 'Our engine records the sequence of kernels and replays it as a tape of PM4 commands, skipping the expensive launch path. Fast, but every so often the GPU died with a page fault at address 0. We chased the cause down to a single bit.'
		},
		{
			id: 'negative',
			nav: 'What we killed',
			kicker: 'Negative results',
			title: 'A graveyard of ideas. We keep it in plain sight.',
			lead: 'Most ideas do not make it. We record every one: what it promised, what we measured and why we killed it. Without that, the numbers that survived would not be worth trusting.'
		},
		{
			id: 'records',
			nav: 'Record board',
			kicker: 'Record board',
			title: 'Before and after. Same card, same model, same script.',
			lead: 'Every card × model pair we measured end to end. “Before” is a typical app with default settings, “after” is our engine.'
		}
	],
	q: {
		same: 'Unchanged',
		card: 'Card',
		model: 'Model',
		file: 'File',
		ctx: 'Quality',
		ctxV: 'the same (gates in ch. 3)',
		upstream: 'Typical app',
		ours: 'Our engine',
		live: 'Live, at the real pace',
		text: 'A graphics card is more than compute. When generating text, the model reads all of its weights for every token, so every millisecond between kernels counts, every unnecessary memory read, and every token that can be guessed early. ',
		scroll: 'Scroll to see how we measure it'
	},
	m: {
		rules: [
			['ABBA', 'We interleave variants A, B, B, A. Card drift (temperature, clocks) then lands equally on both sides.'],
			['Fresh server', 'Every arm starts from scratch: no warm cache, no traces of the previous variant.'],
			['Seeds and prompts', 'spec_sweep: 6 prompts (PL and EN, prose, tech, code) × 3 seeds. Median, not the best run.'],
			['ms per step', 'The time of one step decides, because at T=1 tokens per second also depend on the sampled text.'],
			['Same script', 'Upstream and our engine are measured with the same tool, on the same machine, with the same flags.'],
			['A/A threshold', 'Two runs of the same variant differ by 0.09% ms/step (median of 15 pairs). A smaller “gain” is noise.']
		],
		labTitle: 'Drift lab',
		labLead: 'A and B are the same program, so the true difference is zero. The card gets a little slower with every run. Click the slots to build your own order and see how much “gain” drift alone invents.',
		presets: 'Presets',
		slot: (i: number, v: string) => `Run ${i}: variant ${v}. Click to switch.`,
		drift: 'card drift',
		fake: 'Apparent difference of B vs A',
		verdictBad: 'Drift fakes a gain. This result would go in the bin.',
		verdictOk: 'Drift cancels out to zero. Only the real difference is left.',
		verdictUneven: 'A and B need the same number of runs.',
		model: 'Drift model: each run 0.4% slower than the previous one. An illustration of the principle, not a measurement.',
		tTitle: 'T=0 and T=1 in one sentence',
		t0: 'T=0: the model always takes the most likely token. The same prompt gives the same text bit for bit, so md5 hashes can be compared.',
		t1: 'T=1: the model samples the token from the distribution, as in a normal chat. The text is different every time, so we compare ms per step, not just tokens per second.',
		pick: 'Sample the next token',
		next: 'Next token after “A graphics card is…”'
	},
	l: {
		gates: 'Regression gates (greedy md5, fresh server)',
		gatesNote: 'After every change, including the PM4 fix from chapter 6, the answer hashes equal our engine’s stored reference.',
		demoTitle: 'Stream comparator',
		demoLead: 'Two token streams: the reference and the build after a change. We compare them token by token, then hash the whole answer. Try injecting an error.',
		ref: 'Reference',
		cand: 'After change',
		inject: 'Inject a rounding error',
		heal: 'Undo the error',
		hash: 'hash',
		pass: 'IDENTICAL',
		fail: 'DIVERGED',
		failNote: 'One different token changes everything after it. Such a change fails the md5 gate and goes in the bin or to the KLD gate.',
		demoNote: 'Text and hash (FNV-1a) computed in your browser, to illustrate the principle.',
		tokens: (n: number) => `${n} tokens`,
		kldTitle: 'KLD: when bit-for-bit is impossible',
		kldLead: 'Our multi-column MMVQ sums in a different order than upstream, so against upstream we do not promise identical text. We measure the KL divergence of the token distributions and put it next to upstream’s own noise (RTX 3060).',
		kldOurs: 'ours vs upstream',
		kldNoise: 'upstream noise',
		opsTitle: 'test-backend-ops: every touched op against the CPU',
		opsNote: 'Every test case passes. BITEXACT mode lets us check speculative verification bit for bit.'
	},
	s: {
		modes: ['MTP step', 'W16 step, top-k on CPU', 'W16 step, top-k on GPU'],
		wall: 'step time',
		busy: 'GPU working',
		idle: 'GPU waiting',
		gaps: 'large gaps',
		ms: 'ms',
		timeline: 'Timeline of one step (true scale)',
		burst: (n: number) => `${n} kernels`,
		gap: 'host gap',
		other: 'other',
		ops: 'Where the GPU spends its working time',
		pick: 'Pick a kernel to see its share',
		share: (p: string) => `${p} of GPU working time`,
		mmvq5: 'Matrix × vector for 5 rows at once: the token plus 4 draft tokens. This is reading weights from memory, the card’s physical limit.',
		mmvq1: 'The same for a single row at a time.',
		takeaway: 'Over 80% of the GPU’s working time (70% of the whole step) is reading weights in mmvq n5. On top of that, 4 ms where the GPU waits for the CPU. That is where we hunt for the next milliseconds.',
		w16Lead: 'For code edits we verify 16 rows at once. Two gaps then grow to almost a millisecond: the CPU copies 16 MB of logits and scans them for the top-k. We moved top-k to the GPU: 16 KB goes to the host instead of 16 MB.',
		w16Gain: 'Code edits 2.2–2.4% faster, output identical bit for bit at T=0 and T=1.'
	},
	p: {
		chat: 'Chat (MTP)',
		code: 'Code edit (W16 lookup tail)',
		draft: 'draft',
		accepted: 'accepted',
		rejected: 'rejected',
		bonus: 'from the model',
		perStep: 'tokens per step',
		steps: 'steps',
		vs: 'steps without speculation',
		auto: 'Auto',
		chatNote: (x: string) => `In chat this averages ${x} tokens per step (114.8 t/s × 27.67 ms/step). Simulated hits with that average.`,
		codeNote: (x: string, of: string) => `In code edits the lookup tail copies spans from the context: ${x} of ${of} possible tokens per step. Simulated hits with that average.`,
		chatText: 'The model checks the proposals in one step and keeps only the tokens it would have picked itself, so the text does not change.',
		codeText: 'function total(items) { return items.reduce((sum, item) => sum + item.price * item.qty, 0); }',
		speed: 'Speed on the RX 7900 XTX, Qwen3.8-27B',
		a0: 'Typical app',
		a1: 'Upstream + MTP',
		ours: 'Our engine',
		chatRow: 'Chat (spec_sweep, T=1)',
		codeRow: 'Code edit (T=0, 4 files)'
	},
	x: {
		storyTitle: 'The investigation in five steps',
		story: [
			['The tape', 'We record the step’s ~800 dispatches and replay them as PM4 DISPATCH_DIRECT packets. Kernel registers are copied from the kernel descriptor.'],
			['The symptom', 'Every so often: an SQC page fault at 0x0, many waves at once, then a GPU reset. Only on the tape, never on the normal AQL path.'],
			['The trigger', 'The driver preempts queues at random moments (SVM eviction). Waves in the middle of the tape are saved and restored by CWSR.'],
			['The cause', 'GFX11 requires COMPUTE_PGM_RSRC1.PRIV=1 on every compute dispatch (workaround DEGFX11_12113). Firmware sets it for AQL on its own; our tape took 0 from the descriptor. The fault dumps confirm it: AQL waves have priv 1, tape waves priv 0.'],
			['The fix', 'GGML_HIP_PM4_WA=2: PRIV=1, no ORDERED_APPEND, RESTART=0. Before shipping we forced evictions in the middle of the tape to prove that this was it.']
		],
		regTitle: 'COMPUTE_PGM_RSRC1',
		regLead: 'Flip bit 20 and trigger a preemption in the middle of the tape.',
		bit: 'PRIV (bit 20)',
		evict: 'Preempt the queue',
		ok: 'Waves came back after preemption. The tape keeps playing.',
		bad: 'Waves came back without privilege: page fault @0x0, GPU reset.',
		idle: 'The tape is playing. Click “Preempt the queue”.',
		resultTitle: 'After the fix',
		requests: 'production requests',
		faults: 'GPU faults',
		occTitle: 'The occupancy cliff: VGPR → waves per SIMD',
		occLead: 'On RDNA3 a SIMD has 1536 vector registers per lane, handed out in blocks of 24. The more registers a kernel uses, the fewer waves fit at once, and fewer waves mean fewer chances to hide memory latency. Move the slider.',
		vgpr: 'VGPR per kernel',
		waves: 'waves per SIMD',
		preset: (v: number) => `Q4_K ncols=5: ${v} VGPR`,
		cliff: 'The Q4_K kernel for 5 columns used 140 VGPR and got 10 waves. Capped at 119 VGPR it fits 12 waves, with no spill to memory.'
	},
	n: {
		killed: 'killed',
		stopped: 'stopped',
		open: 'Show details',
		promise: 'Promise',
		result: 'Result',
		why: 'Why it ended',
		items: [
			{
				id: 'lds',
				name: 'LDS-only barriers',
				fig: '±0.2%',
				tag: 'killed',
				promise: 'Lighter synchronisation in kernels: wait only for shared memory, not for all memory.',
				result: 'Means of two ABBA pairs: Qwen pp4096 1130.6 → 1128.8; LFM 6125 → 6139; chat 102.5 → 102.4 t/s. Bit-exact.',
				why: 'All within noise. Barriers are not the bottleneck.'
			},
			{
				id: 'oov',
				name: 'Clustered OOV draft tail',
				fig: '−1.5%',
				tag: 'killed',
				promise: 'The draft head knows 64k of 248k tokens. Add clusters for rare tokens so the draft hits more often.',
				result: '111.0 → 109.4 t/s in chat. The pricier head costs more than the extra hits give.',
				why: 'Net negative. The full-vocabulary variant also has a negative ceiling in every group.'
			},
			{
				id: 'router',
				name: 'DFlash2 router for code edits',
				fig: '+1.1%',
				tag: 'killed',
				promise: 'A second drafter that takes over steps where the lookup tail has nothing to copy.',
				result: 'Oracle ceiling (perfect choice on every step): +1.1% at T=0, +2.0% at T=1. Break-even threshold: +8%.',
				why: 'The W16 tail already takes 14.5 of 16 tokens per step. Nothing left to add. Killed without a minute of GPU time.'
			},
			{
				id: 'wide',
				name: 'MMVQ n=1, wide loads',
				fig: '−1.0%',
				tag: 'killed',
				promise: 'Fewer load instructions per iteration (18 → 12) in the single-row multiply.',
				result: 'Qwen tg128 40.86 → 40.41 t/s. md5 identical.',
				why: 'Load instruction count is not the bottleneck. Fewer instructions does not mean faster.'
			},
			{
				id: 'norm',
				name: 'Norm fusion into the GEMV prologue',
				fig: 'GPU fault',
				tag: 'stopped',
				promise: 'Measured upper bound: skipping 129 norms gives +4.6% (1.07 ms per token).',
				result: 'The first GPU test hung the PM4 tape: SQC page fault @0x0, GPU reset.',
				why: 'Hardware rule: after a fault we stop, no retries. Find the cause first, then try again.'
			}
		]
	},
	r: {
		filterAll: 'All',
		before: 'Typical app',
		after: 'Our engine',
		speed: 't/s',
		x: 'times faster',
		archive: 'Full tables, scripts and principles in the archive below',
		ctaTitle: 'See what your card can do.',
		ctaLead: 'Pick a card and a model. We show the measured result or a clearly labelled estimate.',
		cta: 'Find your card',
		cta2: 'Start the install'
	}
};

export const COPY: Record<Lang, Copy> = { pl, en };
export type MethCopy = Copy;

/** Sources per chapter (file:line), shown in the collapsible "Sources" list. */
const R = 'KERNEL/product/research';
export const CH_SOURCES: Record<string, string[]> = {
	question: ['~/qwen-opt/queue/logs/fb-qwen-U0-p1.log:2', '~/qwen-opt/queue/logs/fb-qwen-T-p1.log:2', 'app/landing/src/lib/data/models.json (raport 04 §2.3.1)'],
	measure: ['KERNEL/wiki/metody/pomiar-abba.md:10-24', `${R}/15f-agentowa-nauka.md (A/A 0,09%)`, `${R}/02-autotuning-i-agenci-kerneli.md:47-52`],
	quality: ['KERNEL/qwen-opt/STATUS-NEXT.md:15', `${R}/26-kolejka-gpu-wieczor.md:9-15`, `${R}/24m-weryfikacja-gpu.md:4,36`],
	step: [`${R}/24m-weryfikacja-gpu.md:8-20,42-49`, '~/qwen-opt/vcost/prof/off (rocprofv3, vc_trace.py)', `${R}/24k-koszt-weryfikacji.md`, `${R}/26-kolejka-gpu-wieczor.md:14`],
	speculation: [`${R}/16b-lookup-tail.md`, `${R}/24j-router-edycja.md:12`, '~/qwen-opt/queue/logs/fb-qwen-{U0,U1,T}-p1.log:2'],
	metal: [`${R}/17-gpu-page-fault.md:210-240,286,381,443`, `${R}/26-kolejka-gpu-wieczor.md:9,22`, `${R}/24n-mmvq-n5.md:16-22,43`, `${R}/24f-mmvq-i-fa.md:12`],
	negative: [`${R}/26-kolejka-gpu-wieczor.md:10-13`, `${R}/24b-skrypty-oov-analysis.md:23`, `${R}/24b-draft-pelny-slownik.md:5-7`, `${R}/24j-router-edycja.md:3`, `${R}/24f-mmvq-i-fa.md:11`, `${R}/24l-fuzja-norm.md:5-7,29`],
	records: ['app/landing/src/lib/data/cards.json', 'app/landing/src/lib/data/measurements.ts']
};
