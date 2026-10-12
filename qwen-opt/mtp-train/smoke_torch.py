"""Torch GPU smoke test: device info + bf16/fp32 matmul correctness and throughput."""
import time
import torch

assert torch.cuda.is_available(), "no ROCm device"
d = torch.device("cuda")
print("device:", torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).gcnArchName)
print("vram GB:", torch.cuda.get_device_properties(0).total_memory / 2**30)
torch.manual_seed(0)
a = torch.randn(4096, 4096, device=d)
b = torch.randn(4096, 4096, device=d)
ref = (a.double() @ b.double()).float()
for dt in (torch.float32, torch.bfloat16, torch.float16):
    x, y = a.to(dt), b.to(dt)
    z = x @ y
    torch.cuda.synchronize()
    rel = ((z.float() - ref).norm() / ref.norm()).item()
    n = 20
    t0 = time.time()
    for _ in range(n):
        z = x @ y
    torch.cuda.synchronize()
    dt_s = (time.time() - t0) / n
    print(f"{str(dt):15s} rel_err={rel:.2e}  {2 * 4096**3 / dt_s / 1e12:.1f} TFLOP/s")
