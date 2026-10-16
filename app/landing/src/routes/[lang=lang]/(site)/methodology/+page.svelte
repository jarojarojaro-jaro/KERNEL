<script lang="ts">
	import { BRAND } from '$lib/brand';
	import cloud from '$lib/data/cloud-results.json';
	import { KLD_EXCEPTIONS, M, MD5 } from '$lib/data/measurements';
	import { ETA, L1_MTP_BAND, TOK_PER_WORD } from '$lib/estimator';
	import { currentLang, href, num } from '$lib/i18n';

	const lang = $derived(currentLang());
	const rows = Object.values(M);
	type CloudRow = { model: string; variant: string; decode_tps_median: number | null; decode_tps_min: number | null; decode_tps_max: number | null; ms_step?: number; tok_step?: number; ttft_ms_2k: number | null; vram_gb: number | null; md5_status: string; n_runs: number };
	const cloudCards = Object.values(cloud.cards as Record<string, { dir: string; rows: CloudRow[] }>);

	const t = $derived({
		pl: {
			title: 'Metodologia i surowe liczby',
			lead: `Każda liczba wydajności na stronie ${BRAND.name} pochodzi z tej tabeli. Podajemy skrypt, wersję silnika, ustawienia i plik źródłowy z numerem linii. Nie zaokrąglamy w górę i nie ekstrapolujemy.`,
			toc: 'Na tej stronie',
			s: ['Zasady', 'Maszyna testowa', 'Surowe pomiary', 'Skrypty pomiarowe', 'Poprawność: md5 i KLD', 'Chmura: karty NVIDIA', 'Estymator na stronie', 'Czego jeszcze nie zmierzyliśmy'],
			rules: [
				'Ten sam model, ta sama kwantyzacja, ten sam kontekst. Zmiana kwantyzacji to osobna rekomendacja z osobnym opisem jakości.',
				'Porównujemy wyniki tego samego skryptu pomiarowego. Gdy zestawiamy wartości z różnych skryptów, piszemy to przy liczbie.',
				'Mediana, nie najlepszy przebieg. Przedziały podajemy, gdy pochodzą z naprzemiennych pomiarów A/B.',
				'Zysk uznajemy dopiero powyżej szumu z testu A/A (|Δ| > 2σ). Inaczej: „brak istotnej zmiany”.',
				'Bez porównań z innymi aplikacjami, dopóki nie zmierzymy ich tym samym narzędziem na tej samej maszynie.'
			],
			machine: 'AMD Radeon RX 7900 XTX (RDNA3, gfx1100, 24 GB, 960 GB/s), AMD Ryzen 7 5700X, Linux 6.8, ROCm 10.0 oraz Vulkan (Mesa RADV). Limit mocy karty i temperatury opisane w NOTES.md.',
			head: ['Pomiar', 'Wartość', 'Silnik i ustawienia', 'Skrypt i metoda', 'Źródło'],
			harness: {
				serve_bench: 'serve_bench.py: llama-server, czat, temp 0, 256 tokenów, 3 przebiegi na prompt, mediana, rozgrzewka.',
				spec_sweep: 'spec_sweep: 6 promptów (PL proza / technika / kod, EN czat / technika / kod) × 3 seedy, T=1, świeży serwer na wariant; metryką rozstrzygającą jest ms/krok.',
				'llama-bench': 'llama-bench z llama.cpp: -fa 1, tg128 (generowanie 128 tokenów bez spekulacji) i pp4096 (przetwarzanie promptu), 2 powtórzenia.',
				long_ctx_bench: 'long_ctx_bench: dekodowanie przy długim kontekście (1,7k–94k tokenów), T=0.',
				unspecified: 'nie podano w notatkach; liczba służy tylko jako ilustracja.'
			},
			md5: 'Skróty md5 odpowiedzi zachłannych po instalacji (świeży serwer) są równe bazie:',
			md5Note: 'Spekulacja MTP daje inny tekst zachłanny niż dekodowanie bez niej. To zachowanie llama.cpp, także upstream; tryb bitowo identycznej spekulacji jest w badaniach (raport 12).',
			kld: 'Zmiany przyjęte przez bramkę KLD zamiast md5:',
			cloudLead: 'Kampania na wynajętych kartach NVIDIA (16.10.2026). Warianty: A0 upstream z ustawieniami domyślnymi, A1 upstream + konfiguracja L1, A2 nasz silnik z flagami A1 (PLAN-TESTOW.md). Status md5 przepisany dokładnie z zestawienia.',
			cloudNone: 'Brak gotowych zestawień.',
			cloudHead: ['Model', 'Wariant', 'Mediana t/s', 'Zakres', 'ms/krok', 'TTFT 2k', 'VRAM', 'md5', 'Przebiegi'],
			est: [
				`Pamięć: M = wagi + KV·kontekst + logity 0,5 GiB + 3 KiB·kontekst + narzut 0,25–0,6 GiB; zapas 1 GiB jak llama.cpp --fit. Wzór trafia ±0,1% na Qwen i LFM (raport 04 §2.2.4).`,
				`Prędkość przed: η · przepustowość / bajty na token. η gęste ${num(ETA.dense.lo, lang, 2)}–${num(ETA.dense.hi, lang, 2)}, MoE ${num(ETA.moe.lo, lang, 2)}–${num(ETA.moe.hi, lang, 2)}, z porównania naszych pomiarów z modelem przepustowości (raport 04 §2.2.4).`,
				`Po L1 (tylko modele ze zmierzoną spekulacją MTP): ×${num(L1_MTP_BAND.lo, lang, 1)}–${num(L1_MTP_BAND.hi, lang, 1)} (PLAN §2). Na innych kartach niż RX 7900 XTX to szacunek.`,
				`Słowa: ${num(TOK_PER_WORD.pl, lang, 2)} tokenu na słowo po polsku, ${num(TOK_PER_WORD.en, lang, 2)} po angielsku (tokenizer Qwen3; raport 06 §2.1.2).`,
				'Przepustowość kart: wartości oznaczone w raporcie 04 §2.1.6 jako zweryfikowane; pozostałe ze specyfikacji producenta i tak oznaczone w wyniku.'
			],
			notYet: [
				'Ollama i LM Studio z ustawieniami domyślnymi tym samym skryptem (eksperyment E1). Do tego czasu nie pokazujemy słupka „typowa aplikacja”.',
				'Karty NVIDIA: kampania w toku; liczby tylko z gotowych zestawień powyżej.',
				'Windows i macOS: nie mierzyliśmy.',
				'Noc L2 na komputerach użytkowników: brak pomiarów, więc brak obietnic.',
				'Przedziały ufności z naprzemiennego A/B dla liczb z tabeli: notatki podają mediany, nie przedziały.'
			]
		},
		en: {
			title: 'Methodology and raw numbers',
			lead: `Every performance number on the ${BRAND.name} website comes from this table. We list the script, engine version, settings and the source file with its line number. We do not round up and we do not extrapolate.`,
			toc: 'On this page',
			s: ['Principles', 'Test machine', 'Raw measurements', 'Measurement scripts', 'Correctness: md5 and KLD', 'Cloud: NVIDIA cards', 'The website estimator', 'What we have not measured yet'],
			rules: [
				'Same model, same quantisation, same context. Changing the quantisation is a separate recommendation with its own quality note.',
				'We compare results from the same measurement script. When we put values from different scripts side by side, we say so next to the number.',
				'Median, not the best run. We give ranges when they come from alternating A/B measurements.',
				'A gain counts only above the noise of an A/A test (|Δ| > 2σ). Otherwise: “no significant change”.',
				'No comparisons with other apps until we measure them with the same tool on the same machine.'
			],
			machine: 'AMD Radeon RX 7900 XTX (RDNA3, gfx1100, 24 GB, 960 GB/s), AMD Ryzen 7 5700X, Linux 6.8, ROCm 10.0 and Vulkan (Mesa RADV). Power limit and temperatures are documented in NOTES.md.',
			head: ['Measurement', 'Value', 'Engine and settings', 'Script and method', 'Source'],
			harness: {
				serve_bench: 'serve_bench.py: llama-server, chat, temp 0, 256 tokens, 3 runs per prompt, median, warm-up.',
				spec_sweep: 'spec_sweep: 6 prompts (PL prose / tech / code, EN chat / tech / code) × 3 seeds, T=1, fresh server per variant; the deciding metric is ms/step.',
				'llama-bench': 'llama.cpp’s llama-bench: -fa 1, tg128 (generating 128 tokens without speculation) and pp4096 (prompt processing), 2 repetitions.',
				long_ctx_bench: 'long_ctx_bench: decoding at long context (1.7k–94k tokens), T=0.',
				unspecified: 'not stated in the notes; the number is used as an illustration only.'
			},
			md5: 'Greedy answer md5 hashes after install (fresh server) equal the base:',
			md5Note: 'MTP speculation yields different greedy text than plain decoding. This is llama.cpp behaviour, upstream included; a bit-exact speculation mode is in research (report 12).',
			kld: 'Changes accepted through the KLD gate instead of md5:',
			cloudLead: 'Campaign on rented NVIDIA cards (16 Oct 2026). Variants: A0 upstream with default settings, A1 upstream + L1 configuration, A2 our engine with A1 flags (PLAN-TESTOW.md). The md5 status is copied verbatim from the scorecard.',
			cloudNone: 'No finished scorecards.',
			cloudHead: ['Model', 'Variant', 'Median t/s', 'Range', 'ms/step', 'TTFT 2k', 'VRAM', 'md5', 'Runs'],
			est: [
				'Memory: M = weights + KV·context + logits 0.5 GiB + 3 KiB·context + 0.25–0.6 GiB overhead; 1 GiB headroom like llama.cpp --fit. The formula is within ±0.1% on Qwen and LFM (report 04 §2.2.4).',
				`Speed before: η · bandwidth / bytes per token. η dense ${num(ETA.dense.lo, lang, 2)}–${num(ETA.dense.hi, lang, 2)}, MoE ${num(ETA.moe.lo, lang, 2)}–${num(ETA.moe.hi, lang, 2)}, from comparing our measurements with the bandwidth model (report 04 §2.2.4).`,
				`After L1 (only models with measured MTP speculation): ×${num(L1_MTP_BAND.lo, lang, 1)}–${num(L1_MTP_BAND.hi, lang, 1)} (PLAN §2). On cards other than the RX 7900 XTX this is an estimate.`,
				`Words: ${num(TOK_PER_WORD.pl, lang, 2)} tokens per word in Polish, ${num(TOK_PER_WORD.en, lang, 2)} in English (Qwen3 tokenizer; report 06 §2.1.2).`,
				'Card bandwidth: values marked verified in report 04 §2.1.6; the rest from vendor specs and labelled as such in the result.'
			],
			notYet: [
				'Ollama and LM Studio with default settings using the same script (experiment E1). Until then we show no “typical app” bar.',
				'NVIDIA cards: campaign in progress; numbers only from finished scorecards above.',
				'Windows and macOS: not measured.',
				'L2 night tuning on user machines: no measurements, so no promises.',
				'Confidence intervals from alternating A/B for the numbers in the table: the notes give medians, not intervals.'
			]
		}
	}[lang]);
	const ids = ['rules', 'machine', 'raw', 'scripts', 'correctness', 'cloud', 'estimator', 'not-yet'];
	const harnesses = ['serve_bench', 'spec_sweep', 'llama-bench', 'unspecified'] as const;
