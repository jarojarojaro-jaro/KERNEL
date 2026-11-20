// K-108: FP16 GEMM peak (hipBLAS GemmEx f16 in/out, f32 compute) + hipMemcpy D2D bandwidth on the RX 7900 XTX.
#include <hip/hip_runtime.h>
#include <hipblas/hipblas.h>
#include <cstdio>
#include <vector>
#include <algorithm>
#define CK(x) do { auto e = (x); if (e) { printf("err %d at %s:%d\n", (int) e, __FILE__, __LINE__); return 1; } } while (0)
int gemm(hipblasHandle_t h, int n, int reps) {
    void *a, *b, *c; size_t bytes = (size_t) n * n * 2;
    CK(hipMalloc(&a, bytes)); CK(hipMalloc(&b, bytes)); CK(hipMalloc(&c, bytes));
    CK(hipMemset(a, 0x3c, bytes)); CK(hipMemset(b, 0x3c, bytes));  // 0x3c3c = ~1.06 in f16
    float al = 1.0f, be = 0.0f; hipEvent_t e0, e1; CK(hipEventCreate(&e0)); CK(hipEventCreate(&e1));
    std::vector<float> ms;
    for (int r = 0; r < reps + 2; ++r) {
        CK(hipEventRecord(e0));
        CK(hipblasGemmEx(h, HIPBLAS_OP_N, HIPBLAS_OP_T, n, n, n, &al, a, HIPBLAS_R_16F, n, b, HIPBLAS_R_16F, n, &be, c,
                         HIPBLAS_R_16F, n, HIPBLAS_COMPUTE_32F, HIPBLAS_GEMM_DEFAULT));
        CK(hipEventRecord(e1)); CK(hipEventSynchronize(e1));
        float t; CK(hipEventElapsedTime(&t, e0, e1)); if (r >= 2) ms.push_back(t);
    }
    std::sort(ms.begin(), ms.end());
    double fl = 2.0 * n * n * (double) n;
    printf("gemm f16 %d^3: min %.3f ms -> %.1f TFLOPS, median %.3f ms -> %.1f TFLOPS (n=%d)\n", n, ms[0], fl / ms[0] / 1e9,
           ms[ms.size() / 2], fl / ms[ms.size() / 2] / 1e9, reps);
    hipFree(a); hipFree(b); hipFree(c); return 0;
}
int main() {
    hipblasHandle_t h; CK(hipblasCreate(&h));
    if (gemm(h, 4096, 50) || gemm(h, 8192, 20)) return 1;
    size_t bytes = 4ull << 30; void *s, *d; CK(hipMalloc(&s, bytes)); CK(hipMalloc(&d, bytes)); CK(hipMemset(s, 1, bytes));
    hipEvent_t e0, e1; CK(hipEventCreate(&e0)); CK(hipEventCreate(&e1)); std::vector<float> ms;
    for (int r = 0; r < 12; ++r) {
        CK(hipEventRecord(e0)); CK(hipMemcpy(d, s, bytes, hipMemcpyDeviceToDevice)); CK(hipEventRecord(e1));
        CK(hipEventSynchronize(e1)); float t; CK(hipEventElapsedTime(&t, e0, e1)); if (r >= 2) ms.push_back(t);
    }
    std::sort(ms.begin(), ms.end());
    printf("hipMemcpy D2D 4 GiB: min %.2f ms -> %.0f GB/s copy (%.0f GB/s read+write), median %.2f ms\n", ms[0],
           bytes / ms[0] / 1e6, 2.0 * bytes / ms[0] / 1e6, ms[ms.size() / 2]);
    return 0;
}
