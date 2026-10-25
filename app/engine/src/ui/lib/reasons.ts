/**
 * Catalog codes in `Option.why[]` and `Recommendation.rejected[].reason`, and optimisation codes in
 * `Candidate.reason` ("code" or "code:value", split on the first ':') rendered as sentences.
 * Unknown codes are shown as they are.
 */
import { num, pct, type Lang } from './i18n';

type Render = (v: string, lang: Lang) => string;

const tps = (v: string, lang: Lang) => num(Number(v), lang, 1);
const gib = (v: string, lang: Lang) => num(Number(v), lang, 1);
const tok = (v: string, lang: Lang) => new Intl.NumberFormat(lang === 'pl' ? 'pl-PL' : 'en-GB').format(Number(v));
/** "11-14" -> "11–14". */
const range = (v: string) => v.replace('-', '–');
/** "<head>/<rest>" (split on the first '/'). */
function split2(v: string): [string, string] {
	const i = v.indexOf('/');
	return i < 0 ? [v, ''] : [v.slice(0, i), v.slice(i + 1)];
}
/** Minutes to read `tokens` at "<lo>-<hi>" t/s: "11–18". */
function fillMinutes(tps: string, tokens: string): string {
	const [lo = 0, hi = 0] = tps.split('-').map(Number);
	const n = Number(tokens);
	return lo > 0 && hi > 0 ? `${Math.round(n / hi / 60)}–${Math.round(n / lo / 60)}` : '?';
}

