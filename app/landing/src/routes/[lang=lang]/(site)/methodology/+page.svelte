<script lang="ts">
	import { onMount } from 'svelte';
	import { BRAND } from '$lib/brand';
	import { CARDS, KLD_EXCEPTIONS, M, MD5, MODEL_INFO, SHEET, variantLabel, variantOf, type Run, type RunView, type VariantKey } from '$lib/data/measurements';
	import { ETA, L1_MTP_BAND, TOK_PER_WORD } from '$lib/estimator';
	import { fmtGB, fmtRatio, localizeDecimals, ratioDigits } from '$lib/format';
	import { reveal } from '$lib/fx/actions';
	import { currentLang, href, num } from '$lib/i18n';

	const lang = $derived(currentLang());
	const rows = Object.values(M);
	const nvidia = CARDS.filter((c) => c.vendor === 'nvidia');
	const nvidiaRuns = nvidia.reduce((n, c) => n + c.runs.length, 0);
	const Q = SHEET.correctness.quality;
	const md5Same = SHEET.lfmFormats5060.filter((f) => f.md5Same);
	const MD5_SRC = 'KERNEL/qwen-opt/STATUS-NEXT.md:15';
	/** Hero specimen: the headline comparison (RTX 3090, Qwen, same script), shown with everything attached to it. */
	const spec = (() => {
		const card = CARDS.find((c) => c.id === 'rtx-3090');
		const run = card?.runs.find((r) => r.model === 'qwen38');
		const ours = run && variantOf(run, run.ours)?.decode;
		const before = run && variantOf(run, run.before)?.decode;
		return card && run && ours && before ? { card, run, ours, before } : null;
	})();

	/** Decimals as printed in the source (38.9 → 1, 28.07 → 2); speeds keep at least one (78 → 78,0). */
	const dec = (v: number) => Math.min(2, (String(v).split('.')[1] ?? '').length);
	const f = (v: number) => num(v, lang, dec(v));
	const tps = (v: number) => num(v, lang, Math.max(1, dec(v)));
	/** One source line when every lane cites the same file:line, otherwise per lane. */
	const oneSrc = (ls: { v: { src: string } }[]) => (ls.every((l) => l.v.src === ls[0].v.src) ? ls[0].v.src : null);
	const kld = (v: number) => num(v, lang, 5);
	const cardName = (id: string) => CARDS.find((c) => c.id === id)?.name ?? id;

	/** Runs measured outside the consolidated sheet (own campaign report) with no KLD figure yet. */
	const noKld = nvidia.flatMap((card) =>
		card.runs.filter((r) => !r.src.startsWith(SHEET.source) && !(r.model in Q)).map((run) => ({ card, run, src: run.src }))
	);
	/** Source of a sheet-vs-scorecard check: the run's own decode line (sheet or campaign report) and the scorecard. */
	function checkSrc(k: (typeof SHEET.checks)[number]) {
		const run = CARDS.find((c) => c.id === k.card)?.runs.find((r) => r.model === k.model);
		const v = run && variantOf(run, k.variant as VariantKey)?.decode;
		return `${v?.src ?? SHEET.source} · ${k.file}`;
	}
	/** Sheet ratios print prefix style (×1.51); the site uses suffix style (1,51×) everywhere. */
	const suffixX = (s: string) => localizeDecimals(s.replace(/\*\*/g, '').replace(/×(\d+(?:\.\d+)?)/g, '$1×'), lang);
	function gainParts(run: RunView) {
		const g = run.gain!;
		const text = run.gainText?.[lang] ?? g.text;
		return (['flags', 'engine', 'total'] as const).map((k, i) => {
			const n = g[k];
			const s = (text[i] ?? '').replace(/\*\*/g, '').trim();
			const rest = s.replace(/^×\d+(?:\.\d+)?\s*/, '').replace(/^\((.*)\)$/, '$1').trim();
			if (n) return { k, v: fmtRatio(n.v, lang), why: rest ? suffixX(rest) : null, hot: k === 'total' && n.v > 1 };
			return { k, v: '—', why: s && s !== '—' ? suffixX(s) : null, hot: false };
		});
	}

	/** Columns per run: typical app → best upstream flags → our engine, plus Prism PTQ1_0 for Bonsai. */
	function lanes(run: Run) {
		const keys: VariantKey[] = [run.before, run.flags, run.ours];
		if (variantOf(run, 'alt')) keys.push('alt');
		const list = keys
			.filter((k, i) => keys.indexOf(k) === i)
			.map((k) => ({ key: k, v: variantOf(run, k)?.decode }))
			.filter((x): x is { key: VariantKey; v: NonNullable<typeof x.v> } => !!x.v);
		const max = Math.max(...list.map((x) => x.v.v));
		return list.map((x) => ({ ...x, p: x.v.v / max, tone: x.key === run.ours ? 'hot' : x.key === run.before ? 'cold' : x.key === 'alt' ? 'alt' : 'warm' }));
	}

	const t = $derived(
		{
			pl: {
				eyebrow: 'Metodologia',
				title: 'Metodologia i surowe liczby',
				lead: `Każda liczba wydajności na stronie ${BRAND.name} pochodzi stąd: skrypt, wersja silnika, ustawienia i plik źródłowy z numerem linii. Nie zaokrąglamy w górę i nie ekstrapolujemy.`,
				stats: [
					{ v: String(CARDS.length), k: 'zmierzone karty' },
					{ v: String(nvidiaRuns), k: 'par karta × model w chmurze' },
					{ v: String(rows.length), k: 'pomiarów w laboratorium (RX 7900 XTX)' }
				],
				statLine: 'plik:linia przy każdej liczbie',
				anatomy: 'Anatomia jednej liczby',
				a: { card: 'Karta', model: 'Model', mode: 'Tryb', script: 'Skrypt', cond: 'Warunki', src: 'Źródło' },
				toc: 'Na tej stronie',
				s: ['Zasady', 'Maszyny testowe', 'Karty NVIDIA (chmura, 16.10.2026)', 'Poprawność: KLD i md5', 'Surowe pomiary RX 7900 XTX', 'Skrypty pomiarowe', 'Estymator na stronie', 'Czego jeszcze nie zmierzyliśmy'],
				rules: [
					'Ten sam model, ta sama kwantyzacja, ten sam kontekst. Zmiana kwantyzacji to osobna rekomendacja z osobnym opisem jakości.',
					'Porównujemy wyniki tego samego skryptu pomiarowego. Gdy zestawiamy wartości z różnych skryptów, piszemy to przy liczbie.',
					'Mediana, nie najlepszy przebieg. Przedziały podajemy, gdy pochodzą z naprzemiennych pomiarów A/B.',
					'Zysk uznajemy dopiero powyżej szumu z testu A/A (|Δ| > 2σ). Inaczej: „brak istotnej zmiany”.',
					'Bez porównań z innymi aplikacjami, dopóki nie zmierzymy ich tym samym narzędziem na tej samej maszynie.'
				],
				lab: 'Laboratorium',
				labLine: 'AMD Radeon RX 7900 XTX (RDNA3, gfx1100, 24 GB, 960 GB/s), AMD Ryzen 7 5700X, Linux 6.8, ROCm 10.0 oraz Vulkan (Mesa RADV). Limit mocy karty i temperatury opisane w NOTES.md.',
				cloud: 'Chmura (wynajęte karty)',
				cloudLead: 'Trzy karty NVIDIA zmierzone 16.10.2026 tym samym skryptem we wszystkich trybach. Tryby: typowa aplikacja (upstream llama.cpp z ustawieniami domyślnymi), najlepsze flagi upstream, nasz silnik z tymi samymi flagami.',
				method: 'Metoda',
				speed: 'Generowanie, tokeny na sekundę (mediana)',
				conditions: 'Warunki',
				checksTitle: 'Rozbieżności arkusza z zestawieniem',
				gain: { flags: 'Z flag upstream', engine: 'Z naszego silnika', total: 'Razem' },
				gibNote: 'Zestawienie podaje tu GiB; pokazujemy jako GB, tak jak producent opisuje pamięć karty.',
				origin: 'Źródło',
				originBody: 'raport kampanii tego modelu, nie zbiorcze zestawienie; liczby sprawdzone z jego scorecard.json.',
				noKld: 'KLD jeszcze nie zmierzone. Greedy md5 naszego silnika różni się od upstreamu (łatki forka), więc dla tego modelu nie mamy jeszcze pomiaru jakości.',
				checksLead: 'Zestawienie porównujemy automatycznie z surowymi wynikami (scorecard.json). Tam, gdzie różnią się bardziej niż zaokrągleniem, mówimy to wprost; na stronie stoi wartość z zestawienia.',
				check: (card: string, model: string, variant: string, sheet: string, sc: string) => `${card}, ${model}, ${variant}: zestawienie ${sheet}, scorecard ${sc}.`,
				checksNone: 'Brak rozbieżności ponad zaokrąglenie.',
				claim: 'Ten sam model, ta sama jakość — zmierzone',
				diff: 'Zwykły tryb greedy naszego silnika nie daje dokładnie tego samego tekstu co upstream, na wszystkich kartach i modelach zbiorczego zestawienia. Przyczyny to wielokolumnowe MMVQ (łatki 0001/0002), a u Qwena także fuzja prologu GDN (0013). Dlatego nie twierdzimy „bit w bit”, tylko mierzymy jakość dywergencją KL (KLD) wobec upstreamu.',
				kldLead: 'Na RTX 3060 KLD naszego silnika wobec upstreamu mieści się w szumie samego upstreamu:',
				kldOurs: 'nasz vs upstream',
				kldNoise: 'szum upstreamu',
				md5Same: (files: string) => `Wyjątek: LFM na RTX 5060 Ti w formatach ${files} daje md5 identyczne z upstreamem.`,
				md5: 'Greedy md5 to u nas test regresji, nie dowód zgodności z upstreamem: po instalacji 70 łatek na RX 7900 XTX skróty odpowiedzi (świeży serwer) są równe zapisanemu wzorcowi naszego silnika.',
				md5Note: 'Spekulacja MTP daje inny tekst zachłanny niż dekodowanie bez niej. To zachowanie llama.cpp, także upstream; tryb spekulacji piszący dokładnie to samo co dekodowanie bez niej jest w badaniach (raport 12).',
				kld: 'Zmiany na RX 7900 XTX przyjęte bramką KLD zamiast md5:',
				head: ['Pomiar', 'Wartość', 'Silnik i ustawienia', 'Skrypt i metoda', 'Źródło'],
				harness: {
					serve_bench: 'serve_bench.py: llama-server, czat, temp 0, 256 tokenów, 3 przebiegi na prompt, mediana, rozgrzewka.',
					spec_sweep: 'spec_sweep: 6 promptów (PL proza / technika / kod, EN czat / technika / kod) × 3 seedy, T=1, świeży serwer na wariant; metryką rozstrzygającą jest ms/krok.',
					'llama-bench': 'llama-bench z llama.cpp: -fa 1, tg128 (generowanie 128 tokenów bez spekulacji) i pp4096 (przetwarzanie promptu), 2 powtórzenia.',
					long_ctx_bench: 'long_ctx_bench: dekodowanie przy długim kontekście (1,7k–94k tokenów), T=0.',
					unspecified: 'nie podano w notatkach; liczba służy tylko jako ilustracja.'
				},
				est: [
					`Pamięć: M = wagi + KV·kontekst + logity 0,5 GiB + 3 KiB·kontekst + narzut 0,25–0,6 GiB; zapas 1 GiB jak llama.cpp --fit. Wzór trafia ±0,1% na Qwen i LFM (raport 04 §2.2.4).`,
					`Prędkość przed: η · przepustowość / bajty na token. η gęste ${num(ETA.dense.lo, lang, 2)}–${num(ETA.dense.hi, lang, 2)}, MoE ${num(ETA.moe.lo, lang, 2)}–${num(ETA.moe.hi, lang, 2)}, z porównania naszych pomiarów z modelem przepustowości (raport 04 §2.2.4).`,
					`Po L1 (tylko modele ze zmierzoną spekulacją MTP): ${num(L1_MTP_BAND.lo, lang, ratioDigits(L1_MTP_BAND.lo))}–${fmtRatio(L1_MTP_BAND.hi, lang)} (PLAN §2). Na kartach, których nie zmierzyliśmy, to szacunek.`,
					`Słowa: ${num(TOK_PER_WORD.pl, lang, 2)} tokenu na słowo po polsku, ${num(TOK_PER_WORD.en, lang, 2)} po angielsku (tokenizer Qwen3; raport 06 §2.1.2).`,
					'Przepustowość kart: wartości oznaczone w raporcie 04 §2.1.6 jako zweryfikowane; pozostałe ze specyfikacji producenta i tak oznaczone w wyniku.'
				],
				tryForm: 'Wypróbuj formularz sprzętu',
				notYet: [
					'Ollama i LM Studio z ustawieniami domyślnymi tym samym skryptem na RX 7900 XTX (eksperyment E1). Na RTX 3090 tryb „typowa aplikacja” daje tyle samo co Ollama (w nawiasie w zestawieniu).',
					'Inne karty NVIDIA i AMD: w kolejce pomiarów. Do tego czasu formularz sprzętu pokazuje szacunek z naszego wzoru, oznaczony jako szacunek.',
					'Windows i macOS: nie mierzyliśmy.',
					'Noc L2 na komputerach użytkowników: brak pomiarów, więc brak obietnic.',
					'Przedziały ufności z naprzemiennego A/B dla liczb z laboratorium: notatki podają mediany, nie przedziały.'
				],
				src: 'źródło'
			},
			en: {
				eyebrow: 'Methodology',
				title: 'Methodology and raw numbers',
				lead: `Every performance number on the ${BRAND.name} website comes from here: script, engine version, settings and the source file with its line number. We do not round up and we do not extrapolate.`,
				stats: [
					{ v: String(CARDS.length), k: 'cards measured' },
					{ v: String(nvidiaRuns), k: 'card × model pairs in the cloud' },
					{ v: String(rows.length), k: 'lab measurements (RX 7900 XTX)' }
				],
				statLine: 'file:line next to every number',
				anatomy: 'Anatomy of one number',
				a: { card: 'Card', model: 'Model', mode: 'Mode', script: 'Script', cond: 'Conditions', src: 'Source' },
				toc: 'On this page',
				s: ['Principles', 'Test machines', 'NVIDIA cards (cloud, 16 Oct 2026)', 'Correctness: KLD and md5', 'Raw RX 7900 XTX measurements', 'Measurement scripts', 'The website estimator', 'What we have not measured yet'],
				rules: [
					'Same model, same quantisation, same context. Changing the quantisation is a separate recommendation with its own quality note.',
					'We compare results from the same measurement script. When we put values from different scripts side by side, we say so next to the number.',
					'Median, not the best run. We give ranges when they come from alternating A/B measurements.',
					'A gain counts only above the noise of an A/A test (|Δ| > 2σ). Otherwise: “no significant change”.',
					'No comparisons with other apps until we measure them with the same tool on the same machine.'
				],
				lab: 'Lab',
				labLine: 'AMD Radeon RX 7900 XTX (RDNA3, gfx1100, 24 GB, 960 GB/s), AMD Ryzen 7 5700X, Linux 6.8, ROCm 10.0 and Vulkan (Mesa RADV). Power limit and temperatures are documented in NOTES.md.',
				cloud: 'Cloud (rented cards)',
				cloudLead: 'Three NVIDIA cards measured on 16 Oct 2026 with the same script in every mode. Modes: typical app (upstream llama.cpp with default settings), best upstream flags, our engine with the same flags.',
				method: 'Method',
				speed: 'Generation, tokens per second (median)',
				conditions: 'Conditions',
				checksTitle: 'Where the sheet and the scorecard disagree',
				gain: { flags: 'From upstream flags', engine: 'From our engine', total: 'Total' },
				gibNote: 'The sheet gives GiB here; shown as GB, the way the vendor labels the card memory.',
				origin: 'Source',
				originBody: 'this model’s campaign report, not the consolidated sheet; figures cross-checked against its scorecard.json.',
				noKld: 'KLD not measured yet. Our engine’s greedy md5 differs from upstream (fork patches), so there is no quality measurement for this model yet.',
				checksLead: 'We cross-check the sheet against the raw results (scorecard.json) automatically. Where they differ by more than rounding, we say so plainly; the site shows the sheet value.',
				check: (card: string, model: string, variant: string, sheet: string, sc: string) => `${card}, ${model}, ${variant}: sheet ${sheet}, scorecard ${sc}.`,
				checksNone: 'No disagreements beyond rounding.',
				claim: 'Same model, same quality — measured',
				diff: 'In plain greedy mode our engine does not produce exactly the same text as upstream, on every card and model in the consolidated sheet. The causes are multi-column MMVQ (patches 0001/0002) and, for Qwen, the fused GDN prologue (0013). So we do not claim “bit-for-bit”; we measure quality with KL divergence (KLD) against upstream.',
				kldLead: 'On the RTX 3060 the KLD of our engine against upstream stays within upstream’s own noise:',
				kldOurs: 'ours vs upstream',
				kldNoise: 'upstream noise',
				md5Same: (files: string) => `Exception: LFM on the RTX 5060 Ti in the ${files} formats gives an md5 identical to upstream.`,
				md5: 'For us, greedy md5 is a regression test, not proof of identity with upstream: after installing the 70 patches on the RX 7900 XTX the answer hashes (fresh server) equal our engine’s stored reference.',
				md5Note: 'MTP speculation yields different greedy text than plain decoding. This is llama.cpp behaviour, upstream included; a speculation mode that writes exactly what plain decoding writes is in research (report 12).',
				kld: 'Changes on the RX 7900 XTX accepted through the KLD gate instead of md5:',
				head: ['Measurement', 'Value', 'Engine and settings', 'Script and method', 'Source'],
				harness: {
					serve_bench: 'serve_bench.py: llama-server, chat, temp 0, 256 tokens, 3 runs per prompt, median, warm-up.',
					spec_sweep: 'spec_sweep: 6 prompts (PL prose / tech / code, EN chat / tech / code) × 3 seeds, T=1, fresh server per variant; the deciding metric is ms/step.',
					'llama-bench': 'llama.cpp’s llama-bench: -fa 1, tg128 (generating 128 tokens without speculation) and pp4096 (prompt processing), 2 repetitions.',
					long_ctx_bench: 'long_ctx_bench: decoding at long context (1.7k–94k tokens), T=0.',
					unspecified: 'not stated in the notes; the number is used as an illustration only.'
				},
				est: [
					'Memory: M = weights + KV·context + logits 0.5 GiB + 3 KiB·context + 0.25–0.6 GiB overhead; 1 GiB headroom like llama.cpp --fit. The formula is within ±0.1% on Qwen and LFM (report 04 §2.2.4).',
					`Speed before: η · bandwidth / bytes per token. η dense ${num(ETA.dense.lo, lang, 2)}–${num(ETA.dense.hi, lang, 2)}, MoE ${num(ETA.moe.lo, lang, 2)}–${num(ETA.moe.hi, lang, 2)}, from comparing our measurements with the bandwidth model (report 04 §2.2.4).`,
					`After L1 (only models with measured MTP speculation): ${num(L1_MTP_BAND.lo, lang, ratioDigits(L1_MTP_BAND.lo))}–${fmtRatio(L1_MTP_BAND.hi, lang)} (PLAN §2). On cards we have not measured this is an estimate.`,
					`Words: ${num(TOK_PER_WORD.pl, lang, 2)} tokens per word in Polish, ${num(TOK_PER_WORD.en, lang, 2)} in English (Qwen3 tokenizer; report 06 §2.1.2).`,
					'Card bandwidth: values marked verified in report 04 §2.1.6; the rest from vendor specs and labelled as such in the result.'
				],
				tryForm: 'Try the hardware form',
				notYet: [
					'Ollama and LM Studio with default settings using the same script on the RX 7900 XTX (experiment E1). On the RTX 3090 the “typical app” mode gives the same as Ollama (in brackets in the sheet).',
					'Other NVIDIA and AMD cards: in the measurement queue. Until then the hardware form shows an estimate from our formula, labelled as an estimate.',
					'Windows and macOS: not measured.',
					'L2 night tuning on user machines: no measurements, so no promises.',
					'Confidence intervals from alternating A/B for the lab numbers: the notes give medians, not intervals.'
				],
				src: 'source'
			}
		}[lang]
	);
	/** Section ids are linked from other pages; keep them stable (prerender fails on a missing id). */
	const ids = ['rules', 'machine', 'cloud', 'correctness', 'raw', 'scripts', 'estimator', 'not-yet'];
	const harnesses = ['serve_bench', 'spec_sweep', 'llama-bench', 'unspecified'] as const;
	const two = (i: number) => String(i + 1).padStart(2, '0');

	let active = $state('rules');
	onMount(() => {
		const els = ids.map((id) => document.getElementById(id)).filter((e): e is HTMLElement => !!e);
		const io = new IntersectionObserver(
			(entries) => {
				for (const e of entries) if (e.isIntersecting) active = e.target.id;
			},
			{ rootMargin: '-30% 0px -60% 0px' }
		);
		els.forEach((e) => io.observe(e));
		return () => io.disconnect();
	});