</script>

<svelte:head>
	<title>{t.title} · {BRAND.name}</title>
	<meta name="description" content={t.lead} />
</svelte:head>

<article class="container section page">
	<header class="head">
		<p class="overline">{lang === 'pl' ? 'Metodologia' : 'Methodology'}</p>
		<h1 class="h1">{t.title}</h1>
		<p class="lead">{t.lead}</p>
	</header>

	<nav class="toc card card--inset" aria-labelledby="toc-title">
		<h2 id="toc-title" class="overline">{t.toc}</h2>
		<ol>{#each t.s as s, i (s)}<li><a href="#{ids[i]}">{s}</a></li>{/each}</ol>
	</nav>

	<div class="body">
		<section id="rules" class="prose">
			<h2>1. {t.s[0]}</h2>
			<ol>{#each t.rules as r (r)}<li>{r}</li>{/each}</ol>
		</section>

		<section id="machine" class="prose">
			<h2>2. {t.s[1]}</h2>
			<p>{t.machine}</p>
		</section>

		<section id="raw">
			<h2 class="h3 sec">3. {t.s[2]}</h2>
			<div class="table-wrap">
				<table class="table raw">
					<thead><tr>{#each t.head as h (h)}<th scope="col">{h}</th>{/each}</tr></thead>
					<tbody>
						{#each rows as m (m.id)}
							<tr>
								<th scope="row">{m.model} <span class="mute num">{m.quant}</span><span class="cfg">{m.config[lang]}</span></th>
								<td class="num big">{num(m.value, lang, m.value >= 1000 ? 0 : 1)} <small>{m.unit}</small></td>
								<td>{m.build}<span class="cfg">{m.backend} · {m.gpu}</span></td>
								<td><span class="badge badge--plain {m.harness === 'unspecified' ? 'badge--soon' : 'badge--progress'}">{m.harness}</span><span class="cfg">{m.method[lang]}</span></td>
								<td class="source">{m.source}<br />{m.date}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>

		<section id="scripts" class="prose">
			<h2>4. {t.s[3]}</h2>
			<dl class="defs">
				{#each harnesses as h (h)}<dt><code>{h}</code></dt><dd>{t.harness[h]}</dd>{/each}
			</dl>
		</section>

		<section id="correctness" class="prose">
			<h2>5. {t.s[4]}</h2>
			<p>{t.md5}</p>
			<ul class="num">
				<li>Qwen3.8-27B plain: <code>{MD5.qwenPlain}…</code></li>
				<li>Qwen3.8-27B MTP: <code>{MD5.qwenMtp}…</code></li>
				<li>LFM2.5-24B-A2B: <code>{MD5.lfm}…</code></li>
			</ul>
			<p class="source">KERNEL/qwen-opt/STATUS-NEXT.md:15</p>
			<p>{t.md5Note}</p>
			<p>{t.kld}</p>
			<ul>{#each KLD_EXCEPTIONS as k (k.source)}<li><strong>{k.what[lang]}</strong>: {k.result[lang]} <span class="source">({k.source})</span></li>{/each}</ul>
		</section>

		<section id="cloud">
			<h2 class="h3 sec">6. {t.s[5]}</h2>
			<p class="prose">{t.cloudLead}</p>
			{#each cloudCards as card (card.dir)}
				<div class="table-wrap cloud">
					<table class="table">
						<caption>~/qwen-opt/cloud/results/{card.dir}/scorecard.json</caption>
						<thead><tr>{#each t.cloudHead as h (h)}<th scope="col">{h}</th>{/each}</tr></thead>
						<tbody>
							{#each card.rows as r (r.model + r.variant)}
								<tr>
									<th scope="row">{r.model}</th>
									<td>{r.variant}</td>
									<td class="num">{r.decode_tps_median ?? '—'}</td>
									<td class="num">{r.decode_tps_min ?? '—'}–{r.decode_tps_max ?? '—'}</td>
									<td class="num">{r.ms_step ?? '—'}</td>
									<td class="num">{r.ttft_ms_2k ?? '—'} ms</td>
									<td class="num">{r.vram_gb ?? '—'} GB</td>
									<td class="md5">{r.md5_status || '—'}</td>
									<td class="num">{r.n_runs}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="mute">{t.cloudNone}</p>
			{/each}
		</section>

		<section id="estimator" class="prose">
			<h2>7. {t.s[6]}</h2>
			<ul>{#each t.est as e (e)}<li>{e}</li>{/each}</ul>
			<p><a href={href(lang, '/start/hardware')}>{lang === 'pl' ? 'Wypróbuj formularz sprzętu' : 'Try the hardware form'} →</a></p>
		</section>

		<section id="not-yet" class="prose">
			<h2>8. {t.s[7]}</h2>
			<ul>{#each t.notYet as n (n)}<li>{n}</li>{/each}</ul>
		</section>
	</div>
</article>

<style>
	.page {
		display: grid;
		grid-template-columns: 15rem minmax(0, 1fr);
		gap: var(--sp-8) var(--sp-12);
		align-items: start;
	}
	.head {
		grid-column: 1 / -1;
		display: grid;
		gap: var(--sp-4);
		max-width: 50rem;
	}
	.toc {
		position: sticky;
		top: 5.5rem;
		padding: var(--sp-5);
	}
	.toc ol {
		margin: var(--sp-3) 0 0;
		padding-left: 1.2em;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-sm);
	}
	.toc a {
		color: var(--text);
		text-decoration: none;
	}
	.toc a:hover {
		color: var(--text-hi);
		text-decoration: underline;
	}
	.body {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--sp-12);
		min-width: 0;
	}
	.body :global(.prose h2) {
		margin-top: 0;
	}
	.sec {
		font-size: var(--fs-xl);
		margin-bottom: var(--sp-4);
	}
	.raw .cfg,
	.raw td .cfg {
		display: block;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		font-weight: var(--fw-regular);
		margin-top: var(--sp-1);
	}
	.big {
		font-size: var(--fs-lg);
		color: var(--text-hi);
	}
	.big small {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.defs {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-3) var(--sp-5);
	}
	.defs dd {
		margin: 0;
	}
	.cloud {
		margin-top: var(--sp-4);
	}
	.md5 {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		max-width: 18rem;
	}
	@media (max-width: 900px) {
		.page {
			grid-template-columns: minmax(0, 1fr);
		}
		.toc {
			position: static;
		}
		.defs {
			grid-template-columns: 1fr;
		}
	}
</style>