const WHY: Record<string, Record<Lang, Render>> = {
	quality_best: { pl: () => 'Najlepsza jakość, która się mieści.', en: () => 'The best quality that fits.' },
	speed_measured: {
		pl: (v, l) => `Zmierzyliśmy ${tps(v, l)} t/s pisania na takiej karcie (oficjalny llama.cpp).`,
		en: (v, l) => `We measured ${tps(v, l)} t/s writing speed on this card (official llama.cpp).`
	},
	speed_estimated: {
		pl: (v, l) => `Szacunek: ok. ${tps(v, l)} t/s pisania, z przepustowości pamięci.`,
		en: (v, l) => `Estimate: about ${tps(v, l)} t/s writing speed, from memory bandwidth.`
	},
	mtp_head: {
		pl: () => 'Model ma głowicę MTP; optymalizacja spróbuje zgadywania kilku tokenów naprzód.',
		en: () => 'The model has an MTP head; optimisation will try drafting a few tokens ahead.'
	},
	mtp_no_memory: {
		pl: () => 'Model ma głowicę MTP, ale przy tym kontekście brakuje pamięci na kontekst draftu (bez spekulacji MTP).',
		en: () => 'The model has an MTP head, but its draft context does not fit at this context (no MTP speculation).'
	},
	moe_fast: {
		pl: () => 'Mieszanka ekspertów: na każdy token pracuje mała część parametrów, więc pisze szybko.',
		en: () => 'Mixture of experts: only a small part of the parameters works per token, so it writes fast.'
	},
	ctx_model_max: { pl: () => 'Kontekst to maksimum, które obsługuje model.', en: () => 'The context is the maximum the model supports.' },
	ctx_memory_limit: { pl: () => 'Kontekst ograniczony dostępną pamięcią.', en: () => 'The context is limited by the available memory.' },
	kv_q8_0: { pl: () => 'Pamięć kontekstu skompresowana do q8_0 (praktycznie bez straty).', en: () => 'Context memory compressed to q8_0 (practically lossless).' },
	kv_q4_0: { pl: () => 'Pamięć kontekstu skompresowana do q4_0, żeby zmieścić długi kontekst.', en: () => 'Context memory compressed to q4_0 to fit a long context.' },
	kv_f16: { pl: () => 'Pamięć kontekstu bez kompresji (f16).', en: () => 'Context memory uncompressed (f16).' },
	ub512_for_ctx: {
		pl: () => 'Mniejsza paczka prefill (512) daje więcej kontekstu; czytanie trochę wolniejsze, pisanie bez zmian.',
		en: () => 'A smaller prefill batch (512) buys more context; reading is a little slower, writing is unchanged.'
	},
	unified_memory: {
		pl: () => 'Pamięć wspólna (Apple): budżet to część RAM, którą macOS daje grafice.',
		en: () => 'Unified memory (Apple): the budget is the part of the RAM macOS gives the GPU.'
	},
	windows_reserve: { pl: () => 'Zostawiamy zapas pamięci dla kompozytora Windows.', en: () => 'We leave memory headroom for the Windows compositor.' },
	no_dgpu_ram: {
		pl: () => 'Nie masz osobnej karty graficznej, więc model liczy się w pamięci RAM.',
		en: () => 'You have no separate graphics card, so the model runs from system RAM.'
	},
	igpu_backend: {
		pl: (v) => `Liczy grafika zintegrowana (${v === 'vulkan' ? 'Vulkan' : v.toUpperCase()}). Czytanie promptu zwykle idzie jej szybciej niż samemu procesorowi (tego nie mierzyliśmy); pisanie i tak ogranicza przepustowość RAM.`,
		en: (v) => `The integrated graphics computes (${v === 'vulkan' ? 'Vulkan' : v.toUpperCase()}). It usually reads the prompt faster than the processor alone (we have not measured this); writing is limited by the RAM bandwidth either way.`
	},
	cpu_igpu_pool: {
		pl: (v, l) => `Liczy procesor (CPU): grafika zintegrowana może użyć najwyżej ${gib(v, l)} GB RAM, a ten model z kontekstem potrzebuje więcej.`,
		en: (v, l) => `The processor (CPU) computes: the integrated graphics may use at most ${gib(v, l)} GB of RAM, and this model with its context needs more.`
	},
	cpu_only: {
		pl: () => 'Brak karty graficznej: liczy procesor (CPU).',
		en: () => 'No graphics card: the processor (CPU) computes.'
	},
	speed_ram_moe: {
		pl: (v, l) => {
			const [a, r] = split2(v);
			return `Wybraliśmy model MoE (${num(Number(a), l, Number(a) % 1 ? 1 : 0)}B aktywnych), bo na pamięci RAM tylko taki pisze z sensowną prędkością (szacunek ${range(r)} t/s).`;
		},
		en: (v, l) => {
			const [a, r] = split2(v);
			return `We chose an MoE model (${num(Number(a), l, Number(a) % 1 ? 1 : 0)}B active), because from RAM only such a model writes at a usable speed (estimate ${range(r)} t/s).`;
		}
	},
	speed_ram_dense: {
		pl: (v, l) => {
			const [p, r] = split2(v);
			return `Wybraliśmy mały model (${num(Number(p), l, Number(p) % 1 ? 1 : 0)}B), bo na pamięci RAM tylko małe modele i MoE piszą z sensowną prędkością (szacunek ${range(r)} t/s).`;
		},
		en: (v, l) => {
			const [p, r] = split2(v);
			return `We chose a small model (${num(Number(p), l, Number(p) % 1 ? 1 : 0)}B), because from RAM only small and MoE models write at a usable speed (estimate ${range(r)} t/s).`;
		}
	},
	prefill_ram: {
		pl: (v, l) => {
			const [r, n] = split2(v);
			return `Czytanie długiego tekstu jest tu wolne: szacunek ${range(r)} t/s. Wypełnienie ${tok(n, l)} tokenów kontekstu zajmie ok. ${fillMinutes(r, n)} min; krótkie pytanie dostaje odpowiedź po kilku sekundach.`;
		},
		en: (v, l) => {
			const [r, n] = split2(v);
			return `Reading long text is slow here: estimate ${range(r)} t/s. Filling ${tok(n, l)} tokens of context takes about ${fillMinutes(r, n)} min; a short question is answered within seconds.`;
		}
	},
	ram_reserve: {
		pl: (v, l) => {
			const [keep, budget] = split2(v);
			return `Zostawiamy ${gib(keep, l)} GB RAM dla systemu i programów; model ma do dyspozycji ${gib(budget, l)} GB.`;
		},
		en: (v, l) => {
			const [keep, budget] = split2(v);
			return `We keep ${gib(keep, l)} GB of RAM for the system and your programs; the model gets ${gib(budget, l)} GB.`;
		}
	},
	gpu_faster: {
		pl: (v) => `Z kartą graficzną 16–24 GB ten model pisałby ${range(v)}× szybciej (nasze pomiary na takich kartach).`,
		en: (v) => `With a 16–24 GB graphics card this model would write ${range(v)}× faster (our measurements on such cards).`
	},
	tight_memory: {
		pl: () => 'Mało zapasu: zostaje mniej niż 3% pamięci, więc stawiamy ten wariant niżej (system i Twoje programy dzielą ten sam RAM).',
		en: () => 'Little headroom: under 3% of the memory stays free, so we rank this option lower (the system and your programs share the same RAM).'
	},
	license_conditional: {
		pl: () => 'Licencja LFM: użycie komercyjne do 10 mln USD przychodu rocznie.',
		en: () => 'LFM licence: commercial use up to USD 10 million annual revenue.'
	}
};

