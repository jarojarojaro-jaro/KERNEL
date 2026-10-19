//! Embeddingi gęste: multilingual-e5-small (ONNX, int8) przez ONNX Runtime, tylko CPU.
//! Wektory fragmentów w `~/.cache/kb/vectors-*.bin`, kluczowane hashem tekstu fragmentu,
//! więc przebudowa liczy tylko nowe/zmienione fragmenty.

use crate::index::{Config, Index};
use anyhow::{anyhow, Context, Result};
use ort::session::builder::GraphOptimizationLevel;
use ort::session::Session;
use ort::value::Tensor;
use std::collections::HashMap;
use std::path::Path;
use tokenizers::{PaddingParams, PaddingStrategy, Tokenizer, TruncationParams};

pub const MAX_TOKENS: usize = 256;

pub struct Embedder {
    session: Session,
    tok: Tokenizer,
    needs_type_ids: bool,
}

impl Embedder {
    pub fn load(dir: &Path, threads: usize) -> Result<Embedder> {
        let model = ["model_quantized.onnx", "model.onnx"]
            .iter()
            .map(|f| dir.join(f))
            .find(|p| p.exists())
            .ok_or_else(|| anyhow!("brak modelu ONNX w {} (zob. tools/kb/README)", dir.display()))?;
        let t0 = std::time::Instant::now();
        let session = Session::builder()?
            .with_optimization_level(GraphOptimizationLevel::Level3)?
            .with_intra_threads(threads)?
            .commit_from_file(&model)
            .with_context(|| format!("ładowanie {}", model.display()))?;
        let t1 = t0.elapsed();
        let needs_type_ids = session.inputs.iter().any(|i| i.name == "token_type_ids");
        let mut tok = Tokenizer::from_file(dir.join("tokenizer.json")).map_err(|e| anyhow!("tokenizer: {e}"))?;
        tok.with_truncation(Some(TruncationParams { max_length: MAX_TOKENS, ..Default::default() }))
            .map_err(|e| anyhow!("{e}"))?;
        tok.with_padding(Some(PaddingParams { strategy: PaddingStrategy::BatchLongest, ..Default::default() }));
        if std::env::var_os("KB_DEBUG").is_some() {
            eprintln!("kb: sesja ONNX {:?}, tokenizer {:?}", t1, t0.elapsed() - t1);
        }
        Ok(Embedder { session, tok, needs_type_ids })
    }

    /// Znormalizowane (L2) wektory, mean pooling po masce uwagi (normalizacja sumy = normalizacja średniej).
    pub fn embed(&mut self, texts: &[String]) -> Result<Vec<Vec<f32>>> {
        if texts.is_empty() {
            return Ok(Vec::new());
        }
        let enc = self.tok.encode_batch(texts.to_vec(), true).map_err(|e| anyhow!("{e}"))?;
        let b = enc.len();
        let l = enc[0].get_ids().len();
        let mut ids = Vec::with_capacity(b * l);
        let mut mask = Vec::with_capacity(b * l);
        for e in &enc {
            ids.extend(e.get_ids().iter().map(|&x| x as i64));
            mask.extend(e.get_attention_mask().iter().map(|&x| x as i64));
        }
        let ids_t = Tensor::from_array(([b, l], ids))?;
        let mask_t = Tensor::from_array(([b, l], mask.clone()))?;
        let outputs = if self.needs_type_ids {
            let tt = Tensor::from_array(([b, l], vec![0i64; b * l]))?;
            self.session.run(ort::inputs!["input_ids" => ids_t, "attention_mask" => mask_t, "token_type_ids" => tt])?
        } else {
            self.session.run(ort::inputs!["input_ids" => ids_t, "attention_mask" => mask_t])?
        };
        let (shape, data) = outputs[0].try_extract_tensor::<f32>()?;
        let dim = shape[2] as usize;
        let mut out = Vec::with_capacity(b);
        for i in 0..b {
            let mut v = vec![0f32; dim];
            for j in 0..l {
                if mask[i * l + j] == 0 {
                    continue;
                }
                let row = &data[(i * l + j) * dim..(i * l + j + 1) * dim];
                for (a, x) in v.iter_mut().zip(row) {
                    *a += x;
                }
            }
            let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt().max(1e-12);
            v.iter_mut().for_each(|x| *x /= norm);
            out.push(v);
        }
        Ok(out)
    }

    pub fn embed_query(&mut self, q: &str) -> Result<Vec<f32>> {
        Ok(self.embed(&[format!("query: {q}")])?.remove(0))
    }
}

/// Wektory fragmentów w kolejności `Index::chunks`.
pub struct Vectors {
    pub dim: usize,
    pub hashes: Vec<u64>,
    pub data: Vec<f32>,
}

