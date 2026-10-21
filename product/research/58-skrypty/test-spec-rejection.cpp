// [LLAMA_DFLASH_SAMPLE] speculative rejection sampling with a sampled DFlash2 selector path: the verified output must
// follow the target distribution exactly, whatever the draft distribution.
//
//   test-spec-rejection [n_samples]   (default 200000)
//
// Toy target p over a 12-token vocabulary, toy selector lattices of k = 6 candidates per position (some candidates
// outside p's support, some target tokens outside the candidates, one repeated id). Each case draws the path with
// common_speculative_dflash2_pick and verifies it with common_sampler_rejection_step, exactly as the server does
// (rejected -> residual draw, accepted to the end -> the target's own sample). Pearson chi-square of the outputs (one
// position, and the joint of two positions with a predecessor-dependent selector and a context-dependent target)
// against p; a test fails below p = 1e-4. The acceptance rate must match sum_x min(p(x), q(x)) (|z| < 5). A negative
// control (q not the draw's distribution) must fail the chi-square, so the test has power.

#include "sampling.h"
#include "speculative.h"

#include "llama.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

static int g_fail = 0;

// upper regularized gamma Q(a, x) (Numerical Recipes 6.2)
static double gamma_q(double a, double x) {
    if (x <= 0.0) {
        return 1.0;
    }
    const double gln = std::lgamma(a);
    if (x < a + 1.0) {
        double ap = a, sum = 1.0/a, del = sum;
        for (int n = 0; n < 1000; ++n) {
            ap += 1.0;
            del *= x/ap;
            sum += del;
            if (std::fabs(del) < std::fabs(sum)*1e-15) {
                break;
            }
        }
        return 1.0 - sum*std::exp(-x + a*std::log(x) - gln);
    }
    double b = x + 1.0 - a, c = 1.0/1e-300, d = 1.0/b, h = d;
    for (int i = 1; i < 1000; ++i) {
        const double an = -i*(i - a);
        b += 2.0;
        d = an*d + b;
        if (std::fabs(d) < 1e-300) d = 1e-300;
        c = b + an/c;
        if (std::fabs(c) < 1e-300) c = 1e-300;
        d = 1.0/d;
        const double del = d*c;
        h *= del;
        if (std::fabs(del - 1.0) < 1e-15) {
            break;
        }
    }
    return std::exp(-x + a*std::log(x) - gln)*h;
}

// Pearson chi-square p-value of observed counts against expected probabilities; a count where p = 0 fails outright
static double chi2_pvalue(const std::vector<double> & p, const std::vector<long> & cnt, long n, int & df) {
    double chi2 = 0.0;
    int cells = 0;
    for (size_t i = 0; i < p.size(); ++i) {
        if (p[i] == 0.0) {
            if (cnt[i] > 0) {
                df = 0;
                return 0.0;
            }
            continue;
        }
        const double e = p[i]*n;
        chi2 += (cnt[i] - e)*(cnt[i] - e)/e;
        cells++;
    }
    df = std::max(1, cells - 1);
    return gamma_q(0.5*df, 0.5*chi2);
}

static void check(bool ok, const std::string & what) {
    if (!ok) {
        g_fail++;
    }
    printf("  %-4s %s\n", ok ? "ok" : "FAIL", what.c_str());
}

static constexpr int V = 12; // toy vocabulary
static constexpr int K = 6;  // selector candidates per position

// the target's candidate array: tokens with p > 0, normalized, in descending order like a sampler leaves it
static std::vector<llama_token_data> target_of(const std::vector<double> & p) {
    std::vector<llama_token_data> out;
    for (int t = 0; t < V; ++t) {
        if (p[t] > 0.0) {
            out.push_back({ t, (float) std::log(p[t]), (float) p[t] });
        }
    }
    std::sort(out.begin(), out.end(), [](const llama_token_data & a, const llama_token_data & b) { return a.p > b.p; });
    return out;
}

// one selector row as DFlash2 lays it out: k candidate ids (as floats), then k x k pair scores (predecessor-major)
struct toy_row {
    std::vector<float> data;
    const float * cand() const { return data.data(); }
    const float * scores(int pred) const { return data.data() + K + (size_t) pred*K; }
};

static toy_row make_row(const std::vector<int> & ids, std::mt19937 & rng, float spread) {
    std::normal_distribution<float> nd(0.0f, spread);
    toy_row r;
    r.data.resize(K + K*K);
    for (int j = 0; j < K; ++j) {
        r.data[j] = (float) ids[j];
    }
    for (int a = 0; a < K; ++a) {
        for (int b = 0; b < K; ++b) {
            r.data[K + a*K + b] = nd(rng) - 0.4f*b; // earlier candidates a bit likelier, like a sorted top-k
        }
    }
    return r;
}