</script>

<svelte:head>
	<title>{t.title} · {BRAND.name}</title>
	<meta name="description" content={t.lead} />
</svelte:head>

<article class="page heat-scope">
	<header class="hero container">
		<div class="hero-text">
			<p class="eyebrow">{t.eyebrow}</p>
			<h1 class="giga title">{t.title}</h1>
			<p class="lede">{t.lead}</p>
		</div>
		{#if spec}
			<figure class="spec" use:reveal aria-labelledby="spec-cap">
				<figcaption id="spec-cap" class="eyebrow">{t.anatomy}</figcaption>
				<div class="spec-top">
					<p class="spec-fig"><span class="spec-num mono">{tps(spec.ours.v)}</span><span class="spec-u mono">t/s</span><span class="spec-x speedup">{fmtRatio(spec.ours.v / spec.before.v, lang)}</span></p>
					<div class="spec-bar" style="--b:{spec.before.v / spec.ours.v}" aria-hidden="true">
						<i class="cold"></i><i class="hot"></i>
					</div>
					<div class="spec-legend" style="--b:{spec.before.v / spec.ours.v}">
						<p class="spec-was mono"><span class="k">{variantLabel(spec.run, spec.run.before)[lang]}</span>{tps(spec.before.v)} t/s</p>
						<p class="spec-now mono"><span class="k">{variantLabel(spec.run, spec.run.ours)[lang]}</span>{tps(spec.ours.v)} t/s</p>
					</div>
				</div>
				<dl class="spec-dl">
					<div><dt>{t.a.card}</dt><dd>{spec.card.name}</dd></div>
					<div><dt>{t.a.model}</dt><dd>{MODEL_INFO[spec.run.model].name} {spec.run.quant}</dd></div>
					<div><dt>{t.a.mode}</dt><dd>{variantLabel(spec.run, spec.run.ours)[lang]}</dd></div>
					<div><dt>{t.a.script}</dt><dd>{spec.run.metric[lang]}</dd></div>
					<div><dt>{t.a.cond}</dt><dd>{spec.run.conditions[lang]}</dd></div>
					<div class="hl"><dt>{t.a.src}</dt><dd class="mono">{spec.ours.src}</dd></div>
				</dl>
			</figure>
		{/if}
		<dl class="stats">
			{#each t.stats as s (s.k)}
				<div><dt>{s.k}</dt><dd class="mono">{s.v}</dd></div>
			{/each}
			<div class="stat-line"><dt class="sr-only">{t.src}</dt><dd>{t.statLine}</dd></div>
		</dl>
	</header>

	<div class="container layout">
		<nav class="toc" aria-labelledby="toc-title">
			<h2 id="toc-title" class="eyebrow">{t.toc}</h2>
			<ol>
				{#each t.s as s, i (s)}
					<li><a href="#{ids[i]}" class:on={active === ids[i]} aria-current={active === ids[i] ? 'location' : undefined}><span class="mono">{two(i)}</span>{s}</a></li>
				{/each}
			</ol>
		</nav>

		<div class="body">
			<section id="rules" class="sec" aria-labelledby="h-rules">
				<h2 id="h-rules" class="sec-h"><span class="no mono">01</span>{t.s[0]}</h2>
				<ol class="rules">{#each t.rules as r, i (r)}<li><span class="mono">{two(i)}</span><p>{r}</p></li>{/each}</ol>
			</section>

			<section id="machine" class="sec" aria-labelledby="h-machine">
				<h2 id="h-machine" class="sec-h"><span class="no mono">02</span>{t.s[1]}</h2>
				<div class="machines">
					<div class="mach">
						<p class="eyebrow">{t.lab}</p>
						<p>{t.labLine}</p>
					</div>
					<div class="mach">
						<p class="eyebrow">{t.cloud}</p>
						<ul>
							{#each nvidia as c (c.id)}
								<li><strong>{c.name}</strong> <span class="mute">{c.arch} · {c.vramGB} GB</span><span class="fine">{c.hwLine?.[lang]}</span><span class="source">{c.hwSrc}</span></li>
							{/each}
						</ul>
					</div>
				</div>
			</section>

			<section id="cloud" class="sec" aria-labelledby="h-cloud">
				<h2 id="h-cloud" class="sec-h"><span class="no mono">03</span>{t.s[2]}</h2>
				<p class="intro">{t.cloudLead}</p>
				<p class="method"><span class="k">{t.method}</span> {nvidia[0].runs[0].metric[lang]} <span class="source">{SHEET.method.decode}</span></p>

				<div class="cards">
					{#each nvidia as c (c.id)}
						<article class="gpu" use:reveal aria-labelledby="gpu-{c.id}">
							<header class="gpu-head">
								<p class="gpu-short mono" aria-hidden="true">{c.short}</p>
								<div>
									<h3 id="gpu-{c.id}" class="gpu-name">{c.name}</h3>
									<p class="mute small">{c.arch} · {c.vramGB} GB · {f(c.bwGBs.v)} GB/s · {f(c.powerW.v)} W</p>
								</div>
							</header>
							{#each c.runs as run (run.model)}
								{@const ls = lanes(run)}
								{@const shared = oneSrc(ls)}
								{@const ours = variantOf(run, run.ours)}
								<div class="run">
									<div class="run-head">
										<h4>{MODEL_INFO[run.model].name} <span class="quant mono">{run.quant}</span></h4>
										{#if ours?.vram}
											{@const g = fmtGB(ours.vram.v, ours.vram.unit, lang)}
											<span class="unit mono">VRAM {g.text}{#if g.binary}<span class="sr-only"> ({t.gibNote})</span><sup aria-hidden="true">*</sup>{/if}</span>
										{/if}
									</div>
									<p class="sr-only">{t.speed}</p>
									<ul class="lanes">
										{#each ls as l, i (l.key)}
											<li class="lane {l.tone}" style="--p: {l.p}; --d: {i * 90}ms">
												<span class="lab">{variantLabel(run, l.key)[lang]}</span>
												<span class="track" aria-hidden="true"><i></i></span>
												<span class="val mono">{tps(l.v.v)}{#if l.v.paren !== undefined}<span class="paren"> ({f(l.v.paren)})</span>{/if}</span>
												{#if !shared}<span class="source lsrc">{l.v.src}</span>{/if}
											</li>
										{/each}
									</ul>
									{#if shared}<p class="source">{shared}</p>{/if}
									{#if run.gain}
										<dl class="gain">
											{#each gainParts(run) as gp (gp.k)}
												<div class:total={gp.hot}><dt>{t.gain[gp.k]}</dt><dd class="mono">{gp.v}</dd>{#if gp.why}<dd class="why">{gp.why}</dd>{/if}</div>
											{/each}
										</dl>
										<p class="source">{run.gain.src}</p>
									{/if}
									<p class="fine cond"><span class="k">{t.conditions}</span> {run.conditions[lang]} <span class="source">{run.conditionsSrc}</span></p>
									{#if run.note}<p class="run-note">{run.note[lang]}</p>{/if}
									{#if ours?.vram && fmtGB(ours.vram.v, ours.vram.unit, lang).binary}<p class="fine"><sup aria-hidden="true">*</sup> {t.gibNote} <span class="source">{ours.vram.src}</span></p>{/if}
									{#if !run.src.startsWith(SHEET.source)}<p class="fine origin"><span class="k">{t.origin}</span> {t.originBody} <span class="source">{run.src}</span></p>{/if}
								</div>
							{/each}
						</article>
					{/each}
				</div>

				<div class="checks" role="note" aria-labelledby="checks-h">
					<h3 id="checks-h" class="eyebrow">{t.checksTitle}</h3>
					<p>{t.checksLead}</p>
					{#if SHEET.checks.length}
						<ul>
							{#each SHEET.checks as k (k.card + k.model + k.variant)}
								<li>
									<strong>{t.check(cardName(k.card), MODEL_INFO[k.model as keyof typeof MODEL_INFO]?.name ?? k.model, k.variant.toUpperCase(), f(k.sheet), f(k.scorecard))}</strong>
									<span class="source">{checkSrc(k)}</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="mute">{t.checksNone}</p>
					{/if}
				</div>
			</section>

			<section id="correctness" class="sec" aria-labelledby="h-correct">
				<h2 id="h-correct" class="sec-h"><span class="no mono">04</span>{t.s[3]}</h2>
				<div id="quality" class="claim">
					<p class="claim-t">{t.claim}</p>
					<p>{t.diff}</p>
					<p class="source">{SHEET.correctness.md5Diff}</p>
					<p>{t.kldLead}</p>
					<div class="kld" role="list">
						{#each [['Saluki 27B', Q.saluki], ['Ternary Bonsai 2 27B', Q.bonsai]] as const as [name, q] (name)}
							<div class="kld-row" role="listitem">
								<p class="kld-m">{name} <span class="mute">· RTX 3060</span></p>
								<p class="kld-v"><span class="mono big">{kld(q.ours.v)}</span><span class="k">{t.kldOurs}</span></p>
								<p class="kld-v"><span class="mono big mute">{kld(q.noise.v)}</span><span class="k">{t.kldNoise}</span></p>
								<p class="source">{q.ours.src}</p>
							</div>
						{/each}
					</div>
					{#if md5Same.length}
						<p>{t.md5Same(md5Same.map((x) => x.file.replace(/\s*\(.*\)$/, '')).join(lang === 'pl' ? ' i ' : ' and '))} <span class="source">{md5Same.map((x) => x.kld.src).join('; ')}</span></p>
					{/if}
					{#each noKld as r (r.card.id + r.run.model)}
						<p class="nokld"><strong>{MODEL_INFO[r.run.model].name} · {r.card.name}:</strong> {t.noKld} <span class="source">{r.src}</span></p>
					{/each}
				</div>

				<div class="prose sub">
					<p>{t.md5}</p>
					<ul class="md5">
						<li><span>Qwen3.8-27B plain</span><code>{MD5.qwenPlain}…</code></li>
						<li><span>Qwen3.8-27B MTP</span><code>{MD5.qwenMtp}…</code></li>
						<li><span>LFM2.5-24B-A2B</span><code>{MD5.lfm}…</code></li>
					</ul>
					<p class="source">{MD5_SRC}</p>
					<p>{t.md5Note}</p>
					<p>{t.kld}</p>
					<ul class="exc">{#each KLD_EXCEPTIONS as k (k.source)}<li><strong>{k.what[lang]}</strong><span class="mono small">{k.result[lang]}</span><span class="source">{k.source}</span></li>{/each}</ul>
				</div>
			</section>

			<section id="raw" class="sec" aria-labelledby="h-raw">
				<h2 id="h-raw" class="sec-h"><span class="no mono">05</span>{t.s[4]}</h2>
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

			<section id="scripts" class="sec" aria-labelledby="h-scripts">
				<h2 id="h-scripts" class="sec-h"><span class="no mono">06</span>{t.s[5]}</h2>
				<dl class="defs">
					{#each harnesses as h (h)}<dt><code>{h}</code></dt><dd>{t.harness[h]}</dd>{/each}
				</dl>
			</section>

			<section id="estimator" class="sec" aria-labelledby="h-est">
				<h2 id="h-est" class="sec-h"><span class="no mono">07</span>{t.s[6]}</h2>
				<ul class="plain">{#each t.est as e (e)}<li>{e}</li>{/each}</ul>
				<p class="go"><a class="btn btn--secondary" href={href(lang, '/start/hardware')}>{t.tryForm} <span class="arrow" aria-hidden="true">→</span></a></p>
			</section>

			<section id="not-yet" class="sec" aria-labelledby="h-not">
				<h2 id="h-not" class="sec-h"><span class="no mono">08</span>{t.s[7]}</h2>
				<ul class="plain">{#each t.notYet as n (n)}<li>{n}</li>{/each}</ul>
			</section>
		</div>
	</div>
</article>

<style>
	.page {
		padding-bottom: var(--section-y);
		/* The hero glow extends past the viewport; clip (not hidden) keeps the sticky TOC working. */
		overflow-x: clip;
	}
	/* ---------- hero ---------- */
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
		align-items: end;
		gap: var(--sp-10) var(--sp-12);
		padding-block: clamp(3.5rem, 2.5rem + 5vw, 7rem) clamp(3rem, 2rem + 4vw, 5rem);
		position: relative;
	}
	.hero-text {
		display: grid;
		gap: var(--sp-6);
	}
	.stats {
		grid-column: 1 / -1;
	}
	/* specimen: one sourced number with everything that belongs to it */
	.spec {
		position: relative;
		margin: 0;
		display: grid;
		gap: var(--sp-3);
		padding: var(--sp-6) var(--sp-6) var(--sp-5);
		border: 1px solid transparent;
		border-radius: var(--r-xl);
		background:
			radial-gradient(70% 55% at 25% 30%, color-mix(in srgb, var(--heat-3) 16%, transparent), transparent 70%) padding-box,
			linear-gradient(var(--bg-1), var(--bg-1)) padding-box,
			linear-gradient(160deg, color-mix(in srgb, var(--heat-3) 75%, transparent), var(--line) 40%, var(--line) 70%, color-mix(in srgb, var(--heat-2) 55%, transparent)) border-box;
		box-shadow:
			var(--shadow-2),
			0 40px 110px -50px color-mix(in srgb, var(--heat-3) 85%, transparent);
	}
	.spec-top {
		display: grid;
		gap: var(--sp-3);
		margin-top: var(--sp-2);
	}
	.spec-fig {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0 var(--sp-3);
		line-height: 0.9;
	}
	.spec-num {
		font-size: clamp(3.75rem, 2.6rem + 3.8vw, 6rem);
		font-weight: 500;
		letter-spacing: -0.06em;
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.spec-x {
		margin-left: auto;
		font-size: clamp(2rem, 1.5rem + 1.6vw, 3rem);
	}
	.spec-u {
		font-size: var(--fs-sm);
		letter-spacing: 0.08em;
		color: var(--text-mute);
	}
	/* heat bar: the cold part is where the typical app stops, the rest is what our engine adds */
	.spec-bar {
		position: relative;
		height: 0.7rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.spec-bar i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		transform-origin: left;
	}
	.spec-bar .hot {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 18px color-mix(in srgb, var(--heat-3) 80%, transparent);
	}
	.spec-bar .cold {
		z-index: 1;
		right: auto;
		width: calc(var(--b) * 100%);
		background: var(--before);
		border-right: 2px solid var(--bg-1);
	}
	.spec-legend {
		display: grid;
		grid-template-columns: calc(var(--b) * 100%) 1fr;
	}
	.spec-was,
	.spec-now {
		display: grid;
		gap: 0.1rem;
		font-size: var(--fs-md);
	}
	.spec-was {
		color: var(--before);
	}
	.spec-now {
		justify-items: end;
		text-align: right;
		color: var(--accent-ink);
		font-weight: 600;
	}
	/* fields hang off a heat spine: each one is a part of the number above */
	.spec-dl {
		position: relative;
		padding-left: var(--sp-4);
	}
	.spec-dl::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		bottom: 1.1rem;
		width: 1px;
		background: linear-gradient(180deg, var(--heat-3), color-mix(in srgb, var(--heat-3) 15%, var(--line)));
	}
	.spec-dl > div {
		position: relative;
	}
	.spec-dl > div::before {
		content: '';
		position: absolute;
		left: calc(-1 * var(--sp-4));
		top: 1.1em;
		width: calc(var(--sp-4) - 0.35rem);
		height: 1px;
		background: color-mix(in srgb, var(--heat-3) 55%, var(--line));
	}
	:global(:root[data-theme='light']) .spec-x,
	:global(:root[data-theme='light']) .spec-num,
	:global(:root[data-theme='light']) .hot .val {
		background: var(--heat-large);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.spec-dl {
		margin: var(--sp-2) 0 0;
		display: grid;
		border-top: 1px solid var(--line);
	}
	.spec-dl > div {
		display: grid;
		grid-template-columns: 5.5rem minmax(0, 1fr);
		gap: var(--sp-3);
		padding: 0.55rem 0;
		border-bottom: 1px solid var(--line);
		font-size: var(--fs-xs);
		line-height: 1.45;
	}
	.spec-dl > div:last-child {
		border-bottom: 0;
	}
	.spec-dl dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
		padding-top: 0.1em;
	}
	.spec-dl dd {
		margin: 0;
		color: var(--text);
	}
	.spec-dl .hl dd {
		color: var(--text-hi);
		font-size: var(--fs-2xs);
		overflow-wrap: anywhere;
	}
	@media (prefers-reduced-motion: no-preference) {
		.spec-bar i {
			transition: transform 1.2s var(--ease-out) 0.25s;
		}
		.spec-bar .hot {
			transition-delay: 0.9s;
		}
		:global(html.js) .spec:not([data-in]) .spec-bar i {
			transform: scaleX(0);
		}
	}
	.hero::before {
		content: '';
		position: absolute;
		inset: -20% -30% auto auto;
		width: 60rem;
		height: 40rem;
		background: radial-gradient(closest-side, color-mix(in srgb, var(--text-hi) 5%, transparent), transparent);
		pointer-events: none;
		z-index: -1;
	}
	.title {
		max-width: 14ch;
	}
	.lede {
		max-width: 46ch;
	}
	.stats {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(0, 1.2fr);
		margin: var(--sp-6) 0 0;
		border-block: 1px solid var(--line);
	}
	.stats > div {
		display: flex;
		flex-direction: column-reverse;
		justify-content: flex-end;
		gap: var(--sp-2);
		padding: var(--sp-5) var(--sp-5) var(--sp-5) 0;
	}
	.stats > div + div {
		border-left: 1px solid var(--line);
		padding-left: var(--sp-5);
	}
	.stats dd {
		margin: 0;
		font-size: clamp(2.25rem, 1.5rem + 2.4vw, 3.5rem);
		font-weight: 500;
		line-height: 1;
		letter-spacing: -0.04em;
		color: var(--text-hi);
	}
	.stats dt {
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.stats .stat-line {
		justify-content: center;
	}
	.stats .stat-line dd {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text);
		line-height: 1.6;
	}

	/* ---------- layout ---------- */
	.layout {
		display: grid;
		grid-template-columns: 14rem minmax(0, 1fr);
		gap: var(--sp-12);
		align-items: start;
		padding-top: var(--sp-12);
	}
	.toc {
		position: sticky;
		top: 6rem;
		display: grid;
		gap: var(--sp-4);
	}
	.toc ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		border-left: 1px solid var(--line);
	}
	.toc a {
		display: grid;
		grid-template-columns: 2rem 1fr;
		gap: var(--sp-1);
		padding: 0.45rem 0 0.45rem var(--sp-4);
		margin-left: -1px;
		border-left: 1px solid transparent;
		font-size: var(--fs-sm);
		line-height: 1.35;
		color: var(--text-mute);
		text-decoration: none;
		transition:
			color var(--dur-2) var(--ease-out),
			border-color var(--dur-2) var(--ease-out);
	}
	.toc a .mono {
		font-size: var(--fs-2xs);
		padding-top: 0.2em;
	}
	.toc a:hover,
	.toc a.on {
		color: var(--text-hi);
	}
	.toc a.on {
		border-left-color: var(--text-hi);
	}
	.body {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: clamp(4rem, 3rem + 3vw, 6.5rem);
		min-width: 0;
	}
	.sec {
		display: grid;
		gap: var(--sp-5);
		scroll-margin-top: 6rem;
		min-width: 0;
	}
	.sec-h {
		display: flex;
		align-items: baseline;
		gap: var(--sp-4);
		font-size: clamp(1.75rem, 1.2rem + 1.8vw, 2.75rem);
		font-weight: 720;
		letter-spacing: -0.03em;
		line-height: 1.05;
		padding-top: var(--sp-5);
		border-top: 1px solid var(--line);
	}
	.no {
		font-size: var(--fs-xs);
		font-weight: 500;
		letter-spacing: 0.08em;
		color: var(--text-mute);
		transform: translateY(-0.6em);
	}
	.intro {
		font-size: var(--fs-md);
		max-width: 44rem;
	}
	.k {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
		margin-right: 0.4em;
	}
	.source {
		display: block;
	}

	/* ---------- rules ---------- */
	.rules {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
	}
	.rules li {
		display: grid;
		grid-template-columns: 3rem 1fr;
		gap: var(--sp-3);
		padding: var(--sp-4) 0;
		border-bottom: 1px solid var(--line);
	}
	.rules li .mono {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		padding-top: 0.3em;
	}
	.rules p {
		font-size: var(--fs-md);
		color: var(--text-hi);
		max-width: 44rem;
	}

	/* ---------- machines ---------- */
	.machines {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
		gap: var(--sp-4);
	}
	.mach {
		display: grid;
		align-content: start;
		gap: var(--sp-3);
		padding: var(--sp-6);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
	}
	.mach ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-4);
	}
	.mach li strong {
		color: var(--text-hi);
		font-weight: 600;
	}
	.mach .fine {
		display: block;
		margin-top: var(--sp-1);
	}

	/* ---------- NVIDIA cards ---------- */
	.method {
		font-size: var(--fs-sm);
		color: var(--text);
		max-width: 52rem;
	}
	.cards {
		display: grid;
		gap: var(--sp-5);
		margin-top: var(--sp-3);
	}
	.gpu {
		position: relative;
		display: grid;
		gap: var(--sp-2);
		padding: var(--sp-8);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background:
			radial-gradient(90% 70% at 100% 0%, color-mix(in srgb, var(--text-hi) 4%, transparent), transparent 70%),
			var(--bg-1);
		overflow: hidden;
	}
	.gpu-head {
		display: flex;
		align-items: flex-end;
		gap: var(--sp-5);
		padding-bottom: var(--sp-5);
		border-bottom: 1px solid var(--line);
	}
	.gpu-short {
		margin: 0;
		font-size: clamp(2.75rem, 2rem + 3vw, 4.5rem);
		font-weight: 500;
		line-height: 0.85;
		letter-spacing: -0.06em;
		color: var(--text-hi);
	}
	.gpu-name {
		font-size: var(--fs-lg);
	}
	.run {
		display: grid;
		gap: var(--sp-3);
		padding-top: var(--sp-5);
	}
	.run + .run {
		border-top: 1px dashed var(--line);
		margin-top: var(--sp-3);
	}
	.run-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--sp-3);
	}
	.run-head h4 {
		font-size: var(--fs-md);
		font-weight: 620;
	}
	.quant,
	.unit {
		font-size: var(--fs-2xs);
		font-weight: 500;
		color: var(--text-mute);
		letter-spacing: 0.04em;
		margin-left: var(--sp-2);
	}
	.lanes {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.lane {
		display: grid;
		grid-template-columns: minmax(9rem, 13rem) minmax(0, 1fr) 7.5rem;
		grid-template-areas: 'lab track val' '. src src';
		align-items: center;
		gap: 0 var(--sp-4);
	}
	.lab {
		grid-area: lab;
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.track {
		grid-area: track;
		position: relative;
		height: 0.5rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		transform-origin: left;
		transform: scaleX(var(--p));
		transition: transform 1.1s var(--ease-out) var(--d);
	}
	.cold .track i {
		background: var(--before);
	}
	.warm .track i {
		background: linear-gradient(90deg, var(--heat-1), var(--heat-2));
	}
	:global(:root[data-theme='light']) .warm .track i {
		background: linear-gradient(90deg, color-mix(in srgb, var(--heat-4) 55%, var(--bg-3)), color-mix(in srgb, var(--heat-3) 65%, var(--bg-3)));
	}
	.alt .track i {
		background: repeating-linear-gradient(-45deg, var(--text-mute) 0 3px, transparent 3px 6px);
		box-shadow: inset 0 0 0 1px var(--text-mute);
	}
	.hot .track i {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 14px -2px color-mix(in srgb, var(--accent) 70%, transparent);
	}
	:global(:root[data-theme='light']) .hot .track i {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 60%, var(--heat-4));
	}
	:global(html.js) .gpu:not([data-in]) .track i {
		transform: scaleX(0);
	}
	.val {
		grid-area: val;
		text-align: right;
		font-size: var(--fs-xl);
		font-weight: 400;
		letter-spacing: -0.04em;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.cold .val {
		color: var(--before);
	}
	.hot .val {
		color: var(--accent-ink);
		font-weight: 600;
	}
	.hot .lab {
		color: var(--text-hi);
		font-weight: 600;
	}
	.paren {
		font-size: 0.55em;
		color: var(--text-mute);
		letter-spacing: 0;
	}
	.lsrc {
		grid-area: src;
		text-align: right;
		opacity: 0.85;
	}
	.gain {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		margin: var(--sp-3) 0 0;
		border-block: 1px solid var(--line);
	}
	.gain > div {
		display: grid;
		align-content: start;
		gap: var(--sp-1);
		padding: var(--sp-3) var(--sp-4) var(--sp-3) 0;
	}
	.gain > div + div {
		border-left: 1px solid var(--line);
		padding-left: var(--sp-4);
	}
	.gain dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.gain dd {
		margin: 0;
	}
	.gain dd.mono {
		font-size: var(--fs-lg);
		letter-spacing: -0.03em;
		color: var(--text-hi);
	}
	.gain .total dd.mono {
		color: var(--accent-ink);
		font-weight: 600;
	}
	.gain .why {
		font-size: var(--fs-xs);
		line-height: 1.45;
		color: var(--text-mute);
	}
	.run-note {
		font-size: var(--fs-sm);
		color: var(--text-hi);
		max-width: 52rem;
		padding: var(--sp-3) var(--sp-4);
		border-left: 2px solid var(--warn);
		background: var(--warn-soft);
		border-radius: 0 var(--r-md) var(--r-md) 0;
	}
	.origin {
		max-width: none;
		padding-left: var(--sp-3);
		border-left: 1px solid var(--line-strong);
	}
	.origin .source,
	.nokld .source {
		display: inline;
	}
	.nokld {
		padding: var(--sp-4) var(--sp-5);
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-lg);
	}
	.nokld strong {
		color: var(--text-hi);
		font-weight: 600;
	}
	.cond {
		max-width: none;
		margin-top: var(--sp-2);
	}
	.cond .source {
		display: inline;
	}
	.checks {
		display: grid;
		gap: var(--sp-3);
		padding: var(--sp-6);
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-xl);
	}
	.checks ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-3);
	}
	.checks strong {
		color: var(--text-hi);
		font-weight: 600;
	}

	/* ---------- correctness ---------- */
	.claim {
		display: grid;
		gap: var(--sp-4);
		padding: var(--sp-8);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-1);
		scroll-margin-top: 6rem;
	}
	.claim > p:not(.source) {
		max-width: 46rem;
	}
	.claim-t {
		font-size: clamp(1.5rem, 1.1rem + 1.4vw, 2.25rem);
		font-weight: 720;
		letter-spacing: -0.03em;
		line-height: 1.08;
		color: var(--text-hi);
	}
	.kld {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-4);
	}
	.kld-row {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-3) var(--sp-4);
		padding: var(--sp-5);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: var(--bg-2);
	}
	.kld-m,
	.kld-row .source {
		grid-column: 1 / -1;
	}
	.kld-m {
		color: var(--text-hi);
		font-weight: 600;
	}
	.kld-v {
		display: grid;
		gap: var(--sp-1);
	}
	.big {
		font-size: var(--fs-xl);
		font-weight: 400;
		letter-spacing: -0.03em;
		color: var(--text-hi);
	}
	.big.mute {
		color: var(--text-mute);
	}
	.sub {
		margin-top: var(--sp-3);
		max-width: 46rem;
	}
	.md5 {
		list-style: none;
		padding: 0 !important;
		display: grid;
		gap: 0;
		border-top: 1px solid var(--line);
	}
	.md5 li {
		display: flex;
		justify-content: space-between;
		gap: var(--sp-4);
		padding: var(--sp-2) 0;
		margin: 0 !important;
		border-bottom: 1px solid var(--line);
		font-size: var(--fs-sm);
	}
	.exc {
		list-style: none;
		padding: 0 !important;
		display: grid;
		gap: var(--sp-3);
	}
	.exc li {
		display: grid;
		gap: var(--sp-1);
		padding-left: var(--sp-4);
		border-left: 1px solid var(--line-strong);
		margin: 0 !important;
	}
	.exc strong {
		color: var(--text-hi);
		font-weight: 600;
	}

	/* ---------- raw table ---------- */
	.raw .cfg {
		display: block;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		font-weight: var(--fw-regular);
		margin-top: var(--sp-1);
	}
	.raw td.big {
		font-size: var(--fs-lg);
	}
	.raw td.big small {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.raw td.source {
		display: table-cell;
		min-width: 12rem;
	}

	/* ---------- scripts, estimator ---------- */
	.defs {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0;
		margin: 0;
		max-width: 52rem;
	}
	.defs dt,
	.defs dd {
		margin: 0;
		padding: var(--sp-4) 0;
		border-bottom: 1px solid var(--line);
	}
	.defs dt {
		padding-right: var(--sp-6);
	}
	.defs code {
		color: var(--text-hi);
		font-size: var(--fs-sm);
	}
	.plain {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		max-width: 48rem;
	}
	.plain li {
		padding: var(--sp-4) 0 var(--sp-4) var(--sp-6);
		border-bottom: 1px solid var(--line);
		position: relative;
	}
	.plain li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 1.45em;
		width: 0.7rem;
		height: 1px;
		background: var(--text-mute);
	}
	.go {
		margin-top: var(--sp-2);
	}

	@media (max-width: 1000px) {
		.hero {
			grid-template-columns: minmax(0, 1fr);
		}
		.layout {
			grid-template-columns: minmax(0, 1fr);
			padding-top: var(--sp-6);
		}
		.toc {
			display: none;
		}
		.stats {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
		.stats .stat-line {
			grid-column: 1 / -1;
			border-left: 0 !important;
			border-top: 1px solid var(--line);
			padding-left: 0 !important;
		}
		.machines,
		.kld {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 640px) {
		.spec-legend {
			grid-template-columns: 1fr 1fr;
		}
		.spec-was,
		.spec-now {
			font-size: var(--fs-sm);
		}
		.gpu-head {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--sp-3);
		}
		.kld-row .big {
			font-size: var(--fs-lg);
		}
		.gain > div {
			padding-right: var(--sp-2);
		}
		.gain > div + div {
			padding-left: var(--sp-2);
		}
		.gain dd.mono {
			font-size: var(--fs-md);
		}
		.stats > div {
			padding-right: var(--sp-3);
		}
		.stats > div + div {
			padding-left: var(--sp-3);
		}
		.stats dt {
			font-size: var(--fs-xs);
		}
		.gpu,
		.claim {
			padding: var(--sp-5);
		}
		.lane {
			grid-template-columns: minmax(0, 1fr) auto;
			grid-template-areas: 'lab val' 'track track' 'src src';
			gap: var(--sp-1) var(--sp-3);
		}
		.lsrc {
			text-align: left;
		}
		.defs {
			grid-template-columns: 1fr;
		}
		.defs dt {
			border-bottom: 0;
			padding-bottom: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.track i {
			transition: none;
		}
	}

	/* ---------- heat layer: section rules, numbers, highlights ---------- */
	.hero::before {
		background:
			radial-gradient(closest-side, color-mix(in srgb, var(--heat-3) 16%, transparent), transparent),
			radial-gradient(closest-side at 30% 70%, color-mix(in srgb, var(--heat-2) 10%, transparent), transparent);
	}
	.stats {
		border-image: linear-gradient(90deg, var(--heat-2), var(--heat-3) 30%, var(--line) 70%) 1;
	}
	.stats dd:not(.stat-line dd) {
		background: var(--heat-ramp-hot);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	:global(:root[data-theme='light']) .stats dd:not(.stat-line dd) {
		background: var(--heat-large);
		-webkit-background-clip: text;
		background-clip: text;
	}
	:global(:root[data-theme='light']) .gpu-short {
		background: linear-gradient(180deg, var(--text-hi) 35%, var(--heat-2));
		-webkit-background-clip: text;
		background-clip: text;
	}
	.toc a.on {
		border-left-color: var(--heat-3);
		background: linear-gradient(90deg, color-mix(in srgb, var(--heat-3) 12%, transparent), transparent 80%);
	}
	.toc a.on .mono,
	.toc a:hover .mono {
		color: var(--accent-ink);
	}
	.sec-h {
		position: relative;
		border-top-color: transparent;
	}
	.sec-h::before {
		content: '';
		position: absolute;
		top: -1px;
		left: 0;
		right: 0;
		height: 1px;
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 18%, var(--heat-4) 30%, var(--line) 55%);
	}
	.sec-h::after {
		content: '';
		position: absolute;
		top: -2px;
		left: 0;
		width: 3.5rem;
		height: 3px;
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 16px color-mix(in srgb, var(--heat-3) 80%, transparent);
	}
	.no {
		color: var(--accent-ink);
	}
	.rules li .mono {
		color: var(--accent-ink);
	}
	.rules li {
		transition: background-color var(--dur-2);
	}
	.rules li:hover {
		background: linear-gradient(90deg, color-mix(in srgb, var(--heat-3) 7%, transparent), transparent 60%);
	}
	.mach,
	.gpu,
	.claim {
		transition:
			border-color var(--dur-3) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.mach:hover,
	.gpu:hover {
		border-color: color-mix(in srgb, var(--heat-3) 55%, var(--line));
		box-shadow: 0 30px 80px -50px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.gpu {
		background:
			radial-gradient(70% 60% at 100% 0%, color-mix(in srgb, var(--heat-3) 10%, transparent), transparent 70%),
			var(--bg-1);
	}
	.gpu-short {
		background: linear-gradient(180deg, var(--text-hi) 30%, var(--heat-3));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.claim {
		border-color: color-mix(in srgb, var(--heat-3) 40%, var(--line));
		background:
			radial-gradient(80% 60% at 0% 0%, color-mix(in srgb, var(--heat-3) 11%, transparent), transparent 70%),
			var(--bg-1);
		box-shadow: 0 40px 100px -60px color-mix(in srgb, var(--heat-3) 90%, transparent);
	}
	.claim-t {
		background: linear-gradient(90deg, var(--text-hi) 45%, var(--heat-3) 80%, var(--heat-4));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	:global(:root[data-theme='light']) .claim-t {
		background: linear-gradient(90deg, var(--text-hi) 55%, var(--heat-2) 90%);
		-webkit-background-clip: text;
		background-clip: text;
	}
	.kld-row .big:not(.mute) {
		color: var(--accent-ink);
	}
	.checks {
		border-color: color-mix(in srgb, var(--heat-3) 45%, var(--line-strong));
	}
</style>
