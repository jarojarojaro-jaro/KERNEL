//! Silnik zapytań i demon `kb serve`.
//!
//! Załadowanie modelu e5 (tokenizer 17 MB JSON + sesja ONNX) kosztuje 0.4–1 s, a samo zapytanie
//! ~10 ms. Dlatego `kb search` najpierw pyta demona przez gniazdo Unix
//! (`~/.cache/kb/kb-<hash>.sock`); jeśli go nie ma, liczy w procesie i uruchamia demona w tle
//! (`nice -n 19 taskset -c 0-3`, kończy się po `KB_IDLE` s bezczynności, domyślnie 1800). Demon przed każdym
//! zapytaniem odświeża indeks (stat plików, ~2 ms), więc nigdy nie odpowiada z nieaktualnej bazy.

use crate::embed::{sync_vectors, Embedder, Vectors};
use crate::index::{Config, Index};
use crate::render::{self, Out};
use crate::search::{facts_query, Agg, Mode, Searcher};
use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Clone)]
pub enum Req {
    Search { q: String, k: usize, mode: String, json: bool, full: bool },
    Facts { q: String, k: usize, agg: Option<String>, unit: Option<String>, json: bool },
}

#[derive(Serialize, Deserialize)]
struct Envelope {
    build: String,
    req: Req,
}

#[derive(Serialize, Deserialize)]
struct Resp {
    stdout: String,
    stderr: String,
    /// demon z innej wersji binarki: klient liczy sam, demon się kończy
    restart: bool,
}

pub struct Engine {
    pub cfg: Config,
    pub idx: Index,
    pub dense: Option<(Embedder, Vectors)>,
}

fn threads() -> usize {
    std::env::var("KB_THREADS").ok().and_then(|s| s.parse().ok()).unwrap_or(4)
}

/// Model + wektory zgodne z indeksem. Przy dużym braku wektorów (świeża instalacja) None:
/// wyszukiwanie spada do BM25 + faktów i mówi o tym na stderr.
pub fn load_dense(cfg: &Config, idx: &Index, max_missing: usize, warn: &mut String) -> Result<Option<(Embedder, Vectors)>> {
    if !cfg.model_dir.join("tokenizer.json").exists() {
        warn.push_str(&format!("kb: brak modelu {} — tryb bm25-facts (zob. tools/kb/README.md)\n", cfg.model_dir.display()));
        return Ok(None);
    }
    let old = Vectors::load(&cfg.vectors_path());
    let stale = match &old {
        Some(v) if v.hashes == idx.passage_hashes => 0,
        Some(v) => {
            let have: std::collections::HashSet<u64> = v.hashes.iter().copied().collect();
            idx.passage_hashes.iter().filter(|h| !have.contains(h)).count()
        }
        None => idx.chunks.len(),
    };
    if stale > max_missing {
        warn.push_str(&format!("kb: {stale} fragmentów bez embeddingu — tryb bm25-facts; uruchom `kb reindex`\n"));
        return Ok(None);
    }
    let mut emb = Embedder::load(&cfg.model_dir, threads())?;
    let vecs = match old {
        Some(v) if stale == 0 => v,
        old => sync_vectors(cfg, idx, &mut emb, old, false)?.0,
    };
    Ok(Some((emb, vecs)))
}

impl Engine {
    /// `max_missing`: ile fragmentów bez wektora wolno doliczyć przy starcie (klient: mało, demon: wszystkie).
    pub fn open(cfg: Config, want_dense: bool, max_missing: usize) -> Result<(Engine, String)> {
        let (idx, _) = Index::open(&cfg, false)?;
        let mut warn = String::new();
        let dense = if want_dense { load_dense(&cfg, &idx, max_missing, &mut warn)? } else { None };
        Ok((Engine { cfg, idx, dense }, warn))
    }

    /// Odświeża indeks po zmianach plików; brakujące embeddingi liczy od razu (gdy model załadowany).
    pub fn refresh(&mut self) -> Result<()> {
        let st = self.idx.refresh(&self.cfg)?;
        if st.rebuilt {
            self.idx.save(&self.cfg)?;
            if let Some((emb, v)) = self.dense.as_mut() {
                let old = std::mem::replace(v, Vectors { dim: 0, hashes: Vec::new(), data: Vec::new() });
                *v = sync_vectors(&self.cfg, &self.idx, emb, Some(old), false)?.0;
            }
        }
        Ok(())
    }

    pub fn handle(&mut self, req: &Req) -> Result<Out> {
        let t = Instant::now();
        match req {
            Req::Search { q, k, mode, json, full } => {
                let mut mode: Mode = clap::ValueEnum::from_str(mode, true).map_err(|e| anyhow!(e))?;
                if mode.needs_dense() && self.dense.is_none() {
                    mode = Mode::Bm25Facts;
                }
                let mut s = Searcher::new(&self.idx, self.dense.as_mut().map(|(e, v)| (e, &*v)));
                let hits = s.search(q, mode, *k)?;
                Ok(render::hits(&self.cfg, &self.idx, q, &hits, mode, *json, *full, t.elapsed().as_secs_f64() * 1e3))
            }
            Req::Facts { q, k, agg, unit, json } => {
                let force = match agg.as_deref() {
                    Some("max") => Some(Agg::Max),
                    Some("min") => Some(Agg::Min),
                    _ => None,
                };
                let (it, fh) = facts_query(&self.idx, q, force, unit.as_deref(), *k);
                Ok(render::facts(&self.cfg, &self.idx, q, &it, &fh, *json, t.elapsed().as_secs_f64() * 1e3))
            }
        }
    }
}

