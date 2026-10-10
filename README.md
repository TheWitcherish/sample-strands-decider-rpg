# sample-strands-decider-rpg

A **sample** repository for experiments, not production code. It replays the five chapters of
[Once Upon Agentic AI](https://github.com/aws-samples/sample-once-upon-agentic-ai) — a Game Master
for a Table-Top Role-Playing Game (TTRPG) built with Strands Agents — and hands the decisions to
[Strands Decider](https://github.com/strands-labs/strands-decider), a small, fast, open-source
decision model. Every answer carries a calibrated confidence, and the story routes on *how sure*
the model is, not only on what it picked. Five chapters add up to one of three final endings.

| Chapter | Workshop topic | Decider capability |
| --- | --- | --- |
| 1. The Art of Agent Summoning | your first agent | `noul` (yes/no) with criteria: bold, cautious, or the table decides |
| 2. The Adventurer's Arsenal | vended tools | `choice`: pick the tool in one forward pass |
| 3. The Art of Magical Forging | the dice `@tool` | `score`: a rubric sets the DC; an unsure GM rolls with disadvantage |
| 4. Planar Portals | MCP | three guard questions in **one** round trip |
| 5. The Grand Alliance | A2A | a council: each ally can be a different decider model |

## Play it on your machine

```bash
git clone https://github.com/TheWitcherish/sample-strands-decider-rpg
cd sample-strands-decider-rpg
uv sync

# Scripted: no model, no GPU, no network.
uv run once-upon-decider campaign --script bold       # -> The Legend of the Loud
uv run once-upon-decider campaign --script cautious   # -> The Quiet Crown
uv run once-upon-decider campaign --script unsure     # -> The Table Remembers
uv run once-upon-decider chapter 3 --script unsure    # disadvantage roll
```

## Run it against the real model

The model is an opt-in extra because it pulls `torch` and `transformers` (about 4 GB of weights
download on the first serve). It runs on an Apple-silicon Mac (MPS), a CUDA GPU, or CPU.

```bash
uv sync --extra decider
export DECIDER_MODEL=StrandsAgents/strands-decider-2B-qwen3.5-v1-2610
uv run --extra decider strands-decider serve "$DECIDER_MODEL" --port 8000   # terminal 1
uv run --extra decider once-upon-decider campaign --decider http             # terminal 2

# Now you try: remix a scene and watch the confidence move.
uv run --extra decider once-upon-decider chapter 1 --decider http \
  --say "I tiptoe to the window, peek inside and count the guards before I even touch the door."
```

### A council of two models (chapter 5)

Serve a second checkpoint on another port and let each ally run on its own model:

```bash
uv run --extra decider strands-decider serve StrandsAgents/strands-decider-2B-hobson-v21 --port 8001
uv run --extra decider once-upon-decider chapter 5 --decider http \
  --council http://localhost:8000,http://localhost:8001
```

`DECIDER_URL` (default `http://localhost:8000`) and `DECIDER_MODEL` are read from the environment.
`--bar` sets the confidence needed to act (default `0.8`; the decider README's own rule for acting
automatically is `0.9`). Model ids are perishable: check the
[Strands Decider README](https://github.com/strands-labs/strands-decider) for the current ones.
The Gemma 4 variants (E2B, E4B, 12B, 26B-A4B) need `strands-decider` from `main`, not the `0.1.0`
release pinned here.

## Certification check

```bash
uv run pytest -q                                  # scripted: every chapter, every ending
DECIDER_LIVE=1 uv run --extra decider pytest -q   # plus every chapter on the live model
```
