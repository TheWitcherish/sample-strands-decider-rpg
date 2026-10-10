"""Tests for the Once Upon Agentic AI branching engine."""

from __future__ import annotations

import os

import httpx
import pytest

from strands_decider_rpg.decider import HttpDecider, ScriptedDecider
from strands_decider_rpg.engine import play_chapter
from strands_decider_rpg.story import CHAPTER_ONE

_KEY = CHAPTER_ONE.question.key


@pytest.mark.parametrize(
    ("score", "branch", "ending_key", "acted"),
    [
        (0.90, "BOLD", "blaze_of_glory", True),
        (0.05, "CAUTIOUS", "the_long_game", True),
        (0.50, "HESITATE", "the_table_decides", False),
    ],
)
def test_three_paths(score: float, branch: str, ending_key: str, acted: bool) -> None:
    decider = ScriptedDecider(scores={_KEY: score})
    result = play_chapter(CHAPTER_ONE, decider)
    assert result.branch == branch
    assert result.ending_key == ending_key
    assert result.acted_confidently is acted


def test_threshold_boundary_acts_at_the_bar() -> None:
    # confidence == bar (0.75) must act, not hesitate: value 0.75 -> confidence 0.75.
    result = play_chapter(CHAPTER_ONE, ScriptedDecider(scores={_KEY: 0.75}), bar=0.75)
    assert result.acted_confidently is True
    assert result.branch == "BOLD"


def test_just_below_bar_hesitates() -> None:
    result = play_chapter(CHAPTER_ONE, ScriptedDecider(scores={_KEY: 0.74}), bar=0.75)
    assert result.acted_confidently is False
    assert result.branch == "HESITATE"


@pytest.mark.skipif(
    os.environ.get("DECIDER_LIVE") != "1",
    reason="set DECIDER_LIVE=1 with a `strands-decider serve` instance running",
)
def test_live_decider_reachable() -> None:
    decider = HttpDecider()
    try:
        result = play_chapter(CHAPTER_ONE, decider)
    except httpx.HTTPError as exc:  # pragma: no cover - only runs against a live server
        pytest.fail(f"live decider unreachable at {decider.base_url}: {exc}")
    assert 0.0 <= result.noul <= 1.0
    assert result.branch in {"BOLD", "CAUTIOUS", "HESITATE"}