// one position: draw from the lattice, verify against p; distribution of the output, acceptance vs sum min(p, q)
static void test_one(const char * name, const std::vector<double> & p, const toy_row & row, float temp, long n) {
    std::mt19937 rng_d(1234), rng_t(5678);
    std::uniform_real_distribution<float> uni(0.0f, 1.0f);

    const auto tgt = target_of(p);
    std::vector<llama_token_data> q, residual;
    std::vector<long> cnt(V, 0);
    long n_acc = 0;
    double acc_expect = 0.0;
    {
        float qp = 0.0f;
        common_speculative_dflash2_pick(row.cand(), row.scores(0), K, temp, 0.5f, q, qp);
        for (const auto & e : q) {
            if (e.p > 0.0f) {
                acc_expect += std::min((double) e.p, p[e.id]);
            }
        }
    }
    for (long s = 0; s < n; ++s) {
        float q_pick = 0.0f;
        const int pick = common_speculative_dflash2_pick(row.cand(), row.scores(0), K, temp, uni(rng_d), q, q_pick);
        const llama_token x = (llama_token) row.cand()[pick];
        // the target's own sample for the fallback (unused unless the residual is empty)
        bool accepted = false;
        const llama_token t = common_sampler_rejection_step(tgt.data(), tgt.size(), q.data(), q.size(), x, tgt[0].id,
                rng_t, residual, accepted);
        cnt[t]++;
        n_acc += accepted;
    }
    int df = 0;
    const double pv = chi2_pvalue(p, cnt, n, df);
    char buf[256];
    snprintf(buf, sizeof buf, "%s: output ~ target, chi2 p = %.4f (df %d)", name, pv, df);
    check(pv > 1e-4, buf);
    const double a = (double) n_acc/n;
    const double z = (a - acc_expect)/std::sqrt(acc_expect*(1.0 - acc_expect)/n + 1e-12);
    snprintf(buf, sizeof buf, "%s: acceptance %.4f vs sum min(p, q) %.4f (z %.2f)", name, a, acc_expect, z);
    check(std::fabs(z) < 5.0, buf);
}

// the target of position 2 given the token at position 1 (a context-dependent toy)
static std::vector<double> p2_of(int t1) {
    std::vector<double> p(V, 0.0);
    double sum = 0.0;
    for (int t = 0; t < V; ++t) {
        if ((t + t1) % 5 == 0) {
            continue; // holes that move with the context
        }
        p[t] = std::exp(-0.35*std::abs(t - (t1*7) % V)) + 0.02;
        sum += p[t];
    }
    for (auto & v : p) {
        v /= sum;
    }
    return p;
}

// two positions, as the server verifies a 2-token draft: the joint (t1, t2) must be p1(t1) p2(t2 | t1)
static void test_two(const std::vector<double> & p1, const toy_row & r1, const toy_row & r2, float temp, long n) {
    std::mt19937 rng_d(42), rng_t(4242);
    std::uniform_real_distribution<float> uni(0.0f, 1.0f);

    const auto tgt1 = target_of(p1);
    std::vector<std::vector<llama_token_data>> tgt2(V);
    std::vector<std::vector<double>> p2(V);
    for (int t = 0; t < V; ++t) {
        p2[t]   = p2_of(t);
        tgt2[t] = target_of(p2[t]);
    }

    std::vector<llama_token_data> q1, q2, residual;
    std::vector<long> cnt(V*V, 0);
    long n_acc = 0;
    for (long s = 0; s < n; ++s) {
        // the draft path: position 1 from predecessor 0 (the anchor), position 2 from the drawn index
        float qp = 0.0f;
        const int i1 = common_speculative_dflash2_pick(r1.cand(), r1.scores(0),  K, temp, uni(rng_d), q1, qp);
        const int i2 = common_speculative_dflash2_pick(r2.cand(), r2.scores(i1), K, temp, uni(rng_d), q2, qp);
        const llama_token x1 = (llama_token) r1.cand()[i1];
        const llama_token x2 = (llama_token) r2.cand()[i2];

        bool acc1 = false, acc2 = false;
        const llama_token t1 = common_sampler_rejection_step(tgt1.data(), tgt1.size(), q1.data(), q1.size(), x1,
                tgt1[0].id, rng_t, residual, acc1);
        llama_token t2;
        if (acc1) {
            const auto & tg = tgt2[t1];
            t2 = common_sampler_rejection_step(tg.data(), tg.size(), q2.data(), q2.size(), x2, tg[0].id, rng_t,
                    residual, acc2);
        } else {
            // rejected at position 1: the next step samples position 2 from the target alone
            std::uniform_real_distribution<double> ud(0.0, 1.0);
            double u = ud(rng_t);
            t2 = V - 1;
            for (int t = 0; t < V; ++t) {
                u -= p2[t1][t];
                if (u <= 0.0 && p2[t1][t] > 0.0) {
                    t2 = t;
                    break;
                }
            }
        }
        cnt[t1*V + t2]++;
        n_acc += acc1 + (acc1 && acc2);
    }
    std::vector<double> pj(V*V);
    for (int a = 0; a < V; ++a) {
        for (int b = 0; b < V; ++b) {
            pj[a*V + b] = p1[a]*p2[a][b];
        }
    }
    int df = 0;
    const double pv = chi2_pvalue(pj, cnt, n, df);
    char buf[256];
    snprintf(buf, sizeof buf, "two positions, T=%.2f: joint ~ p1(t1) p2(t2|t1), chi2 p = %.4f (df %d), %.3f drafts accepted/step",
            temp, pv, df, (double) n_acc/n);
    check(pv > 1e-4, buf);
}

