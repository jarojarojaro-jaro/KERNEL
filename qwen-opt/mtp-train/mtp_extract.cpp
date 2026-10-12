// mtp_extract: per-token data for MTP-head self-distillation / offline acceptance on Qwen3.5-family GGUFs.
//
// For every sequence (prompt + target-generated response) it
//   1. teacher-forces the target and writes
//        h.f16      [n_tok, n_embd]  fp16  target h_nextn (output_norm of the last trunk layer) at every position
//        top.bin    [n_resp, K]      (int32 id, float logprob) target top-K over the full vocab at the positions
//                                    p = n_prompt-1 .. n_tok-2 (they predict the response tokens x_{p+1})
//   2. teacher-forces the MTP head (pairs (x_p, h_{p-1}), h_{-1} = 0, as common/speculative.cpp process() does)
//      and, for the first --parity-seqs sequences, writes the depth-1 draft logits on the reduced draft vocabulary
//        d1.f32     [n_par, n_vocab_dft] fp32 and d1h.f32 [n_par, n_embd] fp32 (MTP h_nextn) at p = n_prompt-1 ..
//   3. for every response position t = n_prompt-1 .. n_tok-2 runs the shipped greedy MTP draft chain exactly as the
//      server does (prefix MTP KV from teacher-forced pairs, row 0 = (x_t, h_{t-1}), n_draft chained passes) and writes
//        chain.bin  [n_resp, n_draft] int32 draft tokens (d_j predicts x_{t+j})
//   meta.txt: one line per sequence "n_tok n_prompt" plus a header.
//
// Input: binary file, int32 n_seq, then per sequence int32 n_tok, int32 n_prompt, int32 tokens[n_tok].

#include "llama.h"
#include "ggml.h"
#include "llama-ext.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include <chrono>

static void die(const char * msg) { fprintf(stderr, "error: %s\n", msg); exit(1); }

static ggml_type parse_type(const std::string & s) {
    if (s == "f16") return GGML_TYPE_F16;
    if (s == "q8_0") return GGML_TYPE_Q8_0;
    if (s == "q4_0") return GGML_TYPE_Q4_0;
    die("unsupported kv type");
    return GGML_TYPE_F16;
}

