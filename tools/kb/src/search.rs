//! Wyszukiwanie: BM25, gęste (e5), hybryda RRF oraz hybryda + fakty liczbowe.

use crate::analyze::{analyze, analyze_query, fold, Tok};
use crate::embed::{Embedder, Vectors};
use crate::facts::{higher_is_better, Fact};
use crate::index::{file_prior, Index};
use anyhow::{anyhow, Result};
use std::collections::{HashMap, HashSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, clap::ValueEnum)]
pub enum Mode {
    Bm25,
    Dense,
    Hybrid,
    #[value(name = "hybrid-facts")]
    HybridFacts,
    #[value(name = "bm25-facts")]
    Bm25Facts,
}

impl Mode {
    pub fn needs_dense(self) -> bool {
        matches!(self, Mode::Dense | Mode::Hybrid | Mode::HybridFacts)
    }
    pub fn name(self) -> &'static str {
        match self {
            Mode::Bm25 => "bm25",
            Mode::Dense => "dense",
            Mode::Hybrid => "hybrid",
            Mode::HybridFacts => "hybrid-facts",
            Mode::Bm25Facts => "bm25-facts",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Agg {
    Best,
    Worst,
    Max,
    Min,
}

#[derive(Debug, Default)]
pub struct Intent {
    pub agg: Option<Agg>,
    /// jednostki podane wprost (t/s, ms, KLD…) – filtr
    pub units: Vec<&'static str>,
    /// jednostki wynikające ze słów (prefill → t/s, koszt → $) – podpowiedź
    pub hint_units: Vec<&'static str>,
    /// liczby z zapytania jako przedziały [lo, hi)
    /// liczby z zapytania jako przedziały [lo, hi) z jednostką doklejoną do liczby („100%”)
    pub numbers: Vec<(f64, f64, Option<&'static str>)>,
    /// pytanie liczbowe („ile”, „wynik”) bez agregacji
    pub numeric: bool,
    /// termy treści (bez słów intencji), tylko pierwotne (bez synonimów)
    pub content: Vec<Tok>,
}

const AGG_WORDS: &[(&str, Agg)] = &[
    ("najlepsz", Agg::Best),
    ("najszybsz", Agg::Best),
    ("najszybciej", Agg::Best),
    ("rekord", Agg::Best),
    ("best", Agg::Best),
    ("fastest", Agg::Best),
    ("record", Agg::Best),
    ("peak", Agg::Best),
    ("najwolniejsz", Agg::Worst),
    ("najgorsz", Agg::Worst),
    ("slowest", Agg::Worst),
    ("worst", Agg::Worst),
    ("najwyzsz", Agg::Max),
    ("najwieksz", Agg::Max),
    ("highest", Agg::Max),
    ("largest", Agg::Max),
    ("max", Agg::Max),
    ("maks", Agg::Max),
    ("najnizsz", Agg::Min),
    ("najmniejsz", Agg::Min),
    ("lowest", Agg::Min),
    ("smallest", Agg::Min),
    ("min", Agg::Min),
];

const HINTS: &[(&str, &[&str])] = &[
    ("prefill", &["t/s"]),
    ("decode", &["t/s"]),
    ("dekod", &["t/s"]),
    ("szybk", &["t/s"]),
    ("predk", &["t/s"]),
    ("speed", &["t/s"]),
    ("throughput", &["t/s"]),
    ("tg128", &["t/s"]),
    ("pp4096", &["t/s"]),
    ("wynik", &["t/s"]),
    ("koszt", &["$", "%"]),
    ("cena", &["$"]),
    ("wydal", &["$"]),
    ("cost", &["$", "%"]),
    ("spent", &["$"]),
    ("budzet", &["$"]),
    ("budget", &["$"]),
    ("ttft", &["s", "ms"]),
    ("latency", &["ms", "s"]),
    ("opozn", &["ms", "s"]),
    ("trwa", &["s", "ms", "min"]),
    ("sekund", &["s"]),
    ("kld", &["KLD"]),
    ("ppl", &["PPL"]),
    ("vram", &["GB"]),
    ("pamiec", &["GB"]),
    ("rpm", &["RPM"]),
    ("wentylator", &["RPM", "%"]),
    ("temperatur", &["°C"]),
    ("hotspot", &["°C"]),
    ("przyspiesz", &["×", "%"]),
    ("speedup", &["×", "%"]),
    ("zysk", &["%", "×"]),
    ("traci", &["%"]),
    ("krok", &["tok/krok", "ms/krok"]),
];

static PREFILL_RE: std::sync::LazyLock<regex::Regex> =
    std::sync::LazyLock::new(|| regex::Regex::new(r"prefill|\bpp\d*\b|ttft|prompt processing|przetwarzani").unwrap());

/// ~40 znaków przed liczbą w linii (prefill w zdaniu obok liczby).
fn label_window(line: &str, raw: &str) -> String {
    let p = line.find(raw).unwrap_or(0);
    let mut s = p.saturating_sub(40);
    while !line.is_char_boundary(s) {
        s += 1;
    }
    line[s..p].to_string()
}

const NUMERIC_WORDS: &[&str] = &["ile", "how", "much", "many", "wynik", "wyniki", "result", "results", "liczba"];

pub fn parse_intent(q: &str) -> Intent {
    let mut it = Intent::default();
    let mut intent_terms: HashSet<String> = HashSet::new();
    for raw in q.split_whitespace() {
        let w = fold(raw.trim_matches(|c: char| !(c.is_alphanumeric() || "/%$×".contains(c))));
        if w.is_empty() {
            continue;
        }
        if let Some((_, a)) = AGG_WORDS.iter().find(|(p, _)| w.starts_with(p)) {
            it.agg = Some(*a);
            intent_terms.extend(analyze(&w).into_iter().map(|t| t.term));
            continue;
        }
        if NUMERIC_WORDS.contains(&w.as_str()) {
            it.numeric = true;
            intent_terms.extend(analyze(&w).into_iter().map(|t| t.term));
            continue;
        }
        let explicit = match w.as_str() {
            "t/s" | "tok/s" | "tokens/s" | "tps" => Some("t/s"),
            "ms" => Some("ms"),
            "kld" => Some("KLD"),
            "ppl" => Some("PPL"),
            "%" => Some("%"),
            "gb" | "gib" => Some("GB"),
            "rpm" => Some("RPM"),
            "$" | "usd" => Some("$"),
            "×" => Some("×"),
            "ms/krok" => Some("ms/krok"),
            "tok/krok" => Some("tok/krok"),
            _ => None,
        };
        if let Some(u) = explicit {
            it.units.push(u);
        }
        for (p, us) in HINTS {
            if w.starts_with(p) {
                it.hint_units.extend(us.iter().copied());
            }
        }
        // liczby: 130 → [130,131); 130.2 → ±0.05; „100%” → 100 z jednostką %
        // „27k”, „98k” to długości kontekstu (etykiety), nie wartości – zostają termami treści
        let (num, nunit) = match w.strip_suffix('%') {
            Some(n) => (n.replace(',', "."), Some("%")),
            None => (w.replace(',', "."), None),
        };
        if !num.is_empty() && num.chars().all(|c| c.is_ascii_digit() || c == '.') && num.matches('.').count() <= 1 && !num.starts_with('.') {
            if let Ok(v) = num.parse::<f64>() {
                let dec = num.split('.').nth(1).map_or(0, |d| d.len()) as i32;
                if dec == 0 {
                    it.numbers.push((v, v + 1.0, nunit));
                } else {
                    let h = 0.5 * 10f64.powi(-dec);
                    it.numbers.push((v - h, v + h, nunit));
                }
            }
        }
    }
    it.content = analyze_query(q).into_iter().filter(|t| t.w >= 0.5 && !intent_terms.contains(&t.term)).collect();
    if it.agg.is_some() && it.content.is_empty() {
        it.content = analyze(q);
    }
    it
}

impl Intent {
    pub fn strong(&self) -> bool {
        self.agg.is_some() || !self.numbers.is_empty() || !self.units.is_empty()
    }
    /// Filtr jednostek: wprost podane, a przy agregacji bez jednostki – podpowiedź albo t/s.
    pub fn unit_filter(&self) -> Option<Vec<&'static str>> {
        if !self.units.is_empty() {
            return Some(self.units.clone());
        }
        if self.agg.is_some() {
            return Some(if self.hint_units.is_empty() { vec!["t/s"] } else { self.hint_units.clone() });
        }
        None
    }
}

#[derive(Debug, Clone)]
pub struct FactHit {
    pub fact: usize,
    pub rel: f32,
    pub coverage: f32,
    /// te same wartość+jednostka w innych miejscach
    pub also: Vec<usize>,
}

/// Fakty pasujące do zapytania. `force_agg` nadpisuje kierunek (--max/--min).
pub fn facts_query(idx: &Index, q: &str, force_agg: Option<Agg>, force_unit: Option<&str>, k: usize) -> (Intent, Vec<FactHit>) {
    let mut it = parse_intent(q);
    if force_agg.is_some() {
        it.agg = force_agg;
    }
    let filter: Option<Vec<String>> = match force_unit {
        Some(u) => Some(vec![crate::analyze::norm_unit(u).unwrap_or(u).to_string()]),
        None => it.unit_filter().map(|v| v.iter().map(|s| s.to_string()).collect()),
    };
    let terms: Vec<(String, f32)> = it.content.iter().map(|t| (t.term.clone(), t.w * idx.idf(&t.term))).filter(|t| t.1 > 0.0).collect();
    let total: f32 = terms.iter().map(|t| t.1).sum::<f32>().max(1e-6);
    // fragmenty z którymkolwiek termem → zbiór termów w fragmencie (treść + kontekst)
    let mut chunk_terms: HashMap<u32, Vec<usize>> = HashMap::new();
    for (ti, (t, _)) in terms.iter().enumerate() {
        if let Some(p) = idx.postings.get(t) {
            for &(ci, _) in p {
                chunk_terms.entry(ci).or_default().push(ti);
            }
        }
    }
    let mut hits: Vec<FactHit> = Vec::new();
    let mut line_cache: HashMap<(u32, u32), HashSet<String>> = HashMap::new();
    let mut heading_cache: HashMap<u32, HashSet<String>> = HashMap::new();
    let candidate_chunks: Vec<u32> = if terms.is_empty() { (0..idx.chunks.len() as u32).collect() } else { chunk_terms.keys().copied().collect() };
    for ci in candidate_chunks {
        let (s, e) = idx.chunk_facts[ci as usize];
        if s == e {
            continue;
        }
        let in_chunk = chunk_terms.get(&ci);
        let c = &idx.chunks[ci as usize];
        for fi in s..e {
            let f = &idx.facts[fi as usize];
            if let Some(fl) = &filter {
                if !fl.iter().any(|u| u == &f.unit) {
                    continue;
                }
            }
            let in_range = |x: &Fact| it.numbers.iter().any(|(lo, hi, u)| x.value >= *lo && x.value < *hi && u.is_none_or(|u| u == x.unit));
            let num_match = in_range(f);
            // warunek z zapytania („przy 100%”) spełniony przez inną liczbę w tej samej linii
            let cond_match = !num_match && !it.numbers.is_empty() && idx.facts[s as usize..e as usize].iter().any(|g| g.line == f.line && in_range(g));
            if !it.numbers.is_empty() && !num_match && it.content.iter().all(|t| t.term.chars().all(|c| c.is_ascii_digit() || c == '.' || c == 'k')) {
                continue;
            }
            let line_terms = line_cache.entry((ci, f.line)).or_insert_with(|| {
                let text = c.text.lines().nth((f.line - c.start) as usize).unwrap_or("");
                analyze(text).into_iter().map(|t| t.term).collect()
            });
            let label_terms: HashSet<String> = analyze(&f.label).into_iter().map(|t| t.term).collect();
            // wiersz tabeli: sekcja (nagłówek nad tabelą) jest podmiotem wiersza, jak tekst linii
            // („## RX 7900 XTX – Qwen…” + „| code-edit | 400.9 t/s |”)
            let section_terms = if c.table_header.is_empty() {
                None
            } else {
                Some(heading_cache.entry(ci).or_insert_with(|| analyze(c.heading.rsplit(" > ").next().unwrap_or("")).into_iter().map(|t| t.term).collect::<HashSet<String>>()))
            };
            let mut rel = 0.0;
            let mut cov = 0.0;
            for (ti, (t, w)) in terms.iter().enumerate() {
                let m = if label_terms.contains(t) {
                    1.0
                } else if line_terms.contains(t) || section_terms.as_ref().is_some_and(|h| h.contains(t)) {
                    0.8
                } else if in_chunk.is_some_and(|v| v.contains(&ti)) {
                    0.55
                } else {
                    0.0
                };
                rel += w * m;
                if m > 0.0 {
                    cov += w;
                }
            }
            let mut rel = rel / total;
            let cov = if terms.is_empty() { 1.0 } else { cov / total };
            if num_match {
                rel += 1.0;
            } else if cond_match {
                rel += 0.5;
            }
            if it.hint_units.iter().any(|u| *u == f.unit) {
                rel += 0.1;
            }
            if rel <= 0.0 {
                continue;
            }
            hits.push(FactHit { fact: fi as usize, rel, coverage: cov, also: Vec::new() });
        }
    }
    let prior = |h: &FactHit| file_prior(&idx.chunk_file(idx.facts[h.fact].chunk).path);
    match it.agg {
        Some(agg) => {
            // strony pochodne (AUDYT, log, opisy kb) nie konkurują o rekord, chyba że nic innego nie ma
            if hits.iter().any(|h| prior(h) >= 0.5) {
                hits.retain(|h| prior(h) >= 0.5);
            }
            let best_cov = hits.iter().map(|h| h.coverage).fold(0.0, f32::max);
            hits.retain(|h| h.coverage >= best_cov - 1e-4);
            // rekordy najpierw ze strony rekordów, potem z notatek i raportów, na końcu z surowego researchu
            let tier = |h: &FactHit| {
                let p = &idx.chunk_file(idx.facts[h.fact].chunk).path;
                if p == "wiki/REKORDY.md" { 2 } else if file_prior(p) >= 1.0 { 1 } else { 0 }
            };
            let top_tier = hits.iter().map(tier).max().unwrap_or(0);
            hits.retain(|h| tier(h) == top_tier);
            // liczba musi być „o tym”: etykieta/linia zgodna prawie jak najlepsza
            let best_rel = hits.iter().map(|h| h.rel).fold(0.0, f32::max);
            hits.retain(|h| h.rel >= best_rel - 0.15);
            // „najszybszy X” bez słowa o prefillu = szybkość generowania: prefill/pp nie konkuruje
            if !PREFILL_RE.is_match(&fold(q)) {
                hits.retain(|h| {
                    let f = &idx.facts[h.fact];
                    let c = &idx.chunks[f.chunk as usize];
                    let line = c.text.lines().nth((f.line - c.start) as usize).unwrap_or("");
                    let lab = fold(&f.label);
                    let head = fold(c.heading.rsplit(" > ").next().unwrap_or(""));
                    !PREFILL_RE.is_match(&lab) && !PREFILL_RE.is_match(&head) && !PREFILL_RE.is_match(&fold(&label_window(line, &f.raw)))
                });
            }
            let up = |f: &Fact| match agg {
                Agg::Max => true,
                Agg::Min => false,
                Agg::Best => higher_is_better(&f.unit),
                Agg::Worst => !higher_is_better(&f.unit),
            };
            hits.sort_by(|a, b| {
                let (fa, fb) = (&idx.facts[a.fact], &idx.facts[b.fact]);
                let va = if up(fa) { -fa.value } else { fa.value };
                let vb = if up(fb) { -fb.value } else { fb.value };
                va.total_cmp(&vb).then(b.rel.total_cmp(&a.rel)).then(prior(b).total_cmp(&prior(a)))
            });
        }
        None => {
            hits.sort_by(|a, b| (b.rel * prior(b)).total_cmp(&(a.rel * prior(a))).then(a.fact.cmp(&b.fact)));
        }
    }
    // grupowanie: ta sama wartość i jednostka = jeden wynik z listą innych źródeł
    let mut grouped: Vec<FactHit> = Vec::new();
    for h in hits {
        let f = &idx.facts[h.fact];
        if let Some(g) = grouped.iter_mut().find(|g| {
            let gf = &idx.facts[g.fact];
            gf.value == f.value && gf.unit == f.unit && (g.rel - h.rel).abs() < 0.35
        }) {
            if g.also.len() < 8 {
                g.also.push(h.fact);
            }
            continue;
        }
        if grouped.len() >= k {
            continue;
        }
        grouped.push(h);
    }
    (it, grouped)
}

/// Typy notatek w wiki (foldery) wynikające z formy pytania: decyzja, przyczyna/lekcja, „jak”, „co to”.
pub struct Routing {
    boosts: Vec<(&'static str, f32)>,
}

const ROUTES: &[(&[&str], &[(&str, f32)])] = &[
    (&["decyz", "zdecyd", "wybral", "wybor", "postanow", "zasad", "decision", "decided", "decide", "rule", "wolno", "polityk"], &[("wiki/decyzje/", 1.6)]),
    (&["dlaczego", "czemu", "why", "przyczyn", "lekcj", "lesson", "skad", "powod"], &[("wiki/lekcje/", 1.3), ("wiki/eksperymenty/", 1.1)]),
    (&["jak", "how", "howto", "ustaw", "sprawdz", "kiedy"], &[("wiki/metody/", 1.25), ("wiki/narzedzia/", 1.25), ("wiki/lekcje/", 1.15)]),
    (&["co"], &[("wiki/", 1.15)]),
    (&["what"], &[("wiki/", 1.15)]),
    (&["rekord", "najlepsz", "najszybsz", "record", "best", "fastest"], &[("wiki/REKORDY.md", 1.5)]),
];

impl Routing {
    pub fn new(q: &str) -> Routing {
        let mut boosts: Vec<(&'static str, f32)> = Vec::new();
        for raw in q.split_whitespace() {
            let w = fold(raw.trim_matches(|c: char| !c.is_alphanumeric()));
            for (words, b) in ROUTES {
                let hit = words.iter().any(|p| if p.len() <= 4 { w == *p } else { w.starts_with(p) });
                if hit {
                    for (prefix, f) in b.iter() {
                        if !boosts.iter().any(|(p, _)| p == prefix) {
                            boosts.push((prefix, *f));
                        }
                    }
                }
            }
        }
        Routing { boosts }
    }

    pub fn factor(&self, path: &str) -> f32 {
        self.boosts.iter().filter(|(p, _)| path.starts_with(p)).map(|(_, f)| *f).fold(1.0, f32::max)
    }
}

#[derive(Debug, Clone)]
pub struct Hit {
    pub chunk: u32,
    pub score: f32,
    pub line: u32,
    pub fact: Option<usize>,
}

pub struct Searcher<'a> {
    pub idx: &'a Index,
    pub dense: Option<(&'a mut Embedder, &'a Vectors)>,
    pub rrf_k: f32,
    pub w_dense: f32,
    pub w_facts: f32,
}

fn env_f(name: &str, d: f32) -> f32 {
    std::env::var(name).ok().and_then(|s| s.parse().ok()).unwrap_or(d)
}

impl<'a> Searcher<'a> {
    pub fn new(idx: &'a Index, dense: Option<(&'a mut Embedder, &'a Vectors)>) -> Searcher<'a> {
        Searcher { idx, dense, rrf_k: env_f("KB_RRF_K", 60.0), w_dense: env_f("KB_W_DENSE", 1.0), w_facts: env_f("KB_W_FACTS", 1.0) }
    }
}

impl Searcher<'_> {
    pub fn search(&mut self, q: &str, mode: Mode, k: usize) -> Result<Vec<Hit>> {
        let qt = analyze_query(q);
        let bm = || self.idx.bm25(&qt, 100);
        let mut lists: Vec<(f32, Vec<u32>)> = Vec::new();
        let mut fact_line: HashMap<u32, (u32, usize)> = HashMap::new();
        if matches!(mode, Mode::Bm25 | Mode::Hybrid | Mode::HybridFacts | Mode::Bm25Facts) {
            lists.push((1.0, bm().into_iter().map(|x| x.0).collect()));
        }
        if mode.needs_dense() {
            let (emb, vecs) = self.dense.as_mut().ok_or_else(|| anyhow!("tryb {} wymaga modelu i wektorów", mode.name()))?;
            let qv = emb.embed_query(q)?;
            lists.push((self.w_dense, vecs.search(&qv, 100).into_iter().map(|x| x.0).collect()));
        }
        if matches!(mode, Mode::HybridFacts | Mode::Bm25Facts) {
            let (it, fh) = facts_query(self.idx, q, None, None, 20);
            let w = if it.strong() {
                self.w_facts
            } else if it.numeric {
                0.5 * self.w_facts
            } else if !it.hint_units.is_empty() {
                0.3 * self.w_facts
            } else {
                0.0
            };
            if w > 0.0 {
                let mut seen = HashSet::new();
                let mut l = Vec::new();
                for h in &fh {
                    for &fi in std::iter::once(&h.fact).chain(h.also.iter()) {
                        let f = &self.idx.facts[fi];
                        if seen.insert(f.chunk) {
                            fact_line.entry(f.chunk).or_insert((f.line, fi));
                            l.push(f.chunk);
                        }
                    }
                }
                lists.push((w, l));
            }
        }
        let k_rrf = if lists.len() == 1 { 0.0 } else { self.rrf_k };
        let mut s: HashMap<u32, f32> = HashMap::new();
        for (w, l) in &lists {
            for (r, &c) in l.iter().enumerate() {
                *s.entry(c).or_default() += w / (k_rrf + r as f32 + 1.0);
            }
        }
        let route = Routing::new(q);
        // BM25 już zawiera mnożnik fragmentu; gęsta lista i fakty dostają go tutaj
        let has_bm25 = matches!(mode, Mode::Bm25 | Mode::Bm25Facts | Mode::Hybrid | Mode::HybridFacts);
        let mut fused: Vec<(u32, f32)> = s
            .into_iter()
            .map(|(c, x)| {
                let prior = if has_bm25 && lists.len() == 1 { 1.0 } else { self.idx.chunk_prior(c) };
                (c, x * prior * route.factor(&self.idx.chunk_file(c).path))
            })
            .collect();
        fused.sort_by(|a, b| b.1.total_cmp(&a.1).then(a.0.cmp(&b.0)));
        // różnorodność: najwyżej `per_file` fragmentów z jednego pliku, nadmiar spada na koniec listy
        let per_file = env_f("KB_PER_FILE", 1.0) as usize;
        let mut count: HashMap<u32, usize> = HashMap::new();
        let (mut head, mut tail) = (Vec::new(), Vec::new());
        for x in fused {
            let n = count.entry(self.idx.chunks[x.0 as usize].file).or_default();
            *n += 1;
            if *n <= per_file { head.push(x) } else { tail.push(x) }
        }
        head.extend(tail);
        Ok(head
            .into_iter()
            .take(k)
            .map(|(c, score)| {
                let (line, fact) = match fact_line.get(&c) {
                    Some(&(l, fi)) => (l, Some(fi)),
                    None => (best_line(self.idx, c, &qt), None),
                };
                Hit { chunk: c, score, line, fact }
            })
            .collect())
    }
}

/// Linia fragmentu z największą sumą idf pasujących termów.
pub fn best_line(idx: &Index, ci: u32, qt: &[Tok]) -> u32 {
    let c = &idx.chunks[ci as usize];
    if c.start == c.end {
        return c.start;
    }
    let mut best = (c.start, 0.0f32);
    for (k, line) in c.text.lines().enumerate() {
        let terms: HashSet<String> = analyze(line).into_iter().map(|t| t.term).collect();
        let s: f32 = qt.iter().filter(|t| terms.contains(&t.term)).map(|t| t.w * idx.idf(&t.term)).sum();
        if s > best.1 {
            best = (c.start + k as u32, s);
        }
    }
    best.0
}

/// Fragment linii wokół pierwszego trafienia, maks. `width` znaków.
pub fn snippet(line: &str, qt: &[Tok], width: usize) -> String {
    let line = line.trim();
    let chars: Vec<char> = line.chars().collect();
    if chars.len() <= width {
        return line.to_string();
    }
    let folded: String = fold(line);
    let mut pos = None;
    for t in qt.iter().filter(|t| t.w >= 0.5) {
        let needle = t.term.trim_end_matches(|c: char| c == '.');
        if needle.len() < 2 {
            continue;
        }
        if let Some(p) = folded.find(needle) {
            let cp = folded[..p].chars().count();
            pos = Some(pos.map_or(cp, |x: usize| x.min(cp)));
        }
    }
    let center = pos.unwrap_or(0);
    let start = center.saturating_sub(width / 3).min(chars.len() - width);
    let mut s: String = chars[start..start + width].iter().collect();
    if start > 0 {
        s = format!("…{s}");
    }
    if start + width < chars.len() {
        s.push('…');
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn intent_parsing() {
        let it = parse_intent("najlepszy wynik Qwen XTX");
        assert_eq!(it.agg, Some(Agg::Best));
        let terms: Vec<_> = it.content.iter().map(|t| t.term.as_str()).collect();
        assert!(terms.contains(&"qwen") && terms.contains(&"xtx"), "{terms:?}");
        assert!(!terms.iter().any(|t| t.starts_with("najlep") || t.starts_with("wynik")));
        assert_eq!(it.unit_filter(), Some(vec!["t/s"]));
        let it = parse_intent("gdzie bylo 130 t/s");
        assert_eq!(it.units, vec!["t/s"]);
        assert_eq!(it.numbers, vec![(130.0, 131.0, None)]);
        assert_eq!(parse_intent("wentylator przy 100%").numbers, vec![(100.0, 101.0, Some("%"))]);
        let it = parse_intent("bit-exact przy 27k");
        assert!(it.numbers.is_empty());
        assert!(it.content.iter().any(|t| t.term == "27k"));
        let it = parse_intent("najwolniejszy prefill qwen");
        assert_eq!(it.agg, Some(Agg::Worst));
        assert_eq!(it.unit_filter(), Some(vec!["t/s"]));
    }
}