// the pick itself: draws follow q = softmax(scores / temp), q is normalized, a repeated id holds its total mass
static void test_pick(long n) {
    std::mt19937 rng(7);
    const toy_row row = make_row({ 3, 1, 4, 1, 5, 9 }, rng, 1.0f);
    std::uniform_real_distribution<float> uni(0.0f, 1.0f);
    for (const float temp : { 1.0f, 0.6f }) {
        std::vector<llama_token_data> q;
        float qp = 0.0f;
        std::vector<long> cnt(K, 0);
        for (long s = 0; s < n; ++s) {
            cnt[common_speculative_dflash2_pick(row.cand(), row.scores(2), K, temp, uni(rng), q, qp)]++;
        }
        // expected per index from the scores
        std::vector<double> e(K);
        double sum = 0.0, qsum = 0.0;
        for (int j = 0; j < K; ++j) {
            e[j] = std::exp((double) row.scores(2)[j]/temp);
            sum += e[j];
        }
        for (auto & v : e) {
            v /= sum;
        }
        for (const auto & x : q) {
            qsum += x.p;
        }
        int df = 0;
        const double pv = chi2_pvalue(e, cnt, n, df);
        char buf[256];
        snprintf(buf, sizeof buf, "pick T=%.1f: index ~ softmax(scores/T), chi2 p = %.4f; sum q = %.6f; q(id 1) = %.4f vs %.4f",
                temp, pv, qsum, q[1].p, e[1] + e[3]);
        check(pv > 1e-4 && std::fabs(qsum - 1.0) < 1e-5 && std::fabs(q[1].p - (e[1] + e[3])) < 1e-5 && q[3].p == 0.0f, buf);
    }
}

// power check: a q that is not the distribution the token was drawn from (drawn at T=0.4, q reported at T=1) must
// bias the output detectably, or the chi-square tests above prove nothing
static void test_power(const std::vector<double> & p, const toy_row & row, long n) {
    std::mt19937 rng_d(11), rng_t(13);
    std::uniform_real_distribution<float> uni(0.0f, 1.0f);
    const auto tgt = target_of(p);
    std::vector<llama_token_data> q, q_wrong, residual;
    std::vector<long> cnt(V, 0);
    for (long s = 0; s < n; ++s) {
        float qp = 0.0f;
        const int pick = common_speculative_dflash2_pick(row.cand(), row.scores(0), K, 0.4f, uni(rng_d), q, qp);
        common_speculative_dflash2_pick(row.cand(), row.scores(0), K, 1.0f, 0.5f, q_wrong, qp);
        bool accepted = false;
        cnt[common_sampler_rejection_step(tgt.data(), tgt.size(), q_wrong.data(), q_wrong.size(),
                (llama_token) row.cand()[pick], tgt[0].id, rng_t, residual, accepted)]++;
    }
    int df = 0;
    const double pv = chi2_pvalue(p, cnt, n, df);
    char buf[256];
    snprintf(buf, sizeof buf, "negative control (wrong q): chi2 p = %.2e must be < 1e-4", pv);
    check(pv < 1e-4, buf);
}

int main(int argc, char ** argv) {
    const long n = argc > 1 ? atol(argv[1]) : 200000;

    // the target: token 11 has no mass, tokens 8-10 are never among the draft's candidates
    std::vector<double> p = { 0.22, 0.15, 0.12, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.02, 0.0 };
    {
        double s = 0.0;
        for (double v : p) s += v;
        for (auto & v : p) v /= s;
    }

    std::mt19937 rng(99);
    printf("pick:\n");
    test_pick(n);

    printf("one position:\n");
    const toy_row near  = make_row({ 0, 1, 2, 3, 4, 5 },  rng, 0.5f);   // q close to p's head
    const toy_row far   = make_row({ 7, 6, 11, 0, 5, 2 }, rng, 2.0f);   // peaked q on low-p tokens, one p = 0 token
    const toy_row dup   = make_row({ 2, 0, 2, 4, 11, 1 }, rng, 1.0f);   // a repeated id
    test_one("near q, T=1",   p, near, 1.0f, n);
    test_one("near q, T=0.7", p, near, 0.7f, n);
    test_one("far q, T=1",    p, far,  1.0f, n);
    test_one("far q, T=1.5",  p, far,  1.5f, n);
    test_one("repeated id",   p, dup,  1.0f, n);

    printf("two positions:\n");
    const toy_row r1 = make_row({ 0, 1, 2, 3, 4, 5 }, rng, 1.0f);
    const toy_row r2 = make_row({ 6, 7, 1, 0, 9, 3 }, rng, 1.5f);
    test_two(p, r1, r2, 1.0f, n);
    test_two(p, r1, r2, 0.7f, n);

    printf("power:\n");
    test_power(p, far, n);

    printf(g_fail ? "%d FAILED\n" : "all passed\n", g_fail);
    return g_fail ? 1 : 0;
}
