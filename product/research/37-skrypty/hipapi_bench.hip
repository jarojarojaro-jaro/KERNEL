// Report 37 item #4: host cost of the HIP calls in the speculative step's host gap, on an idle stream.
//   sync      hipStreamSynchronize on an idle stream
//   query     hipStreamQuery on an idle stream
//   h2d N     pinned H2D hipMemcpyAsync of N bytes + a 1-block kernel (the input-batch scatter) + stream sync
//   d2h N     a 1-block kernel + pinned D2H hipMemcpyAsync of N bytes + stream sync (result readback)
// Run twice: default and GPU_FORCE_BLIT_COPY_SIZE=1024 (copies < 1 MiB by blit kernel instead of SDMA).
// Build: hipcc -O2 --offload-arch=gfx1100 hipapi_bench.hip -o hipapi_bench
#include <hip/hip_runtime.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <vector>

#define CK(x) do { hipError_t e = (x); if (e != hipSuccess) { printf("%s: %s\n", #x, hipGetErrorString(e)); return 1; } } while (0)

__global__ void touch(char * p) { if (threadIdx.x == 0) p[0] ^= 1; }

static double now_us() {
    return std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

template <typename F> static double med_us(int n, F f) {
    std::vector<double> v(n);
    for (int i = 0; i < n; ++i) { const double t = now_us(); f(); v[i] = now_us() - t; }
    std::sort(v.begin(), v.end());
    return v[n / 2];
}

int main() {
    hipStream_t s;
    CK(hipStreamCreateWithFlags(&s, hipStreamNonBlocking));
    char * h; char * d;
    CK(hipHostMalloc((void **) &h, 1 << 20, hipHostMallocDefault));
    CK(hipMalloc((void **) &d, 1 << 20));
    touch<<<1, 64, 0, s>>>(d);
    CK(hipStreamSynchronize(s));
    const int n = 2000;
    printf("sync idle      %7.2f us\n", med_us(n, [&] { (void) hipStreamSynchronize(s); }));
    printf("query idle     %7.2f us\n", med_us(n, [&] { (void) hipStreamQuery(s); }));
    printf("kernel+sync    %7.2f us\n", med_us(n, [&] { touch<<<1, 64, 0, s>>>(d); (void) hipStreamSynchronize(s); }));
    for (int sz : {1024, 8192, 32768, 102400}) {
        printf("h2d %6d     %7.2f us\n", sz, med_us(n, [&] {
            (void) hipMemcpyAsync(d, h, sz, hipMemcpyHostToDevice, s); touch<<<1, 64, 0, s>>>(d); (void) hipStreamSynchronize(s); }));
    }
    for (int sz : {1024, 8192, 65536}) {
        printf("d2h %6d     %7.2f us\n", sz, med_us(n, [&] {
            touch<<<1, 64, 0, s>>>(d); (void) hipMemcpyAsync(h, d, sz, hipMemcpyDeviceToHost, s); (void) hipStreamSynchronize(s); }));
    }
    return 0;
}
