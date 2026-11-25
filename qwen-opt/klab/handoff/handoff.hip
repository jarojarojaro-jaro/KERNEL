// klab handoff — K-021 PoC-A: producer -> consumer hand-off inside a persistent grid vs kernel boundaries (plain HIP,
// no PM4 ring). Spec: ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:155 (row A); prior art X1 (PM4-PDL,
// 1024-3072 blocks): ~/qwen-opt/pm4pdl/x1/pdl_kern.hip, report 16a §1.
//
// Workload: a chain of N synthetic MMVQ stages shaped like Qwen verify MMVQ Q5_K n=5 (5 columns, 5120 input columns =
// 3520 B of weights per row, R output rows). Stage s reads the R x 5 byte output of stage s-1 (all-to-all dependency,
// like MMVQ -> norm -> MMVQ), builds its x in LDS with a redundant per-column "norm" (byte sum over the whole input,
// XORed into x), then computes y_s = W_s . x with v_dot4 (int, so every arm is bit-exact by definition).
//
// Arms (µs per stage = (T(n2) - T(n1)) / (n2 - n1), pairwise, so the launch of a persistent kernel cancels out):
//   S<G>   one kernel per stage, stream launches, G workgroups       (kernel boundary, plain HIP)
//   Gr<G>  the same N launches replayed from a HIP graph             (what the fork does with GGML_HIP_PM4=0)
//   O<G>   persistent G workgroups, no synchronisation (WRONG results) = lower bound "no boundary"
//   H1<G>pP   persistent, hand-off: thread 0 of every WG does one agent-scope release fetch_add on one monotonic
//             counter (128 B line) after its stores; consumers poll that counter (s_sleep 1, bounded)
//   H16<G>pP  persistent, ticket relay: the same single fetch_add (acq_rel); the WG that completes the count writes the
//             epoch into 16 flag copies (one per 128 B line); consumers poll copy blockIdx % 16
//   pP = weight rows of the next stage loaded into VGPRs before the wait (0, 1, 2 rows per wave)
//   E<G>   empty kernels, graph: the pure boundary cost
// Safety: every spin loop is bounded (maxit polls, then error word + global abort flag, all WGs bail out within 256
// polls); the host waits with a wall-clock watchdog and _exit(3)s (the KFD queue dies with the process); persistent
// arms refuse grids that are not co-resident (occupancy x CUs).
// Correctness: every timed run of a correct arm starts from ys = 0 and its full output (all stages) is compared
// bytewise with the stream-dispatch reference; the reference itself is checked against a CPU model on two stages.
//
// Verdict (kill criteria of K-021): handoff = H - O; gain_hip = min(S, Gr) - O; gain_pm4_est = pm4_ref + max(0,
// gain_hip - E) (PM4 boundary packets instead of the HIP boundary, the tail/ramp part stays) [estimate];
// KILL if handoff > 0.3 µs, or (gain - handoff) / gain < 30 % for gain_hip or gain_pm4_est.
//
// build: hipcc -O3 -std=c++17 --offload-arch=gfx1100 handoff.hip -o handoff
#include <hip/hip_runtime.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <thread>
#include <unistd.h>
#include <vector>

