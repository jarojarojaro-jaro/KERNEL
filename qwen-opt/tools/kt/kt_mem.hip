// Device buffers shared by every harness variant loaded into one Kernel Tuner process (libkt_mem.so is loaded once,
// the variants link it): a slot keeps the device copy of a host array and re-uploads only when the host pointer, the
// size or the number of copies changes, so switching variants neither re-uploads the weights nor leaks VRAM.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <map>
#include <string>

namespace {
struct slot {
    const void * host = nullptr;
    size_t size = 0, pitch = 0;
    int copies = 0;
    char * dev = nullptr;
};
std::map<std::string, slot> g_slots;
}

// device pointer of copy 0 (copy c at + c*pitch) of host[0..n), ncopies identical copies, nullptr on error
extern "C" char * kt_dev(const char * name, const void * host, size_t n, int ncopies, size_t * pitch_out) {
    slot & s = g_slots[name];
    if (s.dev == nullptr || s.host != host || s.size != n || s.copies != ncopies) {
        if (s.dev) {
            (void) hipFree(s.dev);
            s.dev = nullptr;
        }
        s.pitch = (n + 255) & ~size_t(255);
        if (hipMalloc(&s.dev, s.pitch * ncopies) != hipSuccess) {
            fprintf(stderr, "kt_mem: hipMalloc of %zu bytes for %s failed\n", s.pitch * ncopies, name);
            s.dev = nullptr;
            return nullptr;
        }
        for (int c = 0; c < ncopies; ++c) {
            if (hipMemcpy(s.dev + c * s.pitch, host, n, hipMemcpyHostToDevice) != hipSuccess) {
                fprintf(stderr, "kt_mem: upload of %s failed\n", name);
                return nullptr;
            }
        }
        s.host = host; s.size = n; s.copies = ncopies;
    }
    if (pitch_out) {
        *pitch_out = s.pitch;
    }
    return s.dev;
}

extern "C" void kt_release_all() {
    for (auto & kv : g_slots) {
        if (kv.second.dev) {
            (void) hipFree(kv.second.dev);
        }
    }
    g_slots.clear();
}
