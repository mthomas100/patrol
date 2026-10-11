# Running Patrol with hosted (non-local) models

**Status: ideas and rough wiring, NOT TESTED.** Patrol was built and measured with every model on one Mac with no
internet. This page is for anyone without that hardware who wants to try it anyway. The local setup is in
[`SETUP.md`](SETUP.md); do its steps 1 and 3 (code, Python environment, 3D items) first either way.

Two things change when the models are hosted:

- **It is no longer offline.** Patrol's point is a search drone that works with no cell service. A hosted version is
  for trying the behaviour, not for the field.
- **Network latency changes the flights.** The drone keeps flying while the model thinks, and answers that arrive too
  late are dropped. Locally a decision takes about 0.3-0.5 s; a hosted call adds network time. Fly with
  **`--lockstep`** (the simulated world pauses while the model thinks) so slow answers do not change what happens.

## The idea: keep Patrol's addresses, put a small proxy behind each

Patrol calls fixed local addresses. Rather than editing code, run a small local proxy on each address that forwards
to the hosted service and adds the API key:

| Patrol calls | Speaks | Hosted equivalent | Proxy |
|---|---|---|---|
| `127.0.0.1:8097/v1/systemone` | the Jev/SystemOne decision API | Cloudflare Workers AI `clef-flash` (the same model) | a ~30-line script (below) |
| `127.0.0.1:8090/v1/chat/completions`, model `qwen38` | OpenAI chat with images | any vision chat model: OpenRouter, Together, Fireworks, Alibaba's own Qwen API | LiteLLM proxy |
| local Parakeet and Kokoro, loaded in-process | Python, not HTTP | a hosted speech-to-text and text-to-speech service | needs a code change; skip voice at first |

## 1. The decision model: Clef-Flash on Cloudflare Workers AI

This is the one that matters: every frame goes through it, and every threshold in Patrol was tuned on Clef-Flash's
probabilities. Cloudflare, which made Clef, hosts it on Workers AI, so the model is the same and the tuning should
mostly carry over. The local copy is 8-bit; the hosted one is presumably full precision. Expect small differences,
not a different system.

From Cloudflare's model page (developers.cloudflare.com/workers-ai/models/clef, read 2026-10-11):

- REST: `POST https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef-flash`, header
  `Authorization: Bearer <API_TOKEN>`.
- Body: `model` (`"clef-flash"`), `state`, `questions` (`noul`, `choice`, `score`), and optional `images` (up to 4,
  PNG, JPEG or WebP). That is the shape Patrol already sends; Patrol sends images as `data:image/jpeg;base64,...`
  strings and the page does not say which encoding it expects, so test that first.
- Price: the page lists $0.24 per million input tokens for Clef, no charge for output, and an image costs one token per
  32x32 block (at most 1,024). A scenario flight makes 50-450 decision calls (measured), so a flight should cost
  cents. Check Clef-Flash's own price on the page.

What the proxy on `:8097` must do (sketch, not tested):

```python
# clef_proxy.py: listen on 127.0.0.1:8097, forward /v1/systemone to Workers AI, answer /health.
import json, os, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

URL = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/ai/run/@cf/cloudflare/clef-flash"

class H(BaseHTTPRequestHandler):
    def do_GET(self):                                    # Patrol's health check looks for "ok"
        self._send(200, {"status": "ok"})
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        req["model"] = "clef-flash"                      # Patrol sends its local name, "clef-flash-mlx"
        r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(req).encode(), {
            "Content-Type": "application/json", "Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"}), timeout=30)
        body = json.loads(r.read())
        self._send(200, body.get("result", body))       # Cloudflare's REST API usually wraps the answer in "result"
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

ThreadingHTTPServer(("127.0.0.1", 8097), H).serve_forever()
```

Check it the way SETUP.md does: `curl -s 127.0.0.1:8097/health`, then `tests/e2e_search.sh --only 1 --no-think`.
Patrol expects an answer with `answers.action.choice` and `answers.action.probabilities`, plus one `noul` per clue.
If the hosted answer looks different, translate it in the proxy, not in Patrol.

**Alternatives.** Typesafe AI's Jev, which defined this API, is also hosted and speaks it, but it is a different
model and Patrol's thresholds were not tuned on it. Without any decision-API model you would have to imitate one with
an ordinary vision chat model (ask for the action and a probability per clue as JSON, or read token probabilities).
That is real work: rewrite `patrol/clef.py` and re-tune every threshold in `patrol/search.py` on the tuning items.

## 2. The chat model: any vision model through LiteLLM

The chat model writes clue descriptions from the operator's words, alert notes, and answers to operator questions. It
never flies the drone, so any decent vision chat model works; a weaker one writes worse clue wording. The author used
Qwen3.8 Flash Next. Hosted Qwen vision models, Gemini Flash, GPT mini models and Claude Haiku are all reasonable. Find
one on openrouter.ai/models, filtered by image input.

LiteLLM's proxy serves an OpenAI-style endpoint under any model name you choose:

```yaml
# litellm.yaml
model_list:
  - model_name: qwen38                         # the name Patrol asks for
    litellm_params:
      model: openrouter/<provider>/<vision-model>
      api_key: os.environ/OPENROUTER_API_KEY
litellm_settings:
  drop_params: true                            # Patrol sends a "thinking" field some providers reject
```

```sh
uv tool install 'litellm[proxy]'
litellm --config litellm.yaml --port 8090
```

Check it with the `curl` in SETUP.md step 5, then fly with `--think`.

## 3. Voice: skip it first

Speech runs in-process: `patrol/voice_worker.py` loads Parakeet and Kokoro from `local-voice`. There is no address to
put a proxy on. Without voice you lose speech only, not the search: the operator types the description (`--describe
"Missing hiker. Blue backpack."`). To add hosted voice, change `voice_worker.py` to call a hosted speech-to-text
service (OpenAI's transcription models, Deepgram, Groq's Whisper) and a text-to-speech service (OpenAI, ElevenLabs,
Cartesia; Kokoro itself is offered by some hosts such as DeepInfra and Replicate). Voice commands are routed by Clef
with a text-only question, so they work through the proxy in section 1.

## 4. Hardware without local models

With the models hosted, the Mac only runs the simulator, the camera and the console. MuJoCo and numpy run on any
recent Mac, Intel included. Linux should work but was never tried. There, a server with no display needs
`MUJOCO_GL=egl` (or `osmesa`) for offscreen rendering. The test preflight also calls the macOS commands `hold` and
`memory_pressure`, so give both stand-ins as SETUP.md step 1 shows for `hold`.

## Summary for an agent doing this

1. SETUP.md steps 0 (skip the memory and Apple Silicon rows), 1 and 3.
2. Ask the user for a Cloudflare account ID and API token, write `clef_proxy.py` from section 1 outside the repo,
   run it, check `/health`, and send one real request with an image. Fix the proxy until the answer has the shape
   Patrol expects.
3. `tests/e2e_search.sh --only 1,2,3,4 --no-think --out runs/hosted-tier1`. Passing means the hosted decision model
   works. If it fails, compare against the thresholds in `patrol/search.py` before changing anything, and tell the user.
4. Optional: ask which chat provider and model to use, run LiteLLM per section 2, then `--only 5`.
5. Report what passed, what failed, and the latency per decision (it is in `REPORT.md`).
