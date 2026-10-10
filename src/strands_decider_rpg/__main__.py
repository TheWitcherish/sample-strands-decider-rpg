"""CLI: play one chapter or the whole campaign, scripted offline or against the live decider.

Scripted (no model, no GPU, no network):
    uv run once-upon-decider chapter 1 --script bold
    uv run once-upon-decider campaign --script unsure

Live (a ``strands-decider serve`` instance on DECIDER_URL):
    uv run once-upon-decider campaign --decider http
    uv run once-upon-decider chapter 5 --decider http --council http://localhost:8000,http://localhost:8001
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import httpx

from strands_decider_rpg.chapters import CHAPTERS, Preset
from strands_decider_rpg.decider import DECIDER_URL, Decider, HttpDecider
from strands_decider_rpg.engine import (
    CONFIDENCE_BAR,
    CampaignResult,
    ChapterResult,
    finish_campaign,
)


def _render_chapter(result: ChapterResult, bar: float) -> str:
    verdict = "ACTED" if result.acted else "HELD BACK"
    lines = [
        f"=== Chapter {result.chapter}: {result.title} ===",
        result.opening,
        f'  adventurer : "{result.say}"',
    ]
    lines += [f"  decider    : {key} -> {a.summary}" for key, a in result.answers.items()]
    if result.detail:
        lines.append(f"  evidence   : {result.detail}")
    lines += [
        f"  confidence : {result.confidence:.3f} (bar {bar:.2f}) -> {verdict}",
        f"  speed      : {result.round_trips} round trip(s), {result.latency_ms:.0f} ms"
        f" on {result.model}",
        f"  {result.narration}",
        f">>> {result.ending_title}: {result.ending_prose}",
        "",
    ]
    return "\n".join(lines)


def _render_campaign(campaign: CampaignResult) -> str:
    fates = " -> ".join(c.fate.value for c in campaign.chapters)
    return "\n".join(
        [
            "=== The Campaign ===",
            f"  fates      : {fates}",
            f"  decider    : {campaign.questions_asked} questions, {campaign.round_trips} round"
            f" trips, {campaign.decider_ms:.0f} ms of model time in total",
            f">>> FINAL ENDING ({campaign.fate.value}): {campaign.ending_title}",
            f"    {campaign.ending_prose}",
        ]
    )


def _unit_interval(raw: str) -> float:
    value = float(raw)
    if not 0.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return value


def _deciders(args: argparse.Namespace, chapter: int) -> tuple[Decider, ...]:
    if args.decider == "scripted":
        return CHAPTERS[chapter].scripted(Preset(args.script))
    urls: Sequence[str] = args.council.split(",") if args.council else (DECIDER_URL,)
    return tuple(HttpDecider(base_url=url.strip()) for url in urls)


def _play(args: argparse.Namespace, chapter: int, say: str | None) -> ChapterResult:
    spec = CHAPTERS[chapter]
    return spec.play(_deciders(args, chapter), say or spec.info.default_say, args.bar, args.seed)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Once Upon Agentic AI, decided by confidence.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--decider", choices=("scripted", "http"), default="scripted")
    common.add_argument("--script", choices=[p.value for p in Preset], default="bold")
    common.add_argument("--bar", type=_unit_interval, default=CONFIDENCE_BAR)
    common.add_argument("--seed", type=int, default=7, help="seed for chapter 3's d20")
    common.add_argument("--council", default="", help="comma-separated decider URLs (chapter 5)")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("chapter", parents=[common], help="play one chapter")
    one.add_argument("number", type=int, choices=sorted(CHAPTERS))
    one.add_argument("--say", help="what the adventurer says (remix the scene)")
    sub.add_parser("campaign", parents=[common], help="play all five chapters")
    args = parser.parse_args(argv)

    try:
        if args.command == "chapter":
            print(_render_chapter(_play(args, args.number, args.say), args.bar))
            return 0
        results = []
        for number in sorted(CHAPTERS):
            result = _play(args, number, None)
            print(_render_chapter(result, args.bar))
            results.append(result)
        print(_render_campaign(finish_campaign(results)))
        return 0
    except httpx.HTTPError as exc:
        print(f"decider unreachable: {exc}. Is `strands-decider serve` running?", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
