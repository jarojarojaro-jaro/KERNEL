//! Indeks: lista plików (mtime, rozmiar, hash), fragmenty, fakty, odwrócony indeks BM25.
//! Przechowywany w `~/.cache/kb/index-<hash korzenia>.bin` (postcard). Odświeżanie przyrostowe:
//! stat wszystkich plików (~2 ms); zmienione pliki są czytane i dzielone ponownie, reszta zostaje.

use crate::analyze::{analyze, Tok};
use crate::chunk::{chunk_markdown, Chunk};
use crate::facts::{extract, Fact};
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;
use xxhash_rust::xxh3::xxh3_64;

/// wersja formatu i reguł ekstrakcji: zmiana wymusza przebudowę indeksu leksykalnego
const VERSION: u32 = 5;
const K1: f32 = 1.2;
const B: f32 = 0.6;
/// wagi pól BM25F względem treści: tytuł + nazwa pliku + tagi, ścieżka nagłówków + nagłówek tabeli
fn field_w(name: &str, default: f32) -> f32 {
    std::env::var(name).ok().and_then(|s| s.parse().ok()).unwrap_or(default)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileMeta {
    pub path: String,
    pub mtime_ns: u128,
    pub size: u64,
    pub hash: u64,
    pub title: String,
    pub tags: String,
    /// zakres fragmentów [start, end)
    pub chunks: (u32, u32),
}

#[derive(Serialize, Deserialize)]
pub struct Index {
    pub version: u32,
    pub root: String,
    pub files: Vec<FileMeta>,
    pub chunks: Vec<Chunk>,
    pub facts: Vec<Fact>,
    /// fragment → zakres faktów [start, end)
    pub chunk_facts: Vec<(u32, u32)>,
    pub postings: HashMap<String, Vec<(u32, f32)>>,
    pub doc_len: Vec<f32>,
    pub avgdl: f32,
    /// hash tekstu do embeddingu każdego fragmentu (klucz wektorów)
    pub passage_hashes: Vec<u64>,
}

pub struct Config {
    pub root: PathBuf,
    pub cache: PathBuf,
    pub model_dir: PathBuf,
}

impl Config {
    pub fn from_env() -> Config {
        let home = std::env::var("HOME").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("."));
        let root = std::env::var("KB_ROOT").map(PathBuf::from).unwrap_or_else(|_| home.join("KERNEL"));
        let cache = std::env::var("KB_CACHE").map(PathBuf::from).unwrap_or_else(|_| home.join(".cache/kb"));
        let model_dir = std::env::var("KB_MODEL")
            .map(PathBuf::from)
            .unwrap_or_else(|_| home.join("models/kb/multilingual-e5-small"));
        Config { root, cache, model_dir }
    }

    fn tag(&self) -> String {
        format!("{:08x}", xxh3_64(self.root.to_string_lossy().as_bytes()) as u32)
    }

    pub fn index_path(&self) -> PathBuf {
        self.cache.join(format!("index-{}.bin", self.tag()))
    }

    pub fn vectors_path(&self) -> PathBuf {
        let model = self.model_dir.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default();
        self.cache.join(format!("vectors-{}-{}.bin", self.tag(), model))
    }
}

const SKIP_DIRS: &[&str] = &["node_modules", "target", "__pycache__"];
/// README narzędzia (przykładowe zapytania) nie jest wiedzą projektu
const SKIP_PATHS: &[&str] = &["tools/kb"];
const SELF_DOCS: &[&str] = &["product/research/19-kb-wyszukiwanie.md", "wiki/narzedzia/kb.md"];

