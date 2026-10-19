//! kb — szybkie wyszukiwanie w bazie wiedzy KERNEL (wiki, raporty, NOTES.md).
//!
//!   kb search <pytanie…>            top-k fragmentów z plik:linia (hybryda BM25 + e5 + fakty)
//!   kb facts <pytanie…> [--max|--min] liczby z jednostką pasujące do pytania (rekordy, max/min)
//!   kb reindex [--full]              odświeżenie indeksu i embeddingów (przyrostowe)
//!   kb eval [--modes …]              recall@k na złotym zbiorze pytań
//!   kb stats                         rozmiar indeksu
//!
//! Wszystkie polecenia mają `--json` dla agentów.

mod analyze;
mod chunk;
mod embed;
mod eval;
mod facts;
mod index;
mod render;
mod search;
mod serve;

use anyhow::Result;
use clap::{Parser, Subcommand};
use embed::{sync_vectors, Embedder, Vectors};
use index::{Config, Index};
use search::{Mode, Searcher};
use serve::{Engine, Req};
use serde_json::json;
use std::path::PathBuf;
use std::time::Instant;

#[derive(Parser)]
#[command(name = "kb", version, about = "Szybkie wyszukiwanie w bazie wiedzy KERNEL (wiki, raporty, NOTES.md)")]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Fragmenty pasujące do pytania, z plik:linia
    Search {
        query: Vec<String>,
        #[arg(short, default_value_t = 8)]
        k: usize,
        #[arg(long, value_enum, default_value_t = Mode::HybridFacts)]
        mode: Mode,
        #[arg(long)]
        json: bool,
        /// pełny tekst fragmentu zamiast jednej linii
        #[arg(long)]
        full: bool,
    },
    /// Fakty liczbowe (wartość + jednostka + źródło); --max/--min sortuje po wartości
    Facts {
        query: Vec<String>,
        #[arg(short, default_value_t = 10)]
        k: usize,
        #[arg(long, conflicts_with = "min")]
        max: bool,
        #[arg(long)]
        min: bool,
        /// filtr jednostki: t/s, ms, s, GB, %, ×, $, KLD, RPM, °C, tok, tok/krok, ms/krok
        #[arg(long)]
        unit: Option<String>,
        #[arg(long)]
        json: bool,
    },
    /// Odświeża indeks leksykalny i embeddingi (tylko zmienione pliki/fragmenty)
    Reindex {
        /// przebudowa od zera (embeddingi nadal z pamięci podręcznej po hashu)
        #[arg(long)]
        full: bool,
        /// bez embeddingów (tylko BM25 + fakty)
        #[arg(long)]
        no_embed: bool,
        #[arg(long)]
        json: bool,
    },
    /// Ocena na złotym zbiorze pytań (recall@k, MRR, opóźnienie)
    Eval {
        #[arg(long)]
        gold: Option<PathBuf>,
        #[arg(long, value_delimiter = ',', default_value = "bm25,bm25-facts,hybrid-facts")]
        modes: Vec<String>,
        #[arg(short, default_value_t = 5)]
        k: usize,
        /// wypisz pytania bez trafienia
        #[arg(long)]
        misses: bool,
        /// przy chybieniach pokaż wyniki i oczekiwane miejsca
        #[arg(long)]
        explain: bool,
        /// kod wyjścia 1, gdy recall@k ostatniego trybu < próg
        #[arg(long)]
        min_recall: Option<f64>,
    },
    /// Demon trzymający model w pamięci (uruchamiany automatycznie przez `kb search`)
    Serve {
        /// koniec po tylu sekundach bezczynności
        #[arg(long, env = "KB_IDLE", default_value_t = 1800)]
        idle: u64,
    },
    /// Statystyki indeksu
    Stats {
        #[arg(long)]
        json: bool,
    },
}

fn threads() -> usize {
    std::env::var("KB_THREADS").ok().and_then(|s| s.parse().ok()).unwrap_or(4)
}

