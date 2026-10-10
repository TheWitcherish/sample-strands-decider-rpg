"""Tests for all five chapters and the campaign: every chapter, every preset, scripted."""

from __future__ import annotations

import pytest

from strands_decider_rpg.__main__ import main
from strands_decider_rpg.chapters import CHAPTERS, Preset, roll_d20
from strands_decider_rpg.engine import CONFIDENCE_BAR, Fate, finish_campaign, tally

EXPECTED: dict[tuple[int, Preset], tuple[str, bool]] = {
    (1, Preset.BOLD): ("BOLD", True),
    (1, Preset.CAUTIOUS): ("CAUTIOUS", True),
    (1, Preset.UNSURE): ("HESITATE", False),
    (2, Preset.BOLD): ("SHELL", True),
    (2, Preset.CAUTIOUS): ("HTTP_REQUEST", True),
    (2, Preset.UNSURE): ("HESITATE", False),
    (3, Preset.BOLD): ("SUCCESS", True),
    (3, Preset.CAUTIOUS): ("FAILURE", True),
    (3, Preset.UNSURE): ("FAILURE", False),
    (4, Preset.BOLD): ("PORTAL_OPENS", True),
    (4, Preset.CAUTIOUS): ("PORTAL_REFUSES", True),
    (4, Preset.UNSURE): ("HESITATE", False),
    (5, Preset.BOLD): ("CHARGE", True),
    (5, Preset.CAUTIOUS): ("PARLEY", True),
    (5, Preset.UNSURE): ("HESITATE", False),
}


@pytest.mark.parametrize(("chapter", "preset"), sorted(EXPECTED))
def test_every_chapter_every_preset(chapter: int, preset: Preset) -> None:
    spec = CHAPTERS[chapter]
    result = spec.play(spec.scripted(preset), spec.info.default_say, CONFIDENCE_BAR, 7)
    assert (result.branch, result.acted) == EXPECTED[(chapter, preset)]
    assert result.chapter == chapter


def test_seed_7_dice() -> None:
    # Chapter 3's presets rely on this: one d20 beats DC 10, disadvantage does not.
    assert 10 <= roll_d20(7) < 20
    assert roll_d20(7, disadvantage=True) < 10


def test_an_unsure_score_rolls_with_disadvantage() -> None:
    spec = CHAPTERS[3]
    result = spec.play(spec.scripted(Preset.UNSURE), spec.info.default_say, CONFIDENCE_BAR, 7)
    assert "disadvantage" in result.detail


def test_chapter_five_needs_confident_allies_to_agree() -> None:
    spec = CHAPTERS[5]
    result = spec.play(spec.scripted(Preset.UNSURE), spec.info.default_say, CONFIDENCE_BAR, 7)
    assert "disagree" in result.narration
    assert result.round_trips == 2


def test_chapter_four_asks_three_questions_in_one_round_trip() -> None:
    spec = CHAPTERS[4]
    result = spec.play(spec.scripted(Preset.BOLD), spec.info.default_say, CONFIDENCE_BAR, 7)
    assert (len(result.answers), result.round_trips) == (3, 1)


@pytest.mark.parametrize(
    ("fates", "expected"),
    [
        ([Fate.GLORY, Fate.GLORY, Fate.CUNNING], Fate.GLORY),
        ([Fate.CUNNING, Fate.TABLE, Fate.CUNNING], Fate.CUNNING),
        ([Fate.GLORY, Fate.CUNNING], Fate.TABLE),
    ],
)
def test_tally(fates: list[Fate], expected: Fate) -> None:
    assert tally(fates) == expected


@pytest.mark.parametrize(
    ("preset", "fate"),
    [(Preset.BOLD, Fate.GLORY), (Preset.CAUTIOUS, Fate.CUNNING), (Preset.UNSURE, Fate.TABLE)],
)
def test_campaign_reaches_each_final_ending(preset: Preset, fate: Fate) -> None:
    results = [
        spec.play(spec.scripted(preset), spec.info.default_say, CONFIDENCE_BAR, 7)
        for spec in CHAPTERS.values()
    ]
    assert finish_campaign(results).fate == fate


def test_cli_campaign_runs(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["campaign", "--script", "unsure"]) == 0
    assert "The Table Remembers" in capsys.readouterr().out


def test_cli_reports_an_unreachable_decider(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["chapter", "1", "--decider", "http", "--council", "http://127.0.0.1:9"]) == 2
    assert "decider unreachable" in capsys.readouterr().err