pub fn socket_path(cfg: &Config) -> PathBuf {
    cfg.index_path().with_extension("sock")
}

/// Identyfikator binarki (mtime + rozmiar): demon starszej wersji nie obsłuży nowego klienta.
fn build_id() -> String {
    std::env::current_exe()
        .and_then(std::fs::metadata)
        .map(|m| {
            let t = m.modified().ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok()).map_or(0, |d| d.as_nanos());
            format!("{}-{}-{}", env!("CARGO_PKG_VERSION"), t, m.len())
        })
        .unwrap_or_default()
}

/// Zapytanie do demona. Err = brak demona albo inna wersja (klient liczy sam).
pub fn client(cfg: &Config, req: &Req) -> Result<Out> {
    let mut s = UnixStream::connect(socket_path(cfg))?;
    s.set_read_timeout(Some(Duration::from_secs(60)))?;
    let mut line = serde_json::to_string(&Envelope { build: build_id(), req: req.clone() })?;
    line.push('\n');
    s.write_all(line.as_bytes())?;
    let mut resp = String::new();
    BufReader::new(s).read_line(&mut resp)?;
    let r: Resp = serde_json::from_str(&resp)?;
    if r.restart {
        return Err(anyhow!("demon innej wersji"));
    }
    Ok(Out { stdout: r.stdout, stderr: r.stderr })
}

/// Uruchamia demona w tle (setsid + nice), bez czekania.
pub fn spawn_daemon(cfg: &Config) {
    let Ok(exe) = std::env::current_exe() else { return };
    let log = std::fs::OpenOptions::new().create(true).append(true).open(cfg.cache.join("serve.log"));
    // zasada serwera: praca w tle na najniższym priorytecie i najwyżej rdzeniach 0-3
    let mut cmd = std::process::Command::new("setsid");
    cmd.args(["-f", "nice", "-n", "19", "taskset", "-c", "0-3"]).arg(exe).arg("serve");
    cmd.stdin(std::process::Stdio::null()).stdout(std::process::Stdio::null());
    match log {
        Ok(f) => cmd.stderr(f),
        Err(_) => cmd.stderr(std::process::Stdio::null()),
    };
    let _ = cmd.spawn();
}

pub fn serve(cfg: Config, idle: u64) -> Result<()> {
    std::fs::create_dir_all(&cfg.cache)?;
    let path = socket_path(&cfg);
    if UnixStream::connect(&path).is_ok() {
        return Ok(()); // inny demon już działa
    }
    // jeden demon naraz także w trakcie rozgrzewania (liczenie brakujących embeddingów)
    let lock = path.with_extension("pid");
    if let Ok(pid) = std::fs::read_to_string(&lock) {
        if std::path::Path::new(&format!("/proc/{}", pid.trim())).exists() {
            return Ok(());
        }
        let _ = std::fs::remove_file(&lock);
    }
    let Ok(mut lf) = std::fs::File::create_new(&lock) else { return Ok(()) };
    write!(lf, "{}", std::process::id())?;
    let started = Instant::now();
    let (mut eng, warn) = match Engine::open(cfg, true, usize::MAX) {
        Ok(x) => x,
        Err(e) => {
            let _ = std::fs::remove_file(&lock);
            return Err(e);
        }
    };
    eprint!("{warn}");
    let _ = std::fs::remove_file(&path);
    let listener = UnixListener::bind(&path)?;
    eprintln!("kb serve: gotowy po {:.1} s, pid {}", started.elapsed().as_secs_f32(), std::process::id());
    let me = build_id();
    let last = Arc::new(AtomicU64::new(now()));
    {
        let last = last.clone();
        let path = path.clone();
        std::thread::spawn(move || loop {
            std::thread::sleep(Duration::from_secs(30));
            if now().saturating_sub(last.load(Ordering::Relaxed)) > idle {
                let _ = std::fs::remove_file(&path);
                let _ = std::fs::remove_file(path.with_extension("pid"));
                std::process::exit(0);
            }
        });
    }
    for conn in listener.incoming() {
        let Ok(mut conn) = conn else { continue };
        last.store(now(), Ordering::Relaxed);
        let mut line = String::new();
        if BufReader::new(&conn).read_line(&mut line).is_err() {
            continue;
        }
        let resp = match serde_json::from_str::<Envelope>(&line) {
            Ok(env) if env.build != me => Resp { stdout: String::new(), stderr: String::new(), restart: true },
            Ok(env) => match eng.refresh().and_then(|_| eng.handle(&env.req)) {
                Ok(o) => Resp { stdout: o.stdout, stderr: o.stderr, restart: false },
                Err(e) => Resp { stdout: String::new(), stderr: format!("kb serve: {e:#}\n"), restart: false },
            },
            Err(e) => Resp { stdout: String::new(), stderr: format!("kb serve: zły request: {e}\n"), restart: false },
        };
        let restart = resp.restart;
        let mut out = serde_json::to_string(&resp)?;
        out.push('\n');
        let _ = conn.write_all(out.as_bytes());
        if restart {
            let _ = std::fs::remove_file(&path);
            let _ = std::fs::remove_file(path.with_extension("pid"));
            return Ok(());
        }
    }
    Ok(())
}

fn now() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map_or(0, |d| d.as_secs())
}