/// Zapytanie przez demona; bez demona liczy w procesie i (dla trybów z modelem) uruchamia demona.
fn query(cfg: Config, req: Req, needs_dense: bool) -> Result<()> {
    let daemon = std::env::var_os("KB_NO_DAEMON").is_none();
    if daemon {
        if let Ok(o) = serve::client(&cfg, &req) {
            print!("{}", o.stdout);
            eprint!("{}", o.stderr);
            return Ok(());
        }
        if needs_dense {
            serve::spawn_daemon(&cfg);
        }
    }
    let (mut eng, warn) = Engine::open(cfg, needs_dense, 400)?;
    eprint!("{warn}");
    let o = eng.handle(&req)?;
    print!("{}", o.stdout);
    eprint!("{}", o.stderr);
    Ok(())
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    // serwer współdzielony z eksperymentami: domyślnie 4 wątki (KB_THREADS)
    let _ = rayon::ThreadPoolBuilder::new().num_threads(threads()).build_global();
    let cfg = Config::from_env();
    match cli.cmd {
        Cmd::Search { query: words, k, mode, json, full } => {
            let req = Req::Search { q: words.join(" "), k, mode: mode.name().to_string(), json, full };
            query(cfg, req, mode.needs_dense())?;
        }
        Cmd::Facts { query: words, k, max, min, unit, json } => {
            let agg = if max { Some("max".to_string()) } else if min { Some("min".to_string()) } else { None };
            query(cfg, Req::Facts { q: words.join(" "), k, agg, unit, json }, false)?;
        }
        Cmd::Serve { idle } => serve::serve(cfg, idle)?,
        Cmd::Reindex { full, no_embed, json } => {
            let t = Instant::now();
            let (idx, st) = Index::open(&cfg, full)?;
            let lex_ms = t.elapsed().as_secs_f64() * 1e3;
            let mut embedded = 0;
            if !no_embed {
                let old = Vectors::load(&cfg.vectors_path());
                if old.as_ref().is_none_or(|v| v.hashes != idx.passage_hashes) {
                    let mut emb = Embedder::load(&cfg.model_dir, threads())?;
                    embedded = sync_vectors(&cfg, &idx, &mut emb, old, !json)?.1.embedded;
                }
            }
            let total_ms = t.elapsed().as_secs_f64() * 1e3;
            if json {
                println!("{}", json!({"files": st.files, "changed": st.changed, "removed": st.removed, "chunks": idx.chunks.len(), "facts": idx.facts.len(), "embedded": embedded, "lexical_ms": lex_ms, "total_ms": total_ms}));
            } else {
                println!(
                    "pliki {} (zmienione {}, usunięte {}), fragmenty {}, fakty {}, nowe embeddingi {}; {:.0} ms (leksykalny {:.0} ms)",
                    st.files, st.changed, st.removed, idx.chunks.len(), idx.facts.len(), embedded, total_ms, lex_ms
                );
            }
        }
        Cmd::Eval { gold, modes, k, misses, explain, min_recall } => {
            let gold_path = gold.unwrap_or_else(|| cfg.root.join("tools/kb/gold/gold.jsonl"));
            let gold = eval::load_gold(&gold_path)?;
            let (idx, _) = Index::open(&cfg, false)?;
            let exp: Vec<_> = gold.iter().map(|g| eval::resolve(&cfg.root, g)).collect();
            for (g, e) in gold.iter().zip(&exp) {
                if e.iter().all(|(_, l)| l.is_empty()) {
                    eprintln!("uwaga: {} — żaden needle nie występuje w korpusie", g.id);
                }
            }
            let need_dense = modes.iter().any(|m| matches!(m.as_str(), "dense" | "hybrid" | "hybrid-facts"));
            let mut dense = if need_dense {
                let old = Vectors::load(&cfg.vectors_path());
                let mut emb = Embedder::load(&cfg.model_dir, threads())?;
                let v = sync_vectors(&cfg, &idx, &mut emb, old, true)?.0;
                Some((emb, v))
            } else {
                None
            };
            let mut s = Searcher::new(&idx, dense.as_mut().map(|(e, v)| (e, &*v)));
            let mut results = Vec::new();
            for m in &modes {
                let r = eval::run_mode(&cfg, &idx, &mut s, &gold, &exp, m, k)?;
                if misses {
                    for (i, g) in gold.iter().enumerate() {
                        if r.ranks[i].is_none_or(|x| x >= k) {
                            eprintln!("[{m}] chybione {} {:>8} | {}", g.id, g.kind, g.q);
                            if explain {
                                eprintln!("      odp. {}", g.answer);
                                for (f, a, b) in r.top[i].iter().take(k) {
                                    eprintln!("      got  {f}:{a}-{b}");
                                }
                                for (f, ls) in &exp[i] {
                                    eprintln!("      want {f}:{ls:?}");
                                }
                            }
                        }
                    }
                }
                results.push(r);
            }
            print!("{}", eval::report(&results, &gold, k));
            if let (Some(th), Some(last)) = (min_recall, results.last()) {
                let all: Vec<usize> = (0..gold.len()).collect();
                let r = last.recall(&all, k);
                if r < th {
                    eprintln!("recall@{k} {} = {r:.3} < {th}", last.mode);
                    std::process::exit(1);
                }
            }
        }
        Cmd::Stats { json } => {
            let (idx, _) = Index::open(&cfg, false)?;
            let isz = std::fs::metadata(cfg.index_path()).map_or(0, |m| m.len());
            let vsz = std::fs::metadata(cfg.vectors_path()).map_or(0, |m| m.len());
            if json {
                println!("{}", json!({"root": cfg.root, "files": idx.files.len(), "chunks": idx.chunks.len(), "facts": idx.facts.len(), "terms": idx.postings.len(), "index_bytes": isz, "vectors_bytes": vsz, "index": cfg.index_path(), "vectors": cfg.vectors_path(), "model": cfg.model_dir}));
            } else {
                println!(
                    "korzeń {}\npliki {}, fragmenty {}, fakty {}, termy {}\nindeks {} ({:.1} MB), wektory {} ({:.1} MB), model {}",
                    cfg.root.display(),
                    idx.files.len(),
                    idx.chunks.len(),
                    idx.facts.len(),
                    idx.postings.len(),
                    cfg.index_path().display(),
                    isz as f64 / 1e6,
                    cfg.vectors_path().display(),
                    vsz as f64 / 1e6,
                    cfg.model_dir.display()
                );
            }
        }
    }
    Ok(())
}