const MAGIC: &[u8; 8] = b"KBVEC001";

impl Vectors {
    pub fn load(path: &Path) -> Option<Vectors> {
        let b = std::fs::read(path).ok()?;
        if b.len() < 24 || &b[..8] != MAGIC {
            return None;
        }
        let dim = u64::from_le_bytes(b[8..16].try_into().ok()?) as usize;
        let n = u64::from_le_bytes(b[16..24].try_into().ok()?) as usize;
        let hs = 24;
        let ds = hs + n * 8;
        if b.len() != ds + n * dim * 4 {
            return None;
        }
        let hashes = b[hs..ds].chunks_exact(8).map(|c| u64::from_le_bytes(c.try_into().unwrap())).collect();
        let data = b[ds..].chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect();
        Some(Vectors { dim, hashes, data })
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        let mut b = Vec::with_capacity(24 + self.hashes.len() * 8 + self.data.len() * 4);
        b.extend_from_slice(MAGIC);
        b.extend_from_slice(&(self.dim as u64).to_le_bytes());
        b.extend_from_slice(&(self.hashes.len() as u64).to_le_bytes());
        for h in &self.hashes {
            b.extend_from_slice(&h.to_le_bytes());
        }
        for x in &self.data {
            b.extend_from_slice(&x.to_le_bytes());
        }
        if let Some(d) = path.parent() {
            std::fs::create_dir_all(d)?;
        }
        let tmp = path.with_extension(format!("tmp{}", std::process::id()));
        std::fs::write(&tmp, b)?;
        std::fs::rename(&tmp, path)?;
        Ok(())
    }

    pub fn row(&self, i: usize) -> &[f32] {
        &self.data[i * self.dim..(i + 1) * self.dim]
    }

    /// Kosinus (wektory znormalizowane) dla wszystkich fragmentów, top-n malejąco.
    pub fn search(&self, q: &[f32], top: usize) -> Vec<(u32, f32)> {
        let mut v: Vec<(u32, f32)> = (0..self.hashes.len())
            .map(|i| (i as u32, self.row(i).iter().zip(q).map(|(a, b)| a * b).sum::<f32>()))
            .collect();
        let top = top.min(v.len());
        if top == 0 {
            return Vec::new();
        }
        v.select_nth_unstable_by(top - 1, |a, b| b.1.total_cmp(&a.1));
        v.truncate(top);
        v.sort_by(|a, b| b.1.total_cmp(&a.1));
        v
    }

}

pub struct SyncStats {
    pub embedded: usize,
}

/// Uzupełnia wektory dla indeksu: istniejące po hashu zostają, brakujące są liczone partiami.
pub fn sync_vectors(cfg: &Config, idx: &Index, emb: &mut Embedder, old: Option<Vectors>, progress: bool) -> Result<(Vectors, SyncStats)> {
    let hashes = idx.passage_hashes.clone();
    let mut known: HashMap<u64, usize> = HashMap::new();
    let mut dim = 0;
    if let Some(o) = &old {
        dim = o.dim;
        for (i, h) in o.hashes.iter().enumerate() {
            known.insert(*h, i);
        }
    }
    let missing: Vec<usize> = (0..hashes.len()).filter(|&i| !known.contains_key(&hashes[i])).collect();
    let mut fresh: HashMap<u64, Vec<f32>> = HashMap::new();
    // sortowanie po długości ogranicza padding w partii
    let mut order = missing.clone();
    order.sort_by_key(|&i| idx.chunks[i].text.len());
    let t0 = std::time::Instant::now();
    for (bi, batch) in order.chunks(32).enumerate() {
        let texts: Vec<String> = batch.iter().map(|&i| idx.passage(i as u32)).collect();
        let vs = emb.embed(&texts)?;
        for (&i, v) in batch.iter().zip(vs) {
            dim = v.len();
            fresh.insert(hashes[i], v);
        }
        if progress && bi % 20 == 0 {
            eprint!("\rembeddingi: {}/{} ({:.0} s)", (bi + 1) * 32, order.len(), t0.elapsed().as_secs_f32());
        }
    }
    if progress && !order.is_empty() {
        eprintln!();
    }
    let mut data = Vec::with_capacity(hashes.len() * dim);
    for h in &hashes {
        match fresh.get(h) {
            Some(v) => data.extend_from_slice(v),
            None => data.extend_from_slice(old.as_ref().unwrap().row(known[h])),
        }
    }
    let v = Vectors { dim, hashes, data };
    if !missing.is_empty() || old.as_ref().is_none_or(|o| o.hashes.len() != v.hashes.len()) {
        v.save(&cfg.vectors_path())?;
    }
    Ok((v, SyncStats { embedded: missing.len() }))
}