/// Pliki korpusu: wszystkie *.md pod korzeniem, bez katalogów ukrytych, node_modules, target.
pub fn scan_corpus(root: &Path) -> Result<Vec<(String, u128, u64)>> {
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let rd = match std::fs::read_dir(&dir) {
            Ok(r) => r,
            Err(e) if dir == root => return Err(e).with_context(|| format!("czytanie {}", root.display())),
            Err(_) => continue,
        };
        for ent in rd.flatten() {
            let name = ent.file_name();
            let name = name.to_string_lossy();
            if name.starts_with('.') {
                continue;
            }
            let Ok(ft) = ent.file_type() else { continue };
            let path = ent.path();
            if ft.is_dir() {
                let rel = path.strip_prefix(root).unwrap_or(&path).to_string_lossy();
                if !SKIP_DIRS.contains(&name.as_ref()) && !SKIP_PATHS.contains(&rel.as_ref()) {
                    stack.push(path);
                }
            } else if ft.is_file() && name.ends_with(".md") {
                let Ok(md) = ent.metadata() else { continue };
                let mtime = md.modified().ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok()).map_or(0, |d| d.as_nanos());
                let rel = path.strip_prefix(root).unwrap_or(&path).to_string_lossy().replace('\\', "/");
                out.push((rel, mtime, md.len()));
            }
        }
    }
    out.sort();
    Ok(out)
}

/// Mnożnik oceny pliku: strony pochodne (audyt, log, spisy linków) niżej, rekordy wyżej.
pub fn file_prior(path: &str) -> f32 {
    let name = path.rsplit('/').next().unwrap_or(path);
    match () {
        _ if path == "wiki/AUDYT.md" => 0.45,
        _ if path == "wiki/log.md" => 0.6,
        _ if name == "_hub.md" || path == "wiki/index.md" => 0.7,
        _ if path.contains("/node_modules/") || path.starts_with("app/") && !path.starts_with("app/REPORT") => 0.6,
        // rejestry: najlepsze wyniki i przebadane źródła (punkt startu każdego researchu)
        _ if path == "wiki/REKORDY.md" || path == "wiki/ZRODLA.md" => 1.25,
        // opisy samego kb cytują przykładowe pytania i liczby z innych notatek – nie mogą ich zasłaniać
        _ if SELF_DOCS.contains(&path) => 0.3,
        // notatki o cudzych repozytoriach i surowe rundy researchu (po angielsku), nie wyniki projektu
        _ if path.starts_with("qwen-opt/research/") => 0.8,
        _ => 1.0,
    }
}

pub struct RefreshStats {
    pub files: usize,
    pub changed: usize,
    pub removed: usize,
    pub rebuilt: bool,
}

/// Pole „tytuł”: tytuł notatki, nazwa pliku (bez folderu i daty), tagi.
pub fn title_text(file: &FileMeta) -> String {
    let name = file.path.rsplit('/').next().unwrap_or(&file.path).trim_end_matches(".md");
    format!("{} {} {}", file.title, name.replace(['-', '_'], " "), file.tags)
}

/// Pole „nagłówki”: ścieżka nagłówków bez tytułu + nagłówek tabeli + folder.
pub fn heading_text(file: &FileMeta, c: &Chunk) -> String {
    let h = c.heading.strip_prefix(&file.title).unwrap_or(&c.heading);
    let folder = file.path.rsplit_once('/').map_or("", |x| x.0);
    format!("{} {} {}", h, c.table_header, folder.replace(['/', '-', '_'], " "))
}

impl Index {
    pub fn empty(root: &Path) -> Index {
        Index {
            version: VERSION,
            root: root.to_string_lossy().to_string(),
            files: Vec::new(),
            chunks: Vec::new(),
            facts: Vec::new(),
            chunk_facts: Vec::new(),
            postings: HashMap::new(),
            doc_len: Vec::new(),
            avgdl: 1.0,
            passage_hashes: Vec::new(),
        }
    }

    pub fn load(cfg: &Config) -> Option<Index> {
        let bytes = std::fs::read(cfg.index_path()).ok()?;
        let idx: Index = postcard::from_bytes(&bytes).ok()?;
        (idx.version == VERSION && idx.root == cfg.root.to_string_lossy()).then_some(idx)
    }

    pub fn save(&self, cfg: &Config) -> Result<()> {
        std::fs::create_dir_all(&cfg.cache)?;
        let bytes = postcard::to_stdvec(self)?;
        let tmp = cfg.index_path().with_extension(format!("tmp{}", std::process::id()));
        std::fs::write(&tmp, bytes)?;
        std::fs::rename(&tmp, cfg.index_path())?;
        Ok(())
    }

