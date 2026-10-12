"""Tests for all five chapters and the campaign: every chapter, every preset, scripted."""

from __future__ import annotations

import pytest

from strands_decider_rpg.__main__ import main
from strands_decider_rpg.chapters import CHAPTERS, Preset, roll_d6
from strands_decider_rpg.engine import CONFIDENCE_BAR, Fate, finish_campaign, tally

EXPECTED: dict[tuple[int, Preset], tuple[str, bool]] = {
    (1, Preset.BOLD): ("SURPRISED", True),
    (1, Preset.CAUTIOUS): ("SEEN_FIRST", True),
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
    (5, Preset.BOLD): ("NO_AGENT", True),
    (5, Preset.CAUTIOUS): ("CHARACTER_AGENT", True),
    (5, Preset.UNSURE): ("HESITATE", False),
}


@pytest.mark.parametrize(("chapter", "preset"), sorted(EXPECTED))
def test_every_chapter_every_preset(chapter: int, preset: Preset) -> None:
    spec = CHAPTERS[chapter]
    result = spec.play(spec.scripted(preset), spec.info.default_say, CONFIDENCE_BAR, 7)
    assert (result.branch, result.acted) == EXPECTED[(chapter, preset)]
    assert result.chapter == chapter


def test_seed_7_dice() -> None:
    # The presets rely on this: one d6 beats 3+ but not 4+ or 5+; keeping the lower of two
    # misses 3+.
    assert roll_d6(7) == 3
    assert roll_d6(7, keep_lower=True) < 3


def test_chapter_one_rolls_only_when_a_check_is_needed() -> None:
    spec = CHAPTERS[1]
    say = spec.info.default_say
    checked = spec.play(spec.scripted(Preset.CAUTIOUS), say, CONFIDENCE_BAR, 9)
    unchecked = spec.play(spec.scripted(Preset.BOLD), say, CONFIDENCE_BAR, 9)
    assert (checked.branch, checked.detail) == (
        "SPOTS_FIRST",
        "perception check -> needs 4+; the d6 shows 4",
    )
    assert (unchecked.branch, unchecked.detail) == ("SURPRISED", "")


def test_an_unsure_score_rolls_twice_and_keeps_the_lower() -> None:
    spec = CHAPTERS[3]
    result = spec.play(spec.scripted(Preset.UNSURE), spec.info.default_say, CONFIDENCE_BAR, 7)
    assert "twice, keep the lower" in result.detail


def test_chapter_five_asks_the_player_before_calling_an_unsure_agent() -> None:
    spec = CHAPTERS[5]
    result = spec.play(spec.scripted(Preset.UNSURE), spec.info.default_say, CONFIDENCE_BAR, 7)
    assert (result.branch, result.acted, result.round_trips) == ("HESITATE", False, 1)


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


def test_cli_campaign_runs(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The CLI always asks the local server; swap in fixed answers to test it offline.
    monkeypatch.setattr(
        "strands_decider_rpg.__main__._deciders",
        lambda chapter: CHAPTERS[chapter].scripted(Preset.UNSURE),
    )
    assert main(["campaign"]) == 0
    assert "The Table Remembers" in capsys.readouterr().out


def test_cli_reports_an_unreachable_decider(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A dead URL must fail loudly and point at the fix.
    monkeypatch.setattr("strands_decider_rpg.__main__.DECIDER_URL", "http://127.0.0.1:9")
    assert main(["chapter", "1"]) == 2
    err = capsys.readouterr().err
    assert "decider unreachable" in err
    assert "Start the model server first" in err