int main(int argc, char ** argv) {
    std::string model_path, vocab_path, in_path, out_dir, kv = "q4_0", kv_dft = "f16";  // server: -ctk q4_0, draft ctx f16
    int n_vocab_dft = 65536, n_draft = 4, topk = 32, parity_seqs = 2, parity_max = 512, n_ctx = 8192, n_ubatch = 512;
    int seq_begin = 0, seq_end = -1;  // [begin, end): outputs are appended when begin > 0 (time-boxed blocks)
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto next = [&]() { if (i + 1 >= argc) die("missing value"); return std::string(argv[++i]); };
        if (a == "-m") model_path = next();
        else if (a == "--vocab") vocab_path = next();
        else if (a == "--vocab-n") n_vocab_dft = std::stoi(next());
        else if (a == "--in") in_path = next();
        else if (a == "--out") out_dir = next();
        else if (a == "--n-draft") n_draft = std::stoi(next());
        else if (a == "--topk") topk = std::stoi(next());
        else if (a == "--parity-seqs") parity_seqs = std::stoi(next());
        else if (a == "--parity-max") parity_max = std::stoi(next());
        else if (a == "--begin") seq_begin = std::stoi(next());
        else if (a == "--end") seq_end = std::stoi(next());
        else if (a == "-c") n_ctx = std::stoi(next());
        else if (a == "--kv") kv = next();
        else if (a == "--kv-dft") kv_dft = next();
        else die(("unknown arg " + a).c_str());
    }
    if (model_path.empty() || vocab_path.empty() || in_path.empty() || out_dir.empty()) {
        die("usage: mtp_extract -m model.gguf --vocab draft_vocab.txt --in seqs.bin --out dir");
    }

    // ---- input
    std::vector<std::vector<llama_token>> seqs;
    std::vector<int> n_prompts;
    {
        FILE * f = fopen(in_path.c_str(), "rb");
        if (!f) die("cannot open input");
        int32_t n_seq;
        if (fread(&n_seq, 4, 1, f) != 1) die("bad input");
        for (int s = 0; s < n_seq; ++s) {
            int32_t hdr[2];
            if (fread(hdr, 4, 2, f) != 2) die("bad input");
            std::vector<llama_token> t(hdr[0]);
            if (fread(t.data(), 4, hdr[0], f) != (size_t) hdr[0]) die("bad input");
            seqs.push_back(std::move(t));
            n_prompts.push_back(hdr[1]);
        }
        fclose(f);
        if (seq_end < 0 || seq_end > (int) seqs.size()) seq_end = (int) seqs.size();
    }

    std::vector<llama_token> dvocab;
    {
        std::ifstream f(vocab_path);
        long long id;
        while ((int) dvocab.size() < n_vocab_dft && f >> id) dvocab.push_back((llama_token) id);
    }

    llama_backend_init();
    auto mparams = llama_model_default_params();
    mparams.n_gpu_layers = 999;
    mparams.load_mtp = true;
    llama_model * model = llama_model_load_from_file(model_path.c_str(), mparams);
    if (!model) die("model load failed");
    if (!llama_model_set_draft_head_vocab(model, dvocab.data(), (int32_t) dvocab.size())) die("set_draft_head_vocab failed");

    const int n_embd  = llama_model_n_embd(model);
    const int n_vocab = llama_vocab_n_tokens(llama_model_get_vocab(model));

    auto cparams = llama_context_default_params();
    cparams.n_ctx = n_ctx;
    cparams.n_batch = n_ubatch;
    cparams.n_ubatch = n_ubatch;
    cparams.n_seq_max = 1;
    cparams.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
    cparams.type_k = parse_type(kv);
    cparams.type_v = parse_type(kv);
    cparams.no_perf = true;
    llama_context * ctx_tgt = llama_init_from_model(model, cparams);
    if (!ctx_tgt) die("target ctx failed");

    auto dparams = cparams;
    dparams.ctx_type = LLAMA_CONTEXT_TYPE_MTP;
    dparams.n_rs_seq = 0;
    dparams.type_k = parse_type(kv_dft);
    dparams.type_v = parse_type(kv_dft);
    dparams.ctx_other = ctx_tgt;
    llama_context * ctx_dft = llama_init_from_model(model, dparams);
    if (!ctx_dft) die("mtp ctx failed");

    llama_set_embeddings_nextn(ctx_tgt, true, /*masked*/ false);
    llama_set_embeddings_nextn(ctx_dft, true, /*masked*/ true);
    if (!llama_set_mtp_draft_chain(ctx_dft, true)) die("draft chain unsupported");
    llama_set_mtp_draft_chain(ctx_dft, false);

    llama_batch_ext * batch_t = llama_batch_ext_init(ctx_tgt);
    llama_batch_ext * batch_d = llama_batch_ext_init(ctx_dft);

    auto open_out = [&](const char * name) {
        FILE * f = fopen((out_dir + "/" + name).c_str(), seq_begin > 0 ? "ab" : "wb");
        if (!f) die("cannot open output");
        return f;
    };
    FILE * f_h = open_out("h.f16");
    FILE * f_top = open_out("top.bin");
    FILE * f_chain = open_out("chain.bin");
    FILE * f_d1 = open_out("d1.f32");
    FILE * f_d1h = open_out("d1h.f32");
    FILE * f_meta = open_out("meta.txt");
    if (seq_begin == 0) {
        fprintf(f_meta, "n_embd %d n_vocab %d n_vocab_dft %d n_draft %d topk %d parity_seqs %d parity_max %d kv %s\n",
                n_embd, n_vocab, (int) dvocab.size(), n_draft, topk, parity_seqs, parity_max, kv.c_str());
    }

    std::vector<ggml_fp16_t> hrow(n_embd);
    std::vector<float> zeros(n_embd, 0.0f);
    std::vector<int> idx(n_vocab);
    std::vector<char> top_buf((size_t) topk * 8);
    double t_tgt = 0, t_d1 = 0, t_chain = 0;
    long n_chain_total = 0;

    auto now = [] { return std::chrono::steady_clock::now(); };
    auto secs = [](auto a, auto b) { return std::chrono::duration<double>(b - a).count(); };

    for (size_t s = seq_begin; s < (size_t) seq_end; ++s) {
        const auto & tok = seqs[s];
        const int n_tok = (int) tok.size();
        const int n_prompt = n_prompts[s];
        if (n_tok + n_draft + 1 > n_ctx || n_prompt < 2 || n_prompt >= n_tok) die("sequence does not fit / bad n_prompt");
        fprintf(f_meta, "%d %d\n", n_tok, n_prompt);

        llama_memory_clear(llama_get_memory(ctx_tgt), true);
        llama_memory_clear(llama_get_memory(ctx_dft), true);

        // ---- 1. target pass
        auto t0 = now();
        std::vector<float> h_all((size_t) n_tok * n_embd);
        for (int b0 = 0; b0 < n_tok; b0 += n_ubatch) {
            const int nb = std::min(n_ubatch, n_tok - b0);
            llama_batch_ext_clear(batch_t);
            for (int i = 0; i < nb; ++i) {
                const int p = b0 + i;
                const int32_t k = llama_batch_ext_add_token(batch_t, 0, tok[p]);
                const llama_pos pos[4] = { p, 0, 0, 0 };
                llama_batch_ext_set_pos(batch_t, k, pos);
                if (p >= n_prompt - 1 && p <= n_tok - 2) llama_batch_ext_set_output_logits(batch_t, k, true);
            }
            if (llama_process(ctx_tgt, LLAMA_PROCESS_TYPE_DECODE, batch_t) != 0) die("target decode failed");
            const float * h = llama_get_embeddings_nextn(ctx_tgt);
            if (!h) die("no nextn embeddings");
            memcpy(h_all.data() + (size_t) b0 * n_embd, h, (size_t) nb * n_embd * sizeof(float));
            for (int i = 0; i < nb; ++i) {
                const int p = b0 + i;
                if (!(p >= n_prompt - 1 && p <= n_tok - 2)) continue;
                const float * lg = llama_get_logits_ith(ctx_tgt, i);
                float mx = -INFINITY;
                for (int v = 0; v < n_vocab; ++v) mx = std::max(mx, lg[v]);
                double se = 0;
                for (int v = 0; v < n_vocab; ++v) se += std::exp((double) lg[v] - mx);
                const float lse = mx + (float) std::log(se);
                for (int v = 0; v < n_vocab; ++v) idx[v] = v;
                std::partial_sort(idx.begin(), idx.begin() + topk, idx.end(), [&](int a, int b) { return lg[a] > lg[b]; });
                for (int k = 0; k < topk; ++k) {
                    const int32_t id = idx[k];
                    const float lp = lg[id] - lse;
                    memcpy(top_buf.data() + 8 * k, &id, 4);
                    memcpy(top_buf.data() + 8 * k + 4, &lp, 4);
                }
                fwrite(top_buf.data(), 1, top_buf.size(), f_top);
            }
        }
        for (int p = 0; p < n_tok; ++p) {
            ggml_fp32_to_fp16_row(h_all.data() + (size_t) p * n_embd, hrow.data(), n_embd);
            fwrite(hrow.data(), sizeof(ggml_fp16_t), n_embd, f_h);
        }
        auto t1 = now();
        t_tgt += secs(t0, t1);

        // ---- 2. teacher-forced MTP prefix (and depth-1 parity logits)
        const bool parity = (int) s < parity_seqs;
        const int p_end = parity ? std::min(n_tok - 1, n_prompt - 1 + parity_max) : n_prompt - 1;  // exclusive
        for (int b0 = 0; b0 < p_end; b0 += n_ubatch) {
            const int nb = std::min(n_ubatch, p_end - b0);
            llama_batch_ext_clear(batch_d);
            for (int i = 0; i < nb; ++i) {
                const int p = b0 + i;
                const int32_t k = llama_batch_ext_add_token(batch_d, 0, tok[p]);
                const llama_pos pos[4] = { p, 0, 0, 0 };
                llama_batch_ext_set_pos(batch_d, k, pos);
                const float * hp = p == 0 ? zeros.data() : h_all.data() + (size_t) (p - 1) * n_embd;
                llama_batch_ext_set_embd_token(batch_d, k, { hp, 1, (size_t) n_embd });
                // parity batches output every row: with masked=true the MTP context copies the first n_outputs
                // rows of h_nextn (taken before the output gather), so h rows only line up with the logits
                // rows when every row is an output
                if (parity) llama_batch_ext_set_output_logits(batch_d, k, true);
            }
            if (llama_process(ctx_dft, LLAMA_PROCESS_TYPE_DECODE, batch_d) != 0) die("mtp decode failed");
            if (parity) {
                for (int i = 0; i < nb; ++i) {
                    const int p = b0 + i;
                    if (p < n_prompt - 1) continue;
                    const float * lg = llama_get_logits_ith(ctx_dft, i);
                    const float * hn = llama_get_embeddings_nextn_ith(ctx_dft, i);
                    for (size_t v = 0; v < dvocab.size(); ++v) fwrite(&lg[dvocab[v]], 4, 1, f_d1);
                    fwrite(hn, 4, n_embd, f_d1h);
                }
            }
        }
        auto t2 = now();
        t_d1 += secs(t1, t2);

        // ---- 3. greedy draft chain from every response position
        llama_memory_t mem_d = llama_get_memory(ctx_dft);
        for (int t = n_prompt - 1; t <= n_tok - 2; ++t) {
            llama_memory_seq_rm(mem_d, 0, t, -1);
            llama_batch_ext_clear(batch_d);
            const float * hp = h_all.data() + (size_t) (t - 1) * n_embd;
            for (int j = 0; j < n_draft; ++j) {
                const int32_t k = llama_batch_ext_add_token(batch_d, 0, tok[t]);
                const llama_pos pos[4] = { t + j, 0, 0, 0 };
                llama_batch_ext_set_pos(batch_d, k, pos);
                llama_batch_ext_set_embd_token(batch_d, k, { hp, 1, (size_t) n_embd });
            }
            llama_set_mtp_draft_chain(ctx_dft, true);
            const int rc = llama_process(ctx_dft, LLAMA_PROCESS_TYPE_DECODE, batch_d);
            llama_set_mtp_draft_chain(ctx_dft, false);
            if (rc != 0) die("chain decode failed");
            int32_t n_out = 0;
            const llama_token * ids = llama_get_mtp_draft_tokens(ctx_dft, &n_out);
            if (n_out != n_draft) die("chain output size");
            fwrite(ids, 4, n_draft, f_chain);
            ++n_chain_total;
        }
        auto t3 = now();
        t_chain += secs(t2, t3);
        fprintf(stderr, "seq %zu/%zu: n_tok %d n_prompt %d | tgt %.1fs mtp-tf %.1fs chain %.1fs (%.2f ms/chain)\n",
                s + 1, seqs.size(), n_tok, n_prompt, secs(t0, t1), secs(t1, t2), secs(t2, t3),
                1e3 * secs(t2, t3) / std::max(1, n_tok - n_prompt));
    }
    fprintf(stderr, "total: tgt %.1fs mtp-tf %.1fs chain %.1fs, %ld chains\n", t_tgt, t_d1, t_chain, n_chain_total);
    for (FILE * f : { f_h, f_top, f_chain, f_d1, f_d1h, f_meta }) fclose(f);
    llama_batch_ext_free(batch_t);
    llama_batch_ext_free(batch_d);
    llama_free(ctx_dft);
    llama_free(ctx_tgt);
    llama_model_free(model);
    return 0;
}