#define CK(x)                                                                                        \
    do {                                                                                             \
        hipError_t e_ = (x);                                                                         \
        if (e_ != hipSuccess) {                                                                      \
            fprintf(stderr, "HIP error %s at %s:%d: %s\n", hipGetErrorString(e_), __FILE__, __LINE__, #x); \
            _exit(2);                                                                                \
        }                                                                                            \
    } while (0)

constexpr int NC    = 5;                   // columns (verify batch rows)
constexpr int RW4   = 220;                 // uint4 per weight row: 5120 cols * 5.5 bit / 8 = 3520 B
constexpr int XD    = RW4 * 4;             // x dwords per column (3520 int8)
constexpr int NI    = (RW4 + 31) / 32;     // uint4 loads per lane per row (7)
constexpr int NT    = 256;
constexpr int NWAVE = NT / 32;
constexpr int NFLAG = 16;
constexpr int XI    = (XD + NT - 1) / NT;  // x dwords per thread per column (4)
constexpr size_t LDS_BYTES = (size_t) NC * RW4 * sizeof(uint4);

struct Args {
    const uint4 * w;      // P matrices, R x RW4 uint4
    const uint8_t * y0;   // stage-0 input, NC x R
    uint8_t * ys;         // stage outputs, N x NC x R
    uint32_t * sync;      // [0] counter, [32 + 32 q] flag copy q
    uint32_t * err;       // [0] timeouts, [32] abort
    int R, P, s0, ns;
    uint32_t base, maxit;
};

__device__ __forceinline__ int dot4(uint32_t w, uint32_t x, int acc) {
    return __builtin_amdgcn_sudot4(true, (int) w, true, (int) x, acc, false);
}

// column-outer, not unrolled: only one column of x (7 uint4) is live at a time, so a prefetched weight row fits in
// VGPRs without scratch (waves_per_eu 8)
__device__ __forceinline__ void do_row(const uint4 (&wr)[NI], const uint4 * xs, const uint32_t (&m)[NC], int row,
                                       uint8_t * yout, int R, int lane) {
#pragma unroll 1
    for (int c = 0; c < NC; ++c) {
        uint32_t mc = m[0];
#pragma unroll
        for (int q = 1; q < NC; ++q) mc = c == q ? m[q] : mc;
        int acc = 0;
#pragma unroll
        for (int i = 0; i < NI; ++i) {
            const int d = i * 32 + lane;
            if (d < RW4) {
                const uint4 x = xs[c * RW4 + d];
                acc = dot4(wr[i].x, x.x ^ mc, acc);
                acc = dot4(wr[i].y, x.y ^ mc, acc);
                acc = dot4(wr[i].z, x.z ^ mc, acc);
                acc = dot4(wr[i].w, x.w ^ mc, acc);
            }
        }
#pragma unroll
        for (int o = 16; o > 0; o >>= 1) acc += __shfl_xor(acc, o, 32);
        if (lane == 0) yout[(size_t) c * R + row] = (uint8_t) (acc ^ (acc >> 11));
    }
}

__device__ __forceinline__ void load_row(uint4 (&wr)[NI], const uint4 * W, int row, int lane) {
#pragma unroll
    for (int i = 0; i < NI; ++i) {
        const int d = i * 32 + lane;
        wr[i] = d < RW4 ? W[(size_t) row * RW4 + d] : make_uint4(0, 0, 0, 0);
    }
}

// MODE 0: persistent, no sync (O); 1: persistent, counter (H1); 2: persistent, ticket relay x16 (H16);
// 3: one stage per launch (S / Gr). PF: weight rows per wave loaded into VGPRs before the wait.
template <int MODE, int PF>
__global__ __launch_bounds__(NT) __attribute__((amdgpu_waves_per_eu(8))) void k_chain(Args a) {  // 2 WG/CU: G=192 co-resident
    extern __shared__ uint4 xs[];  // NC x RW4
    __shared__ int red[NWAVE][NC];
    const int tid = threadIdx.x, lane = tid & 31, wv = tid >> 5;
    const int G = gridDim.x, TW = G * NWAVE, gw = blockIdx.x * NWAVE + wv;
    const int R = a.R;
    for (int si = 0; si < a.ns; ++si) {
        const int s = a.s0 + si;
        const uint4 * W = a.w + (size_t) (s % a.P) * R * RW4;
        uint4 pf[PF > 0 ? PF : 1][NI];
        if (PF > 0) {
#pragma unroll
            for (int k = 0; k < PF; ++k) {
                const int row = gw + k * TW;
                if (row < R) load_row(pf[k], W, row, lane);
#pragma unroll
                for (int i = 0; i < NI; ++i) asm volatile("" : "+v"(pf[k][i].x), "+v"(pf[k][i].y), "+v"(pf[k][i].z), "+v"(pf[k][i].w));
            }
        }
        if ((MODE == 1 || MODE == 2) && si > 0) {
            if (tid == 0) {
                const uint32_t tgt = MODE == 1 ? (uint32_t) G * (a.base + s) : a.base + s;
                const uint32_t * p = MODE == 1 ? a.sync : a.sync + 32 + 32 * (blockIdx.x % NFLAG);
                uint32_t it = 0;
                while ((int32_t) (__hip_atomic_load(p, __ATOMIC_RELAXED, __HIP_MEMORY_SCOPE_AGENT) - tgt) < 0) {
                    __builtin_amdgcn_s_sleep(1);
                    if ((++it & 255) == 0) {
                        if (__hip_atomic_load(a.err + 32, __ATOMIC_RELAXED, __HIP_MEMORY_SCOPE_AGENT)) break;
                        if (it >= a.maxit) {
                            __hip_atomic_fetch_add(a.err, 1u, __ATOMIC_RELAXED, __HIP_MEMORY_SCOPE_AGENT);
                            __hip_atomic_store(a.err + 32, 1u, __ATOMIC_RELAXED, __HIP_MEMORY_SCOPE_AGENT);
                            break;
                        }
                    }
                }
            }
            __syncthreads();
            __builtin_amdgcn_fence(__ATOMIC_ACQUIRE, "agent");
        }
        // x = input bytes (index j % R; R % 4 == 0, so dword loads), "norm": per-column byte sum over the whole x,
        // XORed in. All loads of a thread are issued before the first use.
        const uint8_t * yin = s == 0 ? a.y0 : a.ys + (size_t) (s - 1) * NC * R;
        int part[NC];
#pragma unroll
        for (int c = 0; c < NC; ++c) part[c] = 0;
        uint32_t * xd = (uint32_t *) xs;
        uint32_t xv[XI][NC];
#pragma unroll
        for (int k = 0; k < XI; ++k) {
            const int d = tid + k * NT;
            const int j = (4 * d) % R;
#pragma unroll
            for (int c = 0; c < NC; ++c) xv[k][c] = d < XD ? *(const uint32_t *) (yin + (size_t) c * R + j) : 0u;
        }
#pragma unroll
        for (int k = 0; k < XI; ++k) {
            const int d = tid + k * NT;
#pragma unroll
            for (int c = 0; c < NC; ++c) {
                const uint32_t v = xv[k][c];
                if (d < XD) xd[c * XD + d] = v;
                part[c] += (int) ((v & 0xff) + ((v >> 8) & 0xff) + ((v >> 16) & 0xff) + (v >> 24));
            }
        }
#pragma unroll
        for (int c = 0; c < NC; ++c) {
#pragma unroll
            for (int o = 16; o > 0; o >>= 1) part[c] += __shfl_xor(part[c], o, 32);
            if (lane == 0) red[wv][c] = part[c];
        }
        __syncthreads();
        uint32_t m[NC];
#pragma unroll
        for (int c = 0; c < NC; ++c) {
            int S = 0;
#pragma unroll
            for (int q = 0; q < NWAVE; ++q) S += red[q][c];
            m[c] = (uint32_t) (S & 0xff) * 0x01010101u;
        }
        uint8_t * yout = a.ys + (size_t) s * NC * R;
#pragma unroll
        for (int k = 0; k < PF; ++k) {
            const int row = gw + k * TW;
            if (row < R) do_row(pf[k], xs, m, row, yout, R, lane);
        }
        for (int row = gw + PF * TW; row < R; row += TW) {
            uint4 wr[NI];
            load_row(wr, W, row, lane);
            do_row(wr, xs, m, row, yout, R, lane);
        }
        __syncthreads();  // LDS reuse by the next stage; all stores of the WG issued before the signal
        if ((MODE == 1 || MODE == 2) && tid == 0) {
            if (MODE == 1) {
                __hip_atomic_fetch_add(a.sync, 1u, __ATOMIC_RELEASE, __HIP_MEMORY_SCOPE_AGENT);
            } else {
                const uint32_t e   = a.base + s + 1;
                const uint32_t old = __hip_atomic_fetch_add(a.sync, 1u, __ATOMIC_ACQ_REL, __HIP_MEMORY_SCOPE_AGENT);
                if (old + 1 == (uint32_t) G * e) {
                    for (int q = 0; q < NFLAG; ++q)
                        __hip_atomic_store(a.sync + 32 + 32 * q, e, __ATOMIC_RELEASE, __HIP_MEMORY_SCOPE_AGENT);
                }
            }
        }
    }
}

__global__ void k_empty() {}

__global__ void k_fill(uint32_t * p, size_t n, uint32_t seed) {
    for (size_t i = blockIdx.x * (size_t) blockDim.x + threadIdx.x; i < n; i += (size_t) gridDim.x * blockDim.x) {
        uint32_t h = (uint32_t) i * 0x9E3779B1u ^ seed;
        h ^= h >> 15; h *= 0x85EBCA77u; h ^= h >> 13; h *= 0xC2B2AE3Du; h ^= h >> 16;
        p[i] = h;
    }
}

// ------------------------------------------------------------------------------------------------------------ host
static int8_t sb(uint32_t v, int b) { return (int8_t) ((v >> (8 * b)) & 0xff); }

// CPU model of one stage (same arithmetic as the kernel), rows [0, R)
static void cpu_stage(const std::vector<uint32_t> & W, const uint8_t * yin, uint8_t * yout, int R) {
    std::vector<uint32_t> x((size_t) NC * XD);
    for (int c = 0; c < NC; ++c) {
        int S = 0;
        for (int d = 0; d < XD; ++d) {
            uint32_t v = 0;
            for (int b = 0; b < 4; ++b) v |= (uint32_t) yin[(size_t) c * R + (4 * d + b) % R] << (8 * b);
            x[(size_t) c * XD + d] = v;
            S += (v & 0xff) + ((v >> 8) & 0xff) + ((v >> 16) & 0xff) + (v >> 24);
        }
        const uint32_t m = (uint32_t) (S & 0xff) * 0x01010101u;
        for (int d = 0; d < XD; ++d) x[(size_t) c * XD + d] ^= m;
    }
    for (int r = 0; r < R; ++r)
        for (int c = 0; c < NC; ++c) {
            int acc = 0;
            for (int d = 0; d < XD; ++d) {
                const uint32_t w = W[(size_t) r * XD + d], xv = x[(size_t) c * XD + d];
                for (int b = 0; b < 4; ++b) acc += (int) sb(w, b) * (int) sb(xv, b);
            }
            yout[(size_t) c * R + r] = (uint8_t) (acc ^ (acc >> 11));
        }
}

struct Opt {
    bool smoke = false;
    std::vector<int> rows = {5120, 1024};
    std::vector<int> grids = {96, 192};
    int n1 = 40, n2 = 200, trials = 15;
    uint32_t maxit = 1u << 18;
    double pm4_ref = 0.46, kill_us = 0.30, kill_frac = 0.30, watchdog_s = 20.0;
};

static std::vector<int> parse_list(const char * s) {
    std::vector<int> v;
    for (const char * p = s; *p;) {
        v.push_back(atoi(p));
        while (*p && *p != ',') ++p;
        if (*p == ',') ++p;
    }
    return v;
}

struct Arm {
    std::string name;
    int kind;  // 0 stream, 1 graph, 2 persistent, 3 empty graph
    int mode, pf, G;
    bool checked;  // output must equal the reference
    std::vector<double> us;
    long mism = 0, runs = 0, timeouts = 0;
    bool skip = false;
    hipGraphExec_t gx[2] = {nullptr, nullptr};
};

static double median(std::vector<double> v, double q = 0.5) {
    if (v.empty()) return NAN;
    std::sort(v.begin(), v.end());
    const double i = q * (v.size() - 1);
    const size_t lo = (size_t) i, hi = std::min(lo + 1, v.size() - 1);
    return v[lo] + (v[hi] - v[lo]) * (i - lo);
}

typedef void (*kfn)(Args);
static kfn kern(int mode, int pf) {
    switch (mode * 4 + pf) {
        case 0: return k_chain<0, 0>;
        case 4: return k_chain<1, 0>;
        case 5: return k_chain<1, 1>;
        case 6: return k_chain<1, 2>;
        case 8: return k_chain<2, 0>;
        case 9: return k_chain<2, 1>;
        case 10: return k_chain<2, 2>;
        case 12: return k_chain<3, 0>;
    }
    fprintf(stderr, "bad kernel %d %d\n", mode, pf);
    _exit(2);
}

static void wait_ev(hipEvent_t e, double limit_s, const char * what) {
    const auto t0 = std::chrono::steady_clock::now();
    for (;;) {
        const hipError_t r = hipEventQuery(e);
        if (r == hipSuccess) return;
        if (r != hipErrorNotReady) { fprintf(stderr, "HIP error %s while waiting (%s)\n", hipGetErrorString(r), what); _exit(2); }
        if (std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count() > limit_s) {
            printf("WATCHDOG: %s did not finish in %.0f s -> exit 3 (queue dies with the process)\nVERDICT K-021 PoC-A: INVALID (host watchdog)\n", what, limit_s);
            fflush(stdout);
            _exit(3);
        }
        std::this_thread::sleep_for(std::chrono::microseconds(200));
    }
}

int main(int argc, char ** argv) {
    Opt o;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto nx = [&]() { if (i + 1 >= argc) { fprintf(stderr, "missing value for %s\n", a.c_str()); exit(2); } return argv[++i]; };
        if (a == "--smoke") { o.smoke = true; o.rows = {1024}; o.grids = {96}; o.n1 = 2; o.n2 = 6; o.trials = 2; o.maxit = 1u << 16; }
        else if (a == "--rows") o.rows = parse_list(nx());
        else if (a == "--grids") o.grids = parse_list(nx());
        else if (a == "--n1") o.n1 = atoi(nx());
        else if (a == "--n2") o.n2 = atoi(nx());
        else if (a == "--trials") o.trials = atoi(nx());
        else if (a == "--maxit") o.maxit = (uint32_t) atol(nx());
        else if (a == "--pm4-ref") o.pm4_ref = atof(nx());
        else if (a == "--watchdog") o.watchdog_s = atof(nx());
        else { fprintf(stderr, "usage: %s [--smoke] [--rows 5120,1024] [--grids 96,192] [--n1 40] [--n2 200] [--trials 15] [--maxit 262144] [--pm4-ref 0.46] [--watchdog 20]\n", argv[0]); return 2; }
    }
    if (o.n2 <= o.n1 || o.n1 < 1) { fprintf(stderr, "need 1 <= n1 < n2\n"); return 2; }

    hipDeviceProp_t prop;
    CK(hipGetDeviceProperties(&prop, 0));
    const char * pm4 = getenv("GGML_HIP_PM4");
    printf("device %s (%s), %d CUs, GGML_HIP_PM4=%s (this bench never uses the PM4 ring)\n", prop.name, prop.gcnArchName,
           prop.multiProcessorCount, pm4 ? pm4 : "(unset)");
    printf("opts: rows %s grids %s n1 %d n2 %d trials %d maxit %u pm4_ref %.2f us, kill: handoff > %.2f us or retained < %.0f%%\n",
           [&] { std::string s; for (int r : o.rows) s += std::to_string(r) + " "; return s; }().c_str(),
           [&] { std::string s; for (int g : o.grids) s += std::to_string(g) + " "; return s; }().c_str(), o.n1, o.n2, o.trials,
           o.maxit, o.pm4_ref, o.kill_us, 100 * o.kill_frac);

    hipStream_t st;
    CK(hipStreamCreateWithFlags(&st, hipStreamNonBlocking));
    hipEvent_t e0, e1;
    CK(hipEventCreate(&e0));
    CK(hipEventCreate(&e1));
    uint32_t * sync;  // counter + 16 flag lines
    uint32_t * err;
    CK(hipMalloc(&sync, 32 * 4 * (NFLAG + 1)));
    CK(hipMalloc(&err, 64 * 4));
    for (int mode = 0; mode < 4; ++mode)
        for (int pf = 0; pf < 3; ++pf) {
            if ((mode == 0 || mode == 3) && pf) continue;
            CK(hipFuncSetAttribute((const void *) kern(mode, pf), hipFuncAttributeMaxDynamicSharedMemorySize, (int) LDS_BYTES));
        }

    int overall = -1;  // -1 invalid, 0 kill, 1 pass (primary shape = first --rows)
    std::string overall_why;
    for (size_t ri = 0; ri < o.rows.size(); ++ri) {
        const int R = o.rows[ri];
        if (R % 4 || R < 8) { fprintf(stderr, "rows must be a multiple of 4\n"); return 2; }
        const size_t mat_dw = (size_t) R * XD;
        const size_t mat_b  = mat_dw * 4;
        int P = (int) std::min<size_t>((size_t) o.n2, ((size_t) 256 << 20) / mat_b + 1);  // > 96 MB Infinity Cache
        P = std::max(P, 1);
        uint32_t * w;
        uint8_t *y0, *ys;
        const size_t ys_b = (size_t) o.n2 * NC * R;
        CK(hipMalloc(&w, mat_b * P));
        CK(hipMalloc(&y0, (size_t) NC * R));
        CK(hipMalloc(&ys, ys_b));
        k_fill<<<1024, 256, 0, st>>>(w, mat_dw * P, 0x1234u + R);
        k_fill<<<64, 256, 0, st>>>((uint32_t *) y0, (size_t) NC * R / 4, 0x777u + R);
        CK(hipStreamSynchronize(st));
        printf("\n=== shape r%d x c5120 Q5_K-shaped n=%d: %.2f MB per matvec, %d matrices (%.0f MB) in rotation\n", R, NC,
               mat_b / 1e6, P, mat_b * P / 1e6);

        uint32_t epoch = 0;  // stages signalled since the last sync reset
        auto reset_sync = [&]() {
            CK(hipMemsetAsync(sync, 0, 32 * 4 * (NFLAG + 1), st));
            CK(hipMemsetAsync(err, 0, 64 * 4, st));
            CK(hipStreamSynchronize(st));
            epoch = 0;
        };
        reset_sync();
        auto args = [&](int s0, int ns) {
            Args a{(const uint4 *) w, y0, ys, sync, err, R, P, s0, ns, epoch, o.maxit};
            return a;
        };
        auto enqueue = [&](Arm & A, int n, int idx) {
            if (A.kind == 0) {
                for (int s = 0; s < n; ++s) hipLaunchKernelGGL(kern(3, 0), dim3(A.G), dim3(NT), LDS_BYTES, st, args(s, 1));
            } else if (A.kind == 1 || A.kind == 3) {
                CK(hipGraphLaunch(A.gx[idx], st));
            } else {
                hipLaunchKernelGGL(kern(A.mode, A.pf), dim3(A.G), dim3(NT), LDS_BYTES, st, args(0, n));
                if (A.mode) epoch += n;
            }
            CK(hipGetLastError());
        };

        // arms
        std::vector<Arm> arms;
        const int Gnat = (R + NWAVE - 1) / NWAVE;  // one row per wave, like a plain MMVQ grid
        std::vector<int> dgrids = o.grids;
        if (std::find(dgrids.begin(), dgrids.end(), Gnat) == dgrids.end()) dgrids.push_back(Gnat);
        for (int G : dgrids) {
            arms.push_back({"S" + std::to_string(G), 0, 3, 0, G, true});
            arms.push_back({"Gr" + std::to_string(G), 1, 3, 0, G, true});
        }
        for (int G : o.grids) {
            arms.push_back({"E" + std::to_string(G), 3, 3, 0, G, false});
            for (int mode = 0; mode <= 2; ++mode)
                for (int pf = 0; pf <= 2; ++pf) {
                    if (mode == 0 && pf) continue;
                    const std::string name = mode == 0 ? "O" + std::to_string(G)
                        : std::string(mode == 1 ? "H1-" : "H16-") + std::to_string(G) + "p" + std::to_string(pf);
                    int occ = 0;
                    CK(hipOccupancyMaxActiveBlocksPerMultiprocessor(&occ, (const void *) kern(mode, pf), NT, LDS_BYTES));
                    const int cap = occ * prop.multiProcessorCount;
                    if (G > cap) {
                        printf("%s: occupancy %d WG/CU x %d CUs = %d resident < %d -> SKIPPED (not co-resident)\n", name.c_str(),
                               occ, prop.multiProcessorCount, cap, G);
                        continue;
                    }
                    arms.push_back({name, 2, mode, pf, G, mode != 0});
                }
        }
        // graphs
        for (Arm & A : arms) {
            if (A.kind != 1 && A.kind != 3) continue;
            for (int idx = 0; idx < 2; ++idx) {
                const int n = idx ? o.n2 : o.n1;
                hipGraph_t g;
                CK(hipStreamBeginCapture(st, hipStreamCaptureModeRelaxed));
                for (int s = 0; s < n; ++s) {
                    if (A.kind == 1) hipLaunchKernelGGL(kern(3, 0), dim3(A.G), dim3(NT), LDS_BYTES, st, args(s, 1));
                    else hipLaunchKernelGGL(k_empty, dim3(A.G), dim3(NT), 0, st);
                }
                CK(hipStreamEndCapture(st, &g));
                CK(hipGraphInstantiate(&A.gx[idx], g, nullptr, nullptr, 0));
                CK(hipGraphDestroy(g));
            }
        }

        // reference = one stage per launch (kernel boundaries), checked against the CPU model on stages 0 and n2-1
        std::vector<uint8_t> ref(ys_b), out(ys_b);
        CK(hipMemsetAsync(ys, 0, ys_b, st));
        CK(hipEventRecord(e0, st));
        enqueue(arms[0], o.n2, 1);
        CK(hipEventRecord(e1, st));
        wait_ev(e1, o.watchdog_s, "reference chain");
        CK(hipMemcpy(ref.data(), ys, ys_b, hipMemcpyDeviceToHost));
        {
            std::vector<uint8_t> y0h((size_t) NC * R), cy((size_t) NC * R);
            CK(hipMemcpy(y0h.data(), y0, y0h.size(), hipMemcpyDeviceToHost));
            std::vector<uint32_t> Wh(mat_dw);
            long bad = 0;
            for (int s : {0, o.n2 - 1}) {
                CK(hipMemcpy(Wh.data(), w + (size_t) (s % P) * mat_dw, mat_b, hipMemcpyDeviceToHost));
                cpu_stage(Wh, s ? ref.data() + (size_t) (s - 1) * NC * R : y0h.data(), cy.data(), R);
                for (size_t i = 0; i < cy.size(); ++i) bad += cy[i] != ref[(size_t) s * NC * R + i];
            }
            printf("reference vs CPU model (stages 0 and %d): %ld mismatching bytes%s\n", o.n2 - 1, bad, bad ? "  ** FAIL **" : "");
            if (bad) {
                printf("VERDICT K-021 PoC-A: INVALID (reference kernel differs from CPU model)\n");
                return 1;
            }
        }

        // trials: every arm measures T(n1) and T(n2), arms rotate their start position per trial
        for (int t = 0; t < o.trials; ++t) {
            for (size_t k = 0; k < arms.size(); ++k) {
                Arm & A = arms[(k + t) % arms.size()];
                if (A.skip) continue;
                double ms[2];
                for (int idx = 0; idx < 2; ++idx) {
                    const int n = idx ? o.n2 : o.n1;
                    if (A.kind != 3) CK(hipMemsetAsync(ys, 0, ys_b, st));
                    CK(hipEventRecord(e0, st));
                    enqueue(A, n, idx);
                    CK(hipEventRecord(e1, st));
                    wait_ev(e1, o.watchdog_s, A.name.c_str());
                    float f;
                    CK(hipEventElapsedTime(&f, e0, e1));
                    ms[idx] = f;
                    if (A.kind == 2 && A.mode) {
                        uint32_t eh[33];
                        CK(hipMemcpy(eh, err, sizeof(eh), hipMemcpyDeviceToHost));
                        if (eh[0] || eh[32]) {
                            printf("  %s: %u poll timeouts (abort %u) -> arm excluded, sync reset\n", A.name.c_str(), eh[0], eh[32]);
                            A.timeouts += eh[0] ? eh[0] : 1;
                            A.skip = true;
                            reset_sync();
                        }
                    }
                    if (A.kind != 3 && idx == 1) {
                        CK(hipMemcpy(out.data(), ys, ys_b, hipMemcpyDeviceToHost));
                        long bad = 0;
                        for (size_t i = 0; i < ys_b; ++i) bad += out[i] != ref[i];
                        A.mism += bad;
                        A.runs++;
                        if (bad && A.checked) printf("  %s: %ld mismatching bytes in trial %d  ** FAIL **\n", A.name.c_str(), bad, t);
                    }
                }
                A.us.push_back((ms[1] - ms[0]) * 1e3 / (o.n2 - o.n1));
            }
        }

        // report
        printf("%-12s %9s %9s %9s  %s\n", "arm", "us/stage", "p25", "p75", "check");
        for (Arm & A : arms) {
            const bool bad = A.mism || A.timeouts;
            printf("%-12s %9.3f %9.3f %9.3f  %s\n", A.name.c_str(), median(A.us), median(A.us, 0.25), median(A.us, 0.75),
                   A.kind == 3 ? "empty kernels (boundary only)"
                   : !A.checked ? (std::to_string(A.mism) + " mismatching bytes over " + std::to_string(A.runs) + " runs (expected: no sync)").c_str()
                   : bad ? ("FAIL: " + std::to_string(A.mism) + " mismatching bytes, " + std::to_string(A.timeouts) + " timeouts").c_str()
                   : ("bit-exact, " + std::to_string(A.runs) + " runs").c_str());
        }
        double tB = 1e30;
        std::string bname;
        for (Arm & A : arms)
            if ((A.kind == 0 || A.kind == 1) && !A.mism && median(A.us) < tB) { tB = median(A.us); bname = A.name; }
        int shape_v = -1;
        std::string shape_why = "no valid hand-off arm";
        for (int G : o.grids) {
            const Arm *O = nullptr, *E = nullptr, *H = nullptr;
            for (Arm & A : arms) {
                if (A.G != G) continue;
                if (A.kind == 2 && A.mode == 0) O = &A;
                if (A.kind == 3) E = &A;
                if (A.kind == 2 && A.mode && !A.mism && !A.timeouts && !A.skip && (!H || median(A.us) < median(H->us))) H = &A;
            }
            if (!O || !H || !E) {
                printf("G=%d: no verdict (%s)\n", G, !O ? "persistent arms skipped" : !E ? "no empty arm" : "every hand-off arm failed");
                continue;
            }
            const double tO = median(O->us), tH = median(H->us), tE = median(E->us);
            const double handoff = tH - tO, gain_hip = tB - tO, tail = std::max(0.0, gain_hip - tE);
            const double gain_pm4 = o.pm4_ref + tail;
            const double ret_hip = gain_hip > 0 ? (gain_hip - handoff) / gain_hip : -1;
            const double ret_pm4 = (gain_pm4 - handoff) / gain_pm4;
            std::string why;
            if (handoff > o.kill_us) why += "handoff " + std::to_string(handoff).substr(0, 5) + " us > " + std::to_string(o.kill_us).substr(0, 4) + "; ";
            if (ret_hip < o.kill_frac) why += "retained vs HIP boundary " + std::to_string((int) (100 * ret_hip)) + "% < 30%; ";
            if (ret_pm4 < o.kill_frac) why += "retained vs PM4 estimate " + std::to_string((int) (100 * ret_pm4)) + "% < 30%; ";
            const int v = why.empty() ? 1 : 0;
            printf("G=%d: best hand-off %s %.3f us, O %.3f us -> handoff %.3f us/stage; boundary best %s %.3f us -> gain_hip %.3f us "
                   "(retained %.0f%%); empty-kernel boundary %.3f us, tail/ramp %.3f us -> gain_pm4_est %.3f us (retained %.0f%%) [estimate]: %s%s\n",
                   G, H->name.c_str(), tH, tO, handoff, bname.c_str(), tB, gain_hip, 100 * ret_hip, tE, tail, gain_pm4, 100 * ret_pm4,
                   v ? "PASS" : "KILL: ", why.c_str());
            if (v > shape_v) { shape_v = v; shape_why = H->name + (v ? " handoff " + std::to_string(handoff).substr(0, 5) + " us" : ": " + why); }
            else if (shape_v == 0 && v == 0) shape_why += " | " + H->name + ": " + why;
        }
        printf("VERDICT r%d: %s (%s)\n", R, shape_v == 1 ? "PASS" : shape_v == 0 ? "KILL" : "INVALID", shape_why.c_str());
        if (ri == 0) { overall = shape_v; overall_why = "r" + std::to_string(R) + ": " + shape_why; }

        for (Arm & A : arms)
            for (auto & g : A.gx)
                if (g) CK(hipGraphExecDestroy(g));
        CK(hipFree(w));
        CK(hipFree(y0));
        CK(hipFree(ys));
    }
    printf("\nVERDICT K-021 PoC-A%s: %s (%s)\n", o.smoke ? " [SMOKE, not a measurement]" : "",
           overall == 1 ? "PASS" : overall == 0 ? "KILL" : "INVALID", overall_why.c_str());
    return overall < 0 ? 1 : 0;
}
