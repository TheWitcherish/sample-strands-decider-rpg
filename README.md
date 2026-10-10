# sample-strands-decider-rpg

A **sample** repository for experiments, not production code. It replays the five chapters of
[Once Upon Agentic AI](https://github.com/aws-samples/sample-once-upon-agentic-ai) — a Game Master
for a Table-Top Role-Playing Game (TTRPG) built with Strands Agents — and hands one decision per
chapter to [Strands Decider 2B](https://strandsagents.com/blog/introducing-strands-decider/), a
small, fast, open-source decision model. The ending you reach depends on how *sure* the model is,
not only on what it picked.

- **Confident yes** → the bold branch.
- **Confident no** → the cautious branch.
- **Not sure** (confidence below the bar) → the Game Master hesitates and the table decides.

## Play it on your machine

```bash
git clone https://github.com/TheWitcherish/sample-strands-decider-rpg
cd sample-strands-decider-rpg
uv sync

# Scripted: no model, no GPU, no network.
uv run once-upon-decider --score 0.9     # confident yes -> A Blaze of Glory
uv run once-upon-decider --score 0.05    # confident no  -> The Long Game
uv run once-upon-decider --score 0.5     # unsure        -> The Table Decides
```

`--score` is the scripted `noul` value in `[0, 1]`, where closer to 1 leans yes. The engine turns
it into a confidence (`max(score, 1 - score)`) and compares that with `--bar` (default `0.75`).

## Run it against the real model

The model is an opt-in extra because it pulls `torch` and `transformers`:

```bash
uv sync --extra decider
export DECIDER_MODEL=StrandsAgents/strands-decider-2B-qwen3.5-v1-2610
uv run strands-decider serve "$DECIDER_MODEL" --port 8000   # terminal 1
uv run once-upon-decider --decider http                     # terminal 2
```

`DECIDER_URL` (default `http://localhost:8000`) and `DECIDER_MODEL` are read from the environment.
Model ids are perishable, so check the
[Strands Decider README](https://github.com/strands-labs/strands-decider) for the current one.

## Certification check

```bash
uv run pytest -q
```

It covers the three branches, the exact confidence bar, and the raw `/v1/systemone` response shape.
