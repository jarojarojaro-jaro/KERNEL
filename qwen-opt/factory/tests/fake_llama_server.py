#!/usr/bin/env python3
"""CPU stand-in for llama-server (tests only): /health, /props, /v1/chat/completions with llama.cpp-shaped timings
and logprobs. Speed: FAKE_MS_STEP ms per step, x (1 - FAKE_EFFECT/100) when the test switch is on; deterministic
text from the prompt and seed (identical across builds, so BIT holds). Prints 'foo_on' when the switch is on and
GGML_HIP_PM4_DEBUG is set (probe)."""
import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SWITCH = "GGML_HIP_TESTSW"
port = int(sys.argv[sys.argv.index("--port") + 1])
on = os.environ.get(SWITCH) == "1"
ms_step = float(os.environ.get("FAKE_MS_STEP", "27.74")) * ((1 - float(os.environ.get("FAKE_EFFECT", "0.5")) / 100)
                                                            if on else 1.0)
if on and os.environ.get("GGML_HIP_PM4_DEBUG"):
    print("pm4trace foo_on dispatch", flush=True)
print("main: server is listening on http://127.0.0.1:%d" % port, flush=True)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            self.send({"status": "ok"})
        elif self.path == "/props":
            self.send({"build_info": "b8000-fake"})
        else:
            self.send_error(404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        n = int(body.get("max_tokens", 16))
        key = json.dumps(body.get("messages")) + str(body.get("seed")) + str(body.get("temperature"))
        h = hashlib.sha256(key.encode()).hexdigest()
        acc_rate = 0.5 + int(h[:2], 16) / 1024
        accepted = int(n * acc_rate * 0.6)
        steps = n - accepted
        resp = {"choices": [{"message": {"content": "fake text " + h[:32]}}],
                "timings": {"predicted_n": n, "predicted_ms": steps * ms_step, "draft_n": int(accepted / acc_rate),
                            "draft_n_accepted": accepted, "predicted_per_second": 1000 * n / (steps * ms_step)}}
        if body.get("logprobs"):
            resp["choices"][0]["logprobs"] = {"content": [
                {"id": i, "token": f"t{i}", "logprob": -0.1,
                 "top_logprobs": [{"id": i, "token": f"t{i}", "logprob": -0.1},
                                  {"id": i + 1, "token": f"t{i + 1}", "logprob": -2.0}]} for i in range(min(n, 32))]}
        self.send(resp)


ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
