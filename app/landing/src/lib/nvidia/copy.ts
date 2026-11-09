/**
 * Copy of the NVIDIA results page (`/pl/nvidia/`, `/en/nvidia/`).
 *
 * Words only: every number on the page is read from `src/lib/data/nvidia-cards.ts`, which carries
 * the `file:line` of each value from `product/SITE-NVIDIA.md`. The headline sentence is the one
 * from the source material (SITE-NVIDIA.md:14); the method and caveats are its §5 and §6.
 */
import { BRAND } from '$lib/brand';
import type { Lang } from '$lib/i18n';

const pl = {
	meta: {
		title: 'Wyniki NVIDIA: 11 kart, do 2× szybciej',
		description:
			'Enigma na 11 kartach NVIDIA, od RTX 2080 Ti do RTX 5090: do 2× szybciej i pełny kontekst 262 144 tokenów. Liczby, modele, licencje i gotowe ustawienia.',
		crumbs: { cards: 'Twoja karta', nvidia: 'Wyniki NVIDIA' }
	},
	hero: {
		eyebrow: '11 kart NVIDIA · od RTX 2080 Ti do RTX 5090',
		/** The headline as the source material words it (SITE-NVIDIA.md:14-15). */
		title: ['Ta sama karta, ten sam model,', 'ta sama jakość odpowiedzi.'],
		titleTail: 'Do 2× szybciej i z pełnym kontekstem 262 144 tokenów.',
		lead: 'Sprawdziliśmy Enigmę na 11 kartach NVIDIA, od RTX 2080 Ti do RTX 5090. Każde ustawienie przeszło test pełnego wypełnienia kontekstu na prawdziwej karcie.',
		statsLabel: 'Liczby, które wyróżniamy',
		stats: {
			r5090: 'RTX 5090, pełny kontekst, silnik Enigmy',
			r4090: 'RTX 4090, pełny kontekst, silnik Enigmy',
			vsllama: 'RTX 5090 wobec zwykłego llama.cpp z MTP, ten sam host',
			r3060: 'RTX 3060: 27B na 12 GB, z silnikiem Enigmy',
			ctx: 'pełny natywny kontekst Qwen3.8-27B na 24 i 32 GB'
		},
		unit: 't/s',
		ctaPrimary: 'Zobacz tabelę 11 kart',
		ctaSecondary: 'Wydanie silników CUDA'
	},
	table: {
		kicker: 'Tabela',
		title: 'Jedna tabela, jedenaście kart',
		lead: 'Trzy kolumny: co było dziś, co daje Enigma i co daje nasz silnik.',
		caption: 'Tempo pisania na kartach NVIDIA: mediana 6 promptów PL/EN przy T=1',
		cols: { card: 'Karta (VRAM)', model: 'Model', ctx: 'Kontekst', today: 'Dziś', enigma: 'Enigma', engine: 'Z silnikiem Enigmy' },
		// Mobile header labels: the full ones do not fit 375 px, and the numbers are the point.
		colsShort: { card: 'Karta', model: 'Model', ctx: 'Kontekst', today: 'Dziś', enigma: 'Enigma', engine: 'Silnik' },
		legend:
			't/s = tempo pisania, mediana 6 promptów PL/EN przy T=1 (próbkowanie jak w czacie). „Dziś” to zwykły llama.cpp z modelem, który Enigma wybierała wcześniej. „Enigma” to obecny wybór. „Z silnikiem Enigmy” to nasze silniki CUDA, dostępne dziś na Linuksie x64 (patrz zastrzeżenia).',
		note12:
			'Przy 12 GB i mniej „dziś” było innym modelem (Gemma 4 12B), dlatego bez procentów. W tym wierszu „Enigma” to Saluki 27B, a „z silnikiem Enigmy” to Bonsai 2 z głowicą MTP — dwa różne modele, nie porównujemy ich jakości.',
		note3090:
			'RTX 3090: starszy pomiar z 19–20 października dał 42,9 → 75,3 → 93,3 t/s przy kontekście 204 800, 3 seedy, kolejność ABBA. Tabela używa nowszego pomiaru z 7 listopada (262 144, 1 seed), żeby wszystkie wiersze stały w jednych warunkach. To dwa różne silniki: wtedy mierzyliśmy prototyp, dziś to, co jest w wydaniu.',
		dash: '–',
		mixSaluki: 'Saluki',
		mixBonsai: 'Bonsai 2 + MTP',
		to: 'do'
	},
	moe: {
		kicker: 'Alternatywa',
		title: 'Szybka alternatywa MoE',
		lead: 'Gdy liczy się przede wszystkim tempo, a 24 mld parametrów w trybie MoE wystarczy: cały model mieści się w VRAM, kontekst 131 072.',
		cols: { card: 'Karta', model: 'Model', ctx: 'Kontekst', tps: 'Tempo' }
	},
	models: {
		kicker: 'Modele',
		title: 'Modele i licencje',
		lead: 'Każdy model z linkiem do plików. Licencje sprawdzone na Hugging Face 8 listopada 2026.',
		cols: { model: 'Model', licence: 'Licencja', file: 'Plik' },
		salukiNote: 'Saluki nadaje się tylko do użytku niekomercyjnego. W wersji komercyjnej 12 GB to Bonsai 2.',
		lfmNote:
			'LFM Open 1.0 pozwala używać modelu komercyjnie firmom poniżej 10 mln USD rocznego przychodu. Powyżej tego progu potrzebna jest osobna umowa.',
		nc: 'tylko niekomercyjnie'
	},
	recipes: {
		kicker: 'Ustawienia',
		title: 'Gotowe ustawienia',
		lead: 'Te same flagi dla każdej karty, reszta zależy od ilości pamięci.',
		base: 'Wspólne dla wszystkich',
		summary: 'Dla zaawansowanych: pełna tabela ustawień',
		cols: { mem: 'Pamięć', engine: 'Silnik', flags: 'Dodatkowe flagi', env: 'Zmienne środowiska', batch: 'Batch' },
		note: 'Pełna tabela z zużyciem pamięci w szczycie jest w repozytorium projektu.'
	},
	method: {
		kicker: 'Metoda',
		title: 'Jak to osiągnęliśmy',
		lead: 'Pięć rzeczy, które razem dają te liczby. Żadna nie działa sama.',
		items: {
			mtp: {
				title: 'Spekulacja MTP dobrana do karty',
				body: 'Qwen3.8-27B ma wbudowaną głowicę, która zgaduje kolejne tokeny, a model sprawdza je jednym przebiegiem. Odpowiedzi są identyczne, tylko szybciej. Najlepiej działa 2–3 tokeny naprzód, nie 4.'
			},
			ctx: {
				title: 'Pełny kontekst bez marnowania pamięci',
				body: 'Zwykły llama.cpp rezerwuje około 1 GB na bufor spekulacji, który nigdy się nie wykonuje. Nasza poprawka zwalnia tę pamięć. To ona pozwala zmieścić 262 144 tokenów na 24 GB i ponad 200 000 na 16 GB.'
			},
			kvq: {
				title: 'Nasz kernel atencji kvq',
				body: 'Czyta skwantyzowany kontekst bez kopiowania go do pełnej precyzji. Oszczędza pamięć (4090: 0,5 GB mniej przy 64k), dzięki czemu długi kontekst w ogóle się mieści. Przy długich rozmowach pisze też szybciej (3090 przy 64k: 102,5 → 112,2 t/s).'
			},
			model: {
				title: 'Najlepszy model dla każdej ilości pamięci',
				body: '27B działa nawet na kartach 11–12 GB dzięki 2-bitowemu Bonsai 2 z doszczepioną głowicą MTP.'
			},
			real: {
				title: 'Każde ustawienie sprawdzone na prawdziwej karcie',
				body: 'Z pełnym wypełnieniem kontekstu, nie wyliczone z kalkulatora.'
			}
		}
	},
	caveats: {
		kicker: 'Zastrzeżenia',
		title: 'Co trzeba wiedzieć o tych liczbach',
		lead: 'Te warunki zmieniają wynik. Podajemy je w całości, nie w przypisie na dole.',
		items: {
			linux: {
				title: 'Kolumna „z silnikiem Enigmy” to Linux x64',
				body: 'Silniki są opublikowane w wydaniu enigma-engines-cuda-2026-11-07 i aplikacja pobiera je sama. Na Windows i macOS Enigma używa zwykłego llama.cpp, czyli wartości z kolumny „Enigma”. Silników dla Windows jeszcze nie budowaliśmy.'
			},
			power: {
				title: 'Limity mocy wynajętych kart',
				body: '4090 była przycięta do 250 W (domyślnie 450 W), 3090 do 340 W, 5060 Ti do 160 W, a 3060 do 140 W. Liczby 4090 są więc zaniżone względem karty na pełnej mocy. Wszystko zmierzone na wynajętej karcie.'
			},
			seeds: {
				title: 'Jeden seed na pomiar',
				body: 'Pomiar z 7 listopada to 1 seed × 6 promptów. Porównania silników na 5090 robiliśmy naprzemiennie (A-B-B-A) na tym samym hoście.'
			},
			fork16: {
				title: 'Fork CUDA dla 16 GB nie jest wybierany',
				body: 'Zmierzony tylko na 5060 Ti: 49,4 t/s przy kontekście 196 608. Do codziennego użytku na 16 GB zostaje wariant z tabeli ustawień.'
			},
			saluki: {
				title: 'Saluki jest tylko niekomercyjny',
				body: 'Licencja CC BY-NC 4.0. W wersji komercyjnej 12 GB to Bonsai 2.'
			},
			bonsai: {
				title: 'Bonsai 2 to inna kwantyzacja',
				body: 'To 2-bitowa kwantyzacja Qwen3.8-27B, więc jakość jest niższa niż 4-bitowego modelu na większych kartach. Nie porównujemy jakości między klasami pamięci.'
			}
		}
	},
	release: {
		kicker: 'Wydanie',
		title: 'Silniki CUDA są w wydaniu',
		body: 'Kolumna „z silnikiem Enigmy” powstała na silnikach z wydania enigma-engines-cuda-2026-11-07. Aplikacja pobiera je sama, nic nie trzeba kompilować.',
		cta: 'Otwórz wydanie na GitHubie'
	},
	links: {
		cards: 'Wszystkie karty NVIDIA z pomiarami',
		methodology: 'Jak mierzymy',
		results: 'Wyniki pomiarów',
		amd: 'Referencja AMD: RX 7900 XTX 24 GB — szczegóły na stronie wyników AMD'
	},
	/* The banner on `/pl/karty/nvidia/`, pointing at this page. */
	fromCards: {
		kicker: 'Pełny kontekst',
		text: 'Wyniki NVIDIA: 11 kart, pełny kontekst',
		body: 'Jedna tabela od RTX 2080 Ti do RTX 5090, modele, licencje i gotowe ustawienia.',
		cta: 'Otwórz stronę wyników'
	}
} as const;

