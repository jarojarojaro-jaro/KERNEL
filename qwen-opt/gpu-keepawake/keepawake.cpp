#include <hip/hip_runtime.h>
#include <cstdio>
#include <unistd.h>

// Holds a KFD context so amdgpu runtime PM cannot suspend the GPU
// (kfd takes a pm_runtime reference for every bound process).
int main() {
    if (hipFree(nullptr) != hipSuccess) return 1;
    std::puts("gpu held awake");
    std::fflush(stdout);
    for (;;) pause();
}
