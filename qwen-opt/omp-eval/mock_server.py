#!/usr/bin/env python3
"""Scripted OpenAI-compatible chat server for proving the omp-eval pipeline without a GPU.

A script (JSON) holds rules: {"match": "<substring of the first user message>", "steps": [step, ...]}.
The reply to a request is step N of the first matching rule, N = number of assistant messages already in the
history, so a rule replays a fixed tool-call sequence across omp's turns. A step is either
{"tool": "<name>", "args": {...}} (one tool call) or {"text": "..."} (final answer). Past the last step, or with no
matching rule, the server answers with plain text "done." (ends the agent loop).
Every request body is appended to --log (JSONL) so the wire format omp sends can be inspected.
Usage: mock_server.py --port 18799 --script mock_script.json [--model mock-model] [--log requests.jsonl]
"""
import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=18799)
ap.add_argument("--script", required=True)
ap.add_argument("--model", default="mock-model")
ap.add_argument("--log")
A = ap.parse_args()
RULES = json.load(open(A.script))


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


def pick(messages):
    users = [text_of(m.get("content")) for m in messages if m.get("role") == "user"]
    first = users[0] if users else ""
    n = sum(1 for m in messages if m.get("role") == "assistant")
    for r in RULES:
        if r["match"] in first:
            return r["steps"][n] if n < len(r["steps"]) else {"text": "done."}
    return {"text": "done."}


def usage(body, completion_tokens):
    prompt = len(json.dumps(body.get("messages", []))) // 4 + len(json.dumps(body.get("tools", []))) // 4
    return {"prompt_tokens": prompt, "completion_tokens": completion_tokens,
            "total_tokens": prompt + completion_tokens}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self.send_json({"object": "list", "data": [{"id": A.model, "object": "model", "owned_by": "mock"}]})
        if self.path.startswith("/health"):
            return self.send_json({"status": "ok"})
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if A.log:
            with open(A.log, "a") as f:
                f.write(json.dumps({"path": self.path, "body": body}) + "\n")
        if not self.path.rstrip("/").endswith("/chat/completions"):
            return self.send_json({"error": "only /v1/chat/completions"}, 404)
        step = pick(body.get("messages", []))
        cid, now = "chatcmpl-" + uuid.uuid4().hex[:12], int(time.time())
        if "tool" in step:
            call = {"id": "call_" + uuid.uuid4().hex[:12], "type": "function",
                    "function": {"name": step["tool"], "arguments": json.dumps(step["args"])}}
            msg, finish, ntok = {"role": "assistant", "content": None, "tool_calls": [call]}, "tool_calls", 40
        else:
            msg, finish, ntok = {"role": "assistant", "content": step["text"]}, "stop", max(1, len(step["text"]) // 4)
        u = usage(body, ntok)
        if not body.get("stream"):
            return self.send_json({"id": cid, "object": "chat.completion", "created": now, "model": A.model,
                                   "choices": [{"index": 0, "message": msg, "finish_reason": finish}], "usage": u})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def ev(delta, fin=None, use=None):
            ch = {"id": cid, "object": "chat.completion.chunk", "created": now, "model": A.model,
                  "choices": [{"index": 0, "delta": delta, "finish_reason": fin}]}
            if use is not None:
                ch["choices"], ch["usage"] = [], use
            self.wfile.write(f"data: {json.dumps(ch)}\n\n".encode())
            self.wfile.flush()

        ev({"role": "assistant", "content": ""})
        if "tool" in step:
            c = msg["tool_calls"][0]
            ev({"tool_calls": [{"index": 0, "id": c["id"], "type": "function",
                                "function": {"name": c["function"]["name"], "arguments": ""}}]})
            ev({"tool_calls": [{"index": 0, "function": {"arguments": c["function"]["arguments"]}}]})
        else:
            ev({"content": msg["content"]})
        ev({}, finish)
        if (body.get("stream_options") or {}).get("include_usage", True):
            ev(None, use=u)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True


ThreadingHTTPServer(("127.0.0.1", A.port), H).serve_forever()
