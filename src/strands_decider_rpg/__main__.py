"""CLI for experiment 1, Chapter 1. The 30-second kickoff.

Scripted (default, no model needed):
    uv run once-upon-decider --score 0.9    # confident bold
    uv run once-upon-decider --score 0.05   # confident cautious
    uv run once-upon-decider --score 0.5    # unsure -> the table decides

Live (needs the model served locally; see the HttpDecider docstring):
    uv run once-upon-decider --decider http
"""

from __future__ import annotations

import argparse
import sys

from strands_decider_rpg.decider import Decider, HttpDecider, ScriptedDecider
from strands_decider_rpg.engine import CONFIDENCE_BAR, PlayResult, play_chapter
from strands_decider_rpg.story import CHAPTER_ONE


def _render(result: PlayResult, *, bar: float) -> str:
    verdict = "ACTED" if result.acted_confidently else "HELD BACK"
    return "\n".join(
        [
            f"=== Chapter {result.chapter}: {result.chapter_title} ===",
            "",
            CHAPTER_ONE.opening,
            "",
            f"  state   : {CHAPTER_ONE.state}",
            f"  question: {CHAPTER_ONE.question.instructions}",
            "",
            f"  decider : noul={result.noul:.3f}  confidence={result.confidence:.3f}"
            f"  (bar={bar:.2f})  ->  {verdict}",
            f"  branch  : {result.branch}",
            "",
            f"  {result.narration}",
            "",
            f">>> ENDING: {result.ending_title}",
            f"    {result.ending_prose}",
        ]
    )


def _unit_interval(raw: str) -> float:
    value = float(raw)
    if not 0.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError("score must be between 0 and 1")
    return value


def main() -> int:
    """Run Chapter 1 and print the branch and ending. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        description="Once Upon Agentic AI, Chapter 1, decided by confidence."
    )
    parser.add_argument("--decider", choices=("scripted", "http"), default="scripted")
    parser.add_argument(
        "--score",
        type=_unit_interval,
        default=0.9,
        help="scripted noul score in [0,1] (ignored for --decider http)",
    )
    parser.add_argument("--bar", type=_unit_interval, default=CONFIDENCE_BAR)
    args = parser.parse_args()

    if args.decider == "http":
        decider: Decider = HttpDecider()
    else:
        decider = ScriptedDecider(scores={CHAPTER_ONE.question.key: args.score})

    result = play_chapter(CHAPTER_ONE, decider, bar=args.bar)
    print(_render(result, bar=args.bar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
