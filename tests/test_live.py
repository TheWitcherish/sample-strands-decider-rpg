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


def test_live_chapter_one_reads_a_clear_kick_as_bold() -> None:
    spec = CHAPTERS[1]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.answers["is_bold"].summary.startswith("yes")


def test_live_chapter_one_reads_a_clear_tiptoe_as_cautious() -> None:
    spec = CHAPTERS[1]
    say = "I crouch by the window and quietly watch the room for a long while before entering."
    result = spec.play(_LIVE, say, CONFIDENCE_BAR, 7)
    assert result.answers["is_bold"].summary.startswith("no")


def test_live_chapter_two_picks_the_rulebook_for_a_rules_lookup() -> None:
    spec = CHAPTERS[2]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.answers["tool"].summary == "http_request"


def test_live_chapter_four_refuses_a_portal_with_no_destination() -> None:
    spec = CHAPTERS[4]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert result.answers["names_place"].summary.startswith("no")
    assert result.branch == "PORTAL_REFUSES"


def test_live_chapter_five_allies_agree_on_an_obvious_parley() -> None:
    spec = CHAPTERS[5]
    result = spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7)
    assert {a.summary for a in result.answers.values()} == {"parley"}


def test_live_campaign_finishes() -> None:
    results = [
        spec.play(_LIVE, spec.info.default_say, CONFIDENCE_BAR, 7) for spec in CHAPTERS.values()
    ]
    campaign = finish_campaign(results)
    assert campaign.round_trips == 6
    assert campaign.questions_asked == 8