    /// Wczytuje indeks i odświeża go, jeśli pliki się zmieniły. `force` = przebudowa od zera.
    pub fn open(cfg: &Config, force: bool) -> Result<(Index, RefreshStats)> {
        let mut idx = if force { None } else { Index::load(cfg) }.unwrap_or_else(|| Index::empty(&cfg.root));
        let st = idx.refresh(cfg)?;
        if st.rebuilt {
            idx.save(cfg)?;
        }
        Ok((idx, st))
    }

    pub fn refresh(&mut self, cfg: &Config) -> Result<RefreshStats> {
        let scanned = scan_corpus(&cfg.root)?;
        let old: HashMap<&str, usize> = self.files.iter().enumerate().map(|(i, f)| (f.path.as_str(), i)).collect();
        let unchanged = scanned.len() == self.files.len()
            && scanned.iter().all(|(p, m, s)| old.get(p.as_str()).is_some_and(|&i| self.files[i].mtime_ns == *m && self.files[i].size == *s));
        if unchanged {
            return Ok(RefreshStats { files: scanned.len(), changed: 0, removed: 0, rebuilt: false });
        }
        let removed = self.files.iter().filter(|f| !scanned.iter().any(|(p, _, _)| p == &f.path)).count();
        // stare fragmenty po ścieżce
        let mut new_files = Vec::with_capacity(scanned.len());
        let mut new_chunks: Vec<Chunk> = Vec::with_capacity(self.chunks.len());
        let mut changed = 0;
        for (fid, (path, mtime, size)) in scanned.iter().enumerate() {
            let fid = fid as u32;
            let prev = old.get(path.as_str()).map(|&i| &self.files[i]);
            if let Some(p) = prev.filter(|p| p.mtime_ns == *mtime && p.size == *size) {
                let start = new_chunks.len() as u32;
                for c in &self.chunks[p.chunks.0 as usize..p.chunks.1 as usize] {
                    let mut c = c.clone();
                    c.file = fid;
                    new_chunks.push(c);
                }
                let mut f = p.clone();
                f.chunks = (start, new_chunks.len() as u32);
                new_files.push(f);
                continue;
            }
            let text = match std::fs::read(cfg.root.join(path)) {
                Ok(b) => String::from_utf8_lossy(&b).into_owned(),
                Err(_) => continue,
            };
            let hash = xxh3_64(text.as_bytes());
            if prev.is_none_or(|p| p.hash != hash) {
                changed += 1;
            }
            let stem = path.rsplit('/').next().unwrap_or(path).trim_end_matches(".md");
            let doc = chunk_markdown(fid, &text, stem);
            let start = new_chunks.len() as u32;
            new_chunks.extend(doc.chunks);
            new_files.push(FileMeta {
                path: path.clone(),
                mtime_ns: *mtime,
                size: *size,
                hash,
                title: doc.title,
                tags: doc.tags,
                chunks: (start, new_chunks.len() as u32),
            });
        }
        self.files = new_files;
        self.chunks = new_chunks;
        self.rebuild_derived();
        Ok(RefreshStats { files: scanned.len(), changed, removed, rebuilt: true })
    }