const en = {
	meta: {
		title: 'NVIDIA results: 11 cards, up to 2× faster',
		description:
			'Enigma on 11 NVIDIA cards, from RTX 2080 Ti to RTX 5090: up to 2× faster and the full 262 144-token context. Numbers, models, licences and ready settings.',
		crumbs: { cards: 'Your card', nvidia: 'NVIDIA results' }
	},
	hero: {
		eyebrow: '11 NVIDIA cards · RTX 2080 Ti to RTX 5090',
		title: ['Same card, same model,', 'same answer quality.'],
		titleTail: 'Up to 2× faster and with the full 262 144-token context.',
		lead: 'We checked Enigma on 11 NVIDIA cards, from RTX 2080 Ti to RTX 5090. Every setting passed a full-context fill test on a real card.',
		statsLabel: 'The numbers we single out',
		stats: {
			r5090: 'RTX 5090, Qwen3.8-27B, full context',
			r4090: 'RTX 4090, Qwen3.8-27B, full context',
			vsllama: 'RTX 5090 against plain llama.cpp with MTP, same host',
			r3060: 'RTX 3060: 27B in 12 GB of memory',
			ctx: 'full native Qwen3.8-27B context'
		},
		unit: 't/s',
		ctaPrimary: 'See the 11-card table',
		ctaSecondary: 'CUDA engine release'
	},
	table: {
		kicker: 'Table',
		title: 'One table, eleven cards',
		lead: 'Three columns: what you had, what Enigma gives and what our engine gives.',
		caption: 'Token generation on NVIDIA cards: median of 6 PL/EN prompts at T=1',
		cols: { card: 'Card (VRAM)', model: 'Model', ctx: 'Context', today: 'Today', enigma: 'Enigma', engine: 'With our engine' },
		colsShort: { card: 'Card', model: 'Model', ctx: 'Context', today: 'Today', enigma: 'Enigma', engine: 'Engine' },
		legend:
			't/s = generation speed, median of 6 PL/EN prompts at T=1 (sampling as in the chat app). “Today” is plain llama.cpp with the model Enigma used to pick. “Enigma” is the current pick. “With our engine” means our CUDA engines, available today on Linux x64 (see the caveats).',
		note12:
			'At 12 GB and below “today” was a different model (Gemma 4 12B), so there are no percentages. In that row “Enigma” is Saluki 27B and “with our engine” is Bonsai 2 with an MTP head — two different models, we do not compare their quality.',
		note3090:
			'RTX 3090: the older measurement from 19–20 October gave 42.9 → 75.3 → 93.3 t/s at a 204 800 context, 3 seeds, ABBA order. The table uses the newer 7 November measurement (262 144, 1 seed) so every row sits under the same conditions. These are two different engines: back then we measured a prototype, today it is what ships.',
		dash: '–',
		mixSaluki: 'Saluki',
		mixBonsai: 'Bonsai 2 + MTP',
		to: 'to'
	},
	moe: {
		kicker: 'Alternative',
		title: 'A fast MoE alternative',
		lead: 'When speed is what matters and 24 billion parameters in MoE mode are enough: the whole model fits in VRAM, context 131,072.',
		cols: { card: 'Card', model: 'Model', ctx: 'Context', tps: 'Speed' }
	},
	models: {
		kicker: 'Models',
		title: 'Models and licences',
		lead: 'Every model with a link to its files. Licences checked on Hugging Face on 8 November 2026.',
		cols: { model: 'Model', licence: 'Licence', file: 'File' },
		salukiNote: 'Saluki is for non-commercial use only. For commercial work on 12 GB, use Bonsai 2.',
		lfmNote:
			'The LFM Open 1.0 licence allows commercial use by companies under $10M annual revenue. Above that threshold a separate agreement is needed.',
		nc: 'non-commercial only'
	},
	recipes: {
		kicker: 'Settings',
		title: 'Ready-made settings',
		lead: 'The same flags on every card; the rest depends on how much memory you have.',
		base: 'Shared by every card',
		summary: 'For advanced users: the full settings table',
		cols: { mem: 'Memory', engine: 'Engine', flags: 'Extra flags', env: 'Environment', batch: 'Batch' },
		note: 'The full table with peak memory use is in the project repository.'
	},
	method: {
		kicker: 'Method',
		title: 'How we got there',
		lead: 'Five things that add up to these numbers. None of them works alone.',
		items: {
			mtp: {
				title: 'MTP speculation tuned to the card',
				body: 'Qwen3.8-27B has a built-in head that guesses the next tokens, and the model checks them in a single pass. Answers are identical, only faster. It works best 2–3 tokens ahead, not 4.'
			},
			ctx: {
				title: 'Full context without wasting memory',
				body: 'Plain llama.cpp reserves about 1 GB for a speculation buffer that never runs. Our fix releases that memory. It is what makes 262 144 tokens fit on 24 GB and more than 200 000 on 16 GB.'
			},
			kvq: {
				title: 'Our attention kernel, kvq',
				body: 'It reads the quantised context without copying it into full precision. That saves memory (4090: 0.5 GB less at 64k), which is what lets a long context fit at all. On long conversations it is also faster (3090 at 64k: 102.5 → 112.2 t/s).'
			},
			model: {
				title: 'The best model for each amount of memory',
				body: '27B runs even on 11–12 GB cards thanks to the 2-bit Bonsai 2 with a grafted MTP head.'
			},
			real: {
				title: 'Every setting checked on a real card',
				body: 'With a full context fill, not calculated from a spreadsheet.'
			}
		}
	},
	caveats: {
		kicker: 'Caveats',
		title: 'What you need to know about these numbers',
		lead: 'These conditions change the result. We list all of them, not in a footnote.',
		items: {
			linux: {
				title: 'The “with our engine” column is Linux x64',
				body: 'The engines are published in the enigma-engines-cuda-2026-11-07 release and the app downloads them itself. On Windows and macOS Enigma uses plain llama.cpp, which means the values in the “Enigma” column. We have not built the engines for Windows yet.'
			},
			power: {
				title: 'Power limits of the rented cards',
				body: 'The 4090 was capped at 250 W (450 W by default), the 3090 at 340 W, the 5060 Ti at 160 W and the 3060 at 140 W. The 4090 numbers are therefore lower than the card at full power. Everything was measured on a rented card.'
			},
			seeds: {
				title: 'One seed per measurement',
				body: 'The 7 November measurement is 1 seed × 6 prompts. Engine comparisons on the 5090 were run in alternating order (A-B-B-A) on the same host.'
			},
			fork16: {
				title: 'The 16 GB CUDA fork is not picked',
				body: 'Measured only on the 5060 Ti: 49.4 t/s at a 196 608 context. For everyday use on 16 GB the variant from the settings table stays.'
			},
			saluki: {
				title: 'Saluki is non-commercial only',
				body: 'CC BY-NC 4.0 licence. For commercial work on 12 GB, use Bonsai 2.'
			},
			bonsai: {
				title: 'Bonsai 2 is a different quantisation',
				body: 'It is a 2-bit quantisation of Qwen3.8-27B, so quality is lower than the 4-bit model on bigger cards. We do not compare quality across memory classes.'
			}
		}
	},
	release: {
		kicker: 'Release',
		title: 'The CUDA engines are out',
		body: 'The “with our engine” column was measured on the engines from the enigma-engines-cuda-2026-11-07 release. The app downloads them itself; nothing to compile.',
		cta: 'Open the release on GitHub'
	},
	links: {
		cards: 'All NVIDIA cards with measurements',
		methodology: 'How we measure',
		results: 'Measurement results',
		amd: 'AMD reference: RX 7900 XTX 24 GB — details on the AMD results page'
	},
	fromCards: {
		kicker: 'Full context',
		text: 'NVIDIA results: 11 cards, full context',
		body: 'One table from RTX 2080 Ti to RTX 5090, models, licences and ready settings.',
		cta: 'Open the results page'
	}
} as const;

export const nvidiaCopy = { pl, en } as const;
export type NvidiaCopy = (typeof nvidiaCopy)[Lang];
