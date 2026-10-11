# SETUP: run Patrol on your own Mac

Written so a coding agent (Claude Code, Codex, or similar) can follow it top to bottom, and a person can too.
Agent: do the steps in order, run every check, and stop and tell the user when a check fails. Never skip a check.
**Ask the user before each download marked ASK**, and before installing anything system-wide.

Patrol is a simulated search drone. It sweeps an area in MuJoCo, and a local decision model (Clef-Flash) judges
camera crops against clue descriptions ("blue backpack"). Optionally a local chat model writes clues and alert notes,
and a local voice stack lets the operator speak. Everything runs on the Mac, with no cloud.

## 0. What you need

| Need | Why | Check (agent: run it) |
|---|---|---|
| Apple Silicon Mac (M1 or later) | Clef-Flash with images runs only through MLX | `uname -m` prints `arm64` |
| 32 GB memory or more (64 GB is comfortable with a chat model) | Clef-Flash 8-bit peaks around 11-13 GB, plus the chat model | `sysctl -n hw.memsize` (bytes) |
| About 15 GB free disk (Tier 1), more for a chat model and voice | weights | `df -h ~` |
| `uv`, `git`, the Hugging Face `hf` CLI | installs and downloads | `uv --version; git --version; hf --version` |

Missing tools: `brew install uv git` and `uv tool install "huggingface_hub[cli]"`, after asking the user.

No Apple Silicon Mac, or not enough memory? See [`HOSTED.md`](HOSTED.md) for hosted models instead (untested).

Pick a tier with the user. Each tier adds to the one before it.

| Tier | What works | Extra downloads |
|---|---|---|
| **1. Search** | sweeps, Clef judging, investigate and confirm, alerts, the live console, e2e scenarios 1-4 with `--no-think` | Clef-Flash (10.7 GB), plus the 3D items (step 3) |
| **2. + chat model** | clue wording from a description, alert notes, operator questions, scenario 5 with `--think` | a vision chat model, size depends on the model |
| **3. + voice** | speak the description and commands, alerts read aloud, scenario 6 | Parakeet speech-to-text and Kokoro speech |

## 1. Get the code

The repos must sit at these exact paths: the voice code is looked up at `~/repos/local-voice`.

```sh
mkdir -p ~/repos && cd ~/repos
git clone https://github.com/mthomas100/patrol ~/repos/patrol
git clone https://github.com/mthomas100/local-decision ~/repos/local-decision   # Clef server (Tier 1)
```

`local-decision`, `local-voice` and `local-3d` are public repos on the same account as Patrol.

Patrol's own environment (Python 3.12; these are the versions it was tested with):

```sh
cd ~/repos/patrol
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python mujoco==3.15.0 numpy==2.5.4 pillow==12.3.0 scipy==1.18.1 trimesh==5.1.1 pytest==9.1.1
```

**Check:** `.venv/bin/python -m pytest -q tests/` passes (about 70 tests, no models needed).

**No `hold` command needed.** The author's Mac has a GPU hold gate; Patrol's test preflight now reports
"no hold command on this Mac" when it is missing and carries on.

**Model addresses.** Patrol looks for Clef on `http://127.0.0.1:8097` and the chat model (named `qwen38`) on
`http://127.0.0.1:8090`. To use other addresses, set `PATROL_CLEF_BASE` and `PATROL_LLM_BASE` (base URLs, no path),
for example `PATROL_CLEF_BASE=http://127.0.0.1:9097 tests/e2e_search.sh --only 1 --no-think`.

## 2. Clef-Flash, the decision model (Tier 1)

Patrol calls it at `http://127.0.0.1:8097/v1/systemone`; that address is fixed in the code.

```sh
cd ~/repos/local-decision
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.lock
bin/decide fetch clef-flash-mlx      # ASK: 10.7 GB into ~/models/clef-flash-mlx-8bit (mlx-community/clef-flash-8bit, Apache-2.0)
bin/decide serve clef-flash-mlx      # loads it and leaves it running on 127.0.0.1:8097
```

Fetch only `clef-flash-mlx`. `decide fetch all` downloads every Clef variant (far more disk). If `decide serve` says
the GPU is busy and nothing heavy is running, add `--force`.

**Check:** `curl -s 127.0.0.1:8097/health` contains `"ok"`. Stop it later with `bin/decide stop`.

## 3. The 3D items (Tier 1, required)

Git holds only each item's description files; the meshes (about 50 MB for all eight) are not in the repo. Without them
nothing can be placed in the scene. There are two ways to get them:

**A. A mesh bundle, if the author published one** (a zip of `assets/items/*/mujoco/`). Unzip it over
`assets/items/`, then rewrite the author's absolute paths to yours (the `mujoco.json` files name their
mesh by full path):

```sh
cd ~/repos/patrol
for f in assets/items/*/mujoco/mujoco.json; do
  d="$PWD/$(dirname "$f")"
  .venv/bin/python -c "import json,sys; p=sys.argv[1]; j=json.load(open(p)); j['obj']=sys.argv[2]+'/mesh.obj'; j['texture']=sys.argv[2]+'/texture.png'; json.dump(j,open(p,'w'),indent=1)" "$f" "$d"
done
```

**B. Rebuild them with m3d** (the author's public `local-3d` repo: text, then a concept image, then a 3D mesh with
Hunyuan3D). This is heavy. Follow "Setup, if rebuilding from scratch" in `~/repos/local-3d/README.md`, but fetch only
the z-image-turbo and Hunyuan3D weights it names (ASK: the full set is about 45 GB). Check: `m3d --help` works. Then:

