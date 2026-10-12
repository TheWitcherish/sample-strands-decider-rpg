# sample-strands-decider-rpg

A **sample** repository for experiments, not production code. It replays the five chapters of
[Once Upon Agentic AI](https://github.com/aws-samples/sample-once-upon-agentic-ai) — an AI Game Master
for a Table-Top Role-Playing Game (TTRPG) built with Strands Agents — and hands the decisions to
[Strands Decider](https://github.com/strands-labs/strands-decider), a small, fast, open-source
decision model. Every answer carries a calibrated confidence, and the story routes on *how sure*
the model is, not only on what it picked. Five chapters add up to one of three final endings.

| Chapter | Workshop topic | Decider capability |
| --- | --- | --- |
| 1. The Art of Agent Summoning | your first agent | `noul` (yes/no) with criteria: does this need a perception check? Sure: roll a d6. Unsure: ask the player |
| 2. The Adventurer's Arsenal | vended tools | `choice`: pick the tool in one forward pass |
| 3. The Art of Magical Forging | the dice `@tool` | `score`: a rubric sets the number to beat on a d6; an unsure AI Game Master rolls twice and keeps the lower |
| 4. Planar Portals | MCP | three guard questions in **one** round trip |
| 5. The Grand Alliance | A2A | `choice`: the orchestrator picks which specialist agent (Rules or Character) to call before answering; unsure means ask the player first |

## Getting Started

The game talks to Strands Decider running on your own machine. The model is an opt-in extra
because it pulls `torch` and `transformers` (about 4 GB of weights download on the first serve).
It runs on an Apple-silicon Mac (MPS), a CUDA GPU, or CPU.

```bash
git clone https://github.com/TheWitcherish/sample-strands-decider-rpg
cd sample-strands-decider-rpg
uv sync

# terminal 1: the model server (leave it running)
export DECIDER_MODEL=StrandsAgents/strands-decider-2B-qwen3.5-v1-2610
uv run --extra decider strands-decider serve "$DECIDER_MODEL" --port 8000

# terminal 2: the game
uv run once-upon-strands-decider chapter 1
uv run once-upon-strands-decider campaign

# Now you try: remix a scene and watch the confidence move.
uv run once-upon-strands-decider chapter 1 \
  --say "The bramblehoot is right in front of me. I slowly offer it a sip of my coffee."
```

After the first download the model is cached on your machine. To serve it with no network at all,
start it with `HF_HUB_OFFLINE=1 UV_OFFLINE=1` in front of the serve command.

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
