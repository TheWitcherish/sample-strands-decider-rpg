"""Integration tests against a REAL decider: every chapter, on the live model.

Run with a ``strands-decider serve`` instance on DECIDER_URL and ``DECIDER_LIVE=1``. The model
picks the branch, so these assert the contract and the clear-cut calls, not every branch.
"""

from __future__ import annotations

import os

import pytest

from strands_decider_rpg.chapters import CHAPTERS
from strands_decider_rpg.decider import HttpDecider
from strands_decider_rpg.engine import CONFIDENCE_BAR, finish_campaign

pytestmark = pytest.mark.skipif(
    os.environ.get("DECIDER_LIVE") != "1",
    reason="set DECIDER_LIVE=1 with a `strands-decider serve` instance running",
)

_LIVE = (HttpDecider(),)


@pytest.mark.parametrize("chapter", sorted(CHAPTERS))
def test_live_chapter_plays(chapter: int) -> None:
    spec = CHAPTERS[chapter]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.latency_ms > 0
    assert 0.0 <= result.confidence <= 1.0
    assert result.model != "scripted"


def test_live_chapter_one_calls_for_a_check_when_the_adventurer_looks() -> None:
    spec = CHAPTERS[1]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.answers["needs_check"].summary.startswith("yes")


def test_live_chapter_one_skips_the_check_when_the_adventurer_walks_on() -> None:
    spec = CHAPTERS[1]
    say = "I ignore the noise and keep walking."
    result = spec.play(_LIVE, say, CONFIDENCE_BAR, 7)
    assert result.answers["needs_check"].summary.startswith("no")


def test_live_chapter_two_picks_the_rulebook_for_a_rules_lookup() -> None:
    spec = CHAPTERS[2]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.answers["tool"].summary == "http_request"


def test_live_chapter_four_refuses_a_portal_with_no_destination() -> None:
    spec = CHAPTERS[4]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.answers["names_place"].summary.startswith("no")
    assert result.branch == "PORTAL_REFUSES"


def test_live_chapter_five_sends_a_rules_question_to_the_rules_agent() -> None:
    spec = CHAPTERS[5]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.answers["specialist"].summary == "rules_agent"
    assert result.round_trips == 1


def test_live_campaign_finishes() -> None:
    results = [
        spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7) for spec in CHAPTERS.values()
    ]
    campaign = finish_campaign(results)
    assert campaign.round_trips == 5
    assert campaign.questions_asked == 7