```sh
cd ~/repos/patrol
rm assets/items/*/mujoco/mujoco.json      # the tracked copies make the build script skip every item
tools/build_items.sh                      # six items, about 3 GPU-minutes each
# the build script does not list these two; build them by hand (output paths must be absolute):
m3d make 'a royal blue hiking backpack with black straps, lying on its back' --post game --yield-llm --seed 7 -o $PWD/assets/items/blue_backpack --json
.venv/bin/python -m patrol.items convert assets/items/blue_backpack --size 0.55
m3d make 'a crumpled blue plastic tarp sheet lying flat on the ground' --post game --yield-llm --seed 7 -o $PWD/assets/items/blue_tarp --json
.venv/bin/python -m patrol.items convert assets/items/blue_tarp --size 2.0
```

Rebuilt meshes will not be identical to the author's, so detection numbers can differ somewhat.

**Check (either way):** every one of `blue_backpack blue_tarp green_sleeping_bag grey_dog orange_leaf_pile
orange_tent red_jacket yellow_helmet` has `assets/items/<name>/mujoco/mesh.obj` and `texture.png`, and the `obj` path
inside its `mujoco.json` exists on this Mac.

## 4. Prove Tier 1

```sh
cd ~/repos/patrol
tests/e2e_search.sh --only 1,2,3,4 --no-think --out runs/setup-tier1
```

**Pass:** exit code 0 and `runs/setup-tier1/REPORT.md` says PASS. Exit code 2 means the preflight failed (usually Clef
not answering: redo step 2's check). Each scenario is a full simulated flight, so this takes a while.

Then the live console:

```sh
bin/patrol console --search --terrain grass --seed 6 \
  --items blue_backpack,orange_tent,blue_tarp --clues blue_backpack,orange_tent --pace 1 --port 8785
```

Open `http://127.0.0.1:8785/` and start the search. The drone sweeps in lanes and outlines odd spots. It should fly
down to look at the tarp and dismiss it, and raise an alert (photo and coordinates) for the backpack and for the tent.

## 5. Tier 2: a vision chat model

Patrol calls an OpenAI-compatible chat server at `http://127.0.0.1:8090/v1/chat/completions` with the model name
`qwen38` and image inputs; both are fixed in the code. Ask the user which local server they already use, and serve a
**vision** model on port 8090 under the name `qwen38`:

- llama.cpp: `llama-server -m <model>.gguf --mmproj <mmproj>.gguf --alias qwen38 --port 8090`
- LM Studio: load the model, set its API identifier to `qwen38`, and set the server port to 8090
- Ollama: `ollama cp <model> qwen38`, and run the server with `OLLAMA_HOST=127.0.0.1:8090`

The author used Qwen3.8 Flash Next (Unsloth's GGUF, `unsloth/Qwen3.8-Flash-Next-GGUF`, Q4 with its `mmproj` vision
file). ASK before downloading; check the model's licence and size on its card. Any vision chat model works; a weaker one
writes worse clue wording and notes. Patrol sends `"thinking": {"type": "disabled"}`, which most servers ignore.

**Check:**

```sh
curl -s 127.0.0.1:8090/v1/chat/completions -H 'content-type: application/json' \
  -d '{"model":"qwen38","max_tokens":8,"messages":[{"role":"user","content":"Say ok"}]}'
```

It returns a `choices` array. Then `tests/e2e_search.sh --only 5 --out runs/setup-tier2` (with `--think`, the default)
should PASS, and the console accepts `--think --describe "Missing hiker. Blue backpack, orange tent."`.

## 6. Tier 3: voice

```sh
git clone https://github.com/mthomas100/local-voice ~/repos/local-voice
cd ~/repos/local-voice/orchestrator && uv sync          # creates orchestrator/.venv, which Patrol calls
```

Follow `~/repos/local-voice/README.md` for its speech models (Parakeet speech-to-text, CC-BY-4.0; Kokoro speech,
Apache-2.0; ASK before the downloads it names). **Check:** `tests/e2e_search.sh --only 6 --out runs/setup-tier3`
passes. It plays recorded voice clips, so no microphone is needed.

## 7. If something fails

| Symptom | Cause and fix |
|---|---|
| `Clef-Flash is not answering on :8097` | Clef server not running (or `PATROL_CLEF_BASE` points elsewhere): step 2. It answers one request at a time, so `/health` can be slow while it is busy. |
| MuJoCo error about a missing `.obj` or `.png` | Item meshes missing, or `mujoco.json` still names the author's paths: step 3. |
| Notes never appear, or chat calls return 404 | Nothing on 8090, or the model is not named `qwen38`: step 5. |
| Voice silent, or `local-voice` errors | `~/repos/local-voice/orchestrator/.venv` missing: step 6. |
| Results drift between runs | Normal within limits. The author measured 17 of 18 scenario flights passing over three seed sets. |

Do not edit `patrol/*.py` while an e2e is running: each scenario starts a fresh process and picks up the edit.
Do not change thresholds in `patrol/search.py`; they were tuned on Clef-Flash 8-bit and are explained in
`DECISIONS.md`.

## Licences

Clef-Flash: Apache-2.0 (Cloudflare). MuJoCo: Apache-2.0. Kokoro: Apache-2.0. Parakeet: CC-BY-4.0. The chat model is
your choice: check its licence. Items made with m3d use Hunyuan3D, which has its own licence terms; read them before
sharing meshes.
