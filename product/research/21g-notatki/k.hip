#include <hip/hip_runtime.h>
__global__ void k(const float* __restrict__ x, float* y){
  __shared__ float s[256];
  float v = x[threadIdx.x + blockIdx.x*256];
  s[threadIdx.x]=v;
  __syncthreads();
  float w = s[255-threadIdx.x];
  float u = x[threadIdx.x*7 + 1000];
  s[threadIdx.x]=w+u;
  __builtin_amdgcn_s_waitcnt(0xc07f); __builtin_amdgcn_s_barrier();
  y[threadIdx.x]=s[(threadIdx.x+1)&255];
}