    /// Fakty i BM25 z fragmentów (~4 MB tekstu: ok. 0.2 s na jednym rdzeniu, równolegle mniej).
    fn rebuild_derived(&mut self) {
        use rayon::prelude::*;
        let (w_title, w_head) = (field_w("KB_W_TITLE", 0.5), field_w("KB_W_HEAD", 0.3));
        let titles: Vec<Vec<Tok>> = self.files.par_iter().map(|f| analyze(&title_text(f))).collect();
        let per_chunk: Vec<(Vec<Tok>, Vec<Tok>, Vec<Fact>)> = self
            .chunks
            .par_iter()
            .enumerate()
            .map(|(ci, c)| {
                let f = &self.files[c.file as usize];
                let body = analyze(&c.text);
                let ctx = analyze(&heading_text(f, c));
                let mut facts = Vec::new();
                for (k, line) in c.text.lines().enumerate() {
                    extract(ci as u32, c.start + k as u32, line, &c.table_header, &mut facts);
                }
                (body, ctx, facts)
            })
            .collect();
        let mut postings: HashMap<String, Vec<(u32, f32)>> = HashMap::new();
        let mut doc_len = Vec::with_capacity(self.chunks.len());
        let mut facts = Vec::new();
        let mut chunk_facts = Vec::with_capacity(self.chunks.len());
        let mut tf: HashMap<&str, f32> = HashMap::new();
        for (ci, (body, ctx, fs)) in per_chunk.iter().enumerate() {
            tf.clear();
            let mut len = 0.0;
            for t in body {
                *tf.entry(&t.term).or_default() += t.w;
                len += t.w;
            }
            for t in ctx {
                *tf.entry(&t.term).or_default() += t.w * w_head;
            }
            for t in &titles[self.chunks[ci].file as usize] {
                *tf.entry(&t.term).or_default() += t.w * w_title;
            }
            doc_len.push(len.max(1.0));
            for (term, w) in tf.iter() {
                match postings.get_mut(*term) {
                    Some(v) => v.push((ci as u32, *w)),
                    None => {
                        postings.insert(term.to_string(), vec![(ci as u32, *w)]);
                    }
                }
            }
            let s = facts.len() as u32;
            facts.extend(fs.iter().cloned());
            chunk_facts.push((s, facts.len() as u32));
        }
        self.avgdl = doc_len.iter().sum::<f32>() / doc_len.len().max(1) as f32;
        self.doc_len = doc_len;
        self.postings = postings;
        self.facts = facts;
        self.chunk_facts = chunk_facts;
        self.passage_hashes = (0..self.chunks.len() as u32).into_par_iter().map(|i| xxh3_64(self.passage(i).as_bytes())).collect();
    }

    pub fn idf(&self, term: &str) -> f32 {
        let n = self.chunks.len() as f32;
        let df = self.postings.get(term).map_or(0, |p| p.len()) as f32;
        if df == 0.0 {
            return 0.0;
        }
        (1.0 + (n - df + 0.5) / (df + 0.5)).ln()
    }

    /// BM25 (pola ważone: treść + kontekst) z mnożnikiem pliku. Zwraca (fragment, wynik) malejąco.
    pub fn bm25(&self, q: &[Tok], top: usize) -> Vec<(u32, f32)> {
        let mut scores: HashMap<u32, f32> = HashMap::new();
        for t in q {
            let Some(p) = self.postings.get(&t.term) else { continue };
            let idf = self.idf(&t.term);
            for &(ci, tf) in p {
                let dl = self.doc_len[ci as usize];
                let s = idf * tf * (K1 + 1.0) / (tf + K1 * (1.0 - B + B * dl / self.avgdl));
                *scores.entry(ci).or_default() += t.w * s;
            }
        }
        let mut v: Vec<(u32, f32)> = scores.into_iter().map(|(ci, s)| (ci, s * self.chunk_prior(ci))).collect();
        v.sort_by(|a, b| b.1.total_cmp(&a.1).then(a.0.cmp(&b.0)));
        v.truncate(top);
        v
    }

    /// Mnożnik fragmentu: plik × streszczenie notatki (pogrubiona linia pod tytułem = sedno notatki).
    pub fn chunk_prior(&self, ci: u32) -> f32 {
        let c = &self.chunks[ci as usize];
        let f = &self.files[c.file as usize];
        let summary = ci == f.chunks.0 && c.text.starts_with("**") && f.path.starts_with("wiki/");
        file_prior(&f.path) * if summary { 1.2 } else { 1.0 }
    }

    pub fn chunk_file(&self, ci: u32) -> &FileMeta {
        &self.files[self.chunks[ci as usize].file as usize]
    }

    /// Tekst do embeddingu fragmentu (prefiks „passage: ” dla e5).
    pub fn passage(&self, ci: u32) -> String {
        let c = &self.chunks[ci as usize];
        let f = self.chunk_file(ci);
        let mut s = String::from("passage: ");
        if !c.heading.starts_with(&f.title) {
            s.push_str(&f.title);
            s.push_str(" > ");
        }
        s.push_str(&c.heading);
        s.push('\n');
        if !c.table_header.is_empty() {
            s.push_str(&c.table_header);
            s.push('\n');
        }
        s.push_str(&c.text);
        s
    }
}