const REJECTED: Record<string, Record<Lang, Render>> = {
	ctx_max_below_min: {
		pl: (v, l) => `Model obsługuje najwyżej ${tok(v, l)} tokenów kontekstu.`,
		en: (v, l) => `The model supports at most ${tok(v, l)} tokens of context.`
	},
	weights_too_big: {
		pl: (v, l) => {
			const [need = '', budget = ''] = v.split('/');
			return `Wagi się nie mieszczą: potrzeba ${gib(need, l)} GB, jest ${gib(budget, l)} GB.`;
		},
		en: (v, l) => {
			const [need = '', budget = ''] = v.split('/');
			return `The weights do not fit: needs ${gib(need, l)} GB, ${gib(budget, l)} GB available.`;
		}
	},
	ctx_below_min: {
		pl: (v, l) => `W pamięci mieści się tylko ${tok(v, l)} tokenów kontekstu.`,
		en: (v, l) => `Only ${tok(v, l)} tokens of context fit in memory.`
	},
	engine_too_old: {
		pl: (v) => `Oficjalny llama.cpp w wersji ${v} jeszcze nie obsługuje tego modelu.`,
		en: (v) => `Official llama.cpp ${v} does not support this model yet.`
	},
	too_slow_on_this_hw: {
		pl: (v, l) => `Za wolny na tym sprzęcie: szacunek ok. ${tps(v, l)} t/s pisania (wymagamy co najmniej 8 t/s).`,
		en: (v, l) => `Too slow on this hardware: about ${tps(v, l)} t/s writing speed estimated (we require at least 8 t/s).`
	}
};

/** Optimisation candidates (`Candidate.reason`); `slower_than` gets the other candidate's label. */
const CANDIDATE: Record<string, Record<Lang, Render>> = {
	no_enigma_engine: {
		pl: (v) => `Dla tej platformy (${v}) nie ma jeszcze silnika Enigma; zostaje oficjalny llama.cpp.`,
		en: (v) => `There is no Enigma engine for this platform (${v}) yet; the official llama.cpp stays.`
	},
	enigma_no_profile: {
		pl: (v) => `Silnik Enigma nie ma jeszcze profilu dla modelu ${v}.`,
		en: (v) => `The Enigma engine has no profile for ${v} yet.`
	},
	enigma_not_published: {
		pl: (v) => `Silnik ${v} nie jest jeszcze opublikowany.`,
		en: (v) => `Engine ${v} is not published yet.`
	},
	ub_no_fit: {
		pl: (v) => `Z paczką ${v} pełny kontekst nie mieści się w pamięci.`,
		en: (v) => `With a batch of ${v} the full context does not fit in memory.`
	},
	no_mtp_head: { pl: () => 'Ten model nie ma głowicy MTP.', en: () => 'This model has no MTP head.' },
	engine_no_mtp: { pl: () => 'Ten silnik nie obsługuje MTP.', en: () => 'This engine does not support MTP.' },
	engine_no_lookup: { pl: () => 'Ten silnik nie obsługuje lookup.', en: () => 'This engine does not support lookup.' },
	ctx_not_fit: { pl: () => 'Pełny kontekst się nie zmieścił.', en: () => 'The full context did not fit.' },
	prefill_loss: {
		pl: (v, l) => `Czytanie zmieniło się o ${pct(Number(v), l)} (dopuszczamy −5 %, a −15 % przy pisaniu szybszym o 20 %+).`,
		en: (v, l) => `Reading changed by ${pct(Number(v), l)} (we allow −5%, or −15% when writing is 20%+ faster).`
	},
	decode_not_faster: {
		pl: (v, l) => `Pisanie nie jest szybsze niż punkt wyjścia (${pct(Number(v), l)}).`,
		en: (v, l) => `Writing is not faster than the starting point (${pct(Number(v), l)}).`
	},
	gain_too_small: {
		pl: (v, l) => `Zysk ${pct(Number(v), l)} jest za mały, żeby zmieniać tekst odpowiedzi (wymagamy co najmniej +3 %).`,
		en: (v, l) => `A ${pct(Number(v), l)} gain is too small to change the answer text (we require at least +3%).`
	},
	slower_than: { pl: (v) => `Wolniej niż „${v}”.`, en: (v) => `Slower than “${v}”.` },
	oom: { pl: () => 'Zabrakło pamięci.', en: () => 'Out of memory.' },
	start_failed: { pl: (v) => `Serwer nie wystartował: ${v}`, en: (v) => `The server did not start: ${v}` },
	failed: { pl: (v) => `Błąd: ${v}`, en: (v) => `Error: ${v}` }
};

function render(table: Record<string, Record<Lang, Render>>, code: string, lang: Lang, mapValue?: (key: string, v: string) => string): string {
	const i = code.indexOf(':');
	const key = i < 0 ? code : code.slice(0, i);
	const value = i < 0 ? '' : code.slice(i + 1);
	const r = table[key];
	return r ? r[lang](mapValue ? mapValue(key, value) : value, lang) : code;
}

export const whyText = (code: string, lang: Lang) => render(WHY, code, lang);
export const rejectedText = (code: string, lang: Lang) => render(REJECTED, code, lang);
export const candidateText = (code: string, lang: Lang, labelOf: (id: string) => string) =>
	render(CANDIDATE, code, lang, (key, v) => (key === 'slower_than' ? labelOf(v) : v));
