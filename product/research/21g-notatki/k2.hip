#include <hip/hip_runtime.h>
__device__ __forceinline__ void lds_barrier(){
  __builtin_amdgcn_fence(__ATOMIC_RELEASE, "workgroup", "local");
  __builtin_amdgcn_s_barrier();
  __builtin_amdgcn_fence(__ATOMIC_ACQUIRE, "workgroup", "local");
}
__global__ void k(const float* __restrict__ x, float* y){
  __shared__ float s[256];
  float v = x[threadIdx.x + blockIdx.x*256];
  s[threadIdx.x]=v;
  lds_barrier();
  float w = s[255-threadIdx.x];
  float u = x[threadIdx.x*7 + 1000];
  s[threadIdx.x]=w+u;
  lds_barrier();
  y[threadIdx.x]=s[(threadIdx.x+1)&255];
}
