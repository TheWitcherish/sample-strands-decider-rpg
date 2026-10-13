"""Every chapter against the real Strands Decider, plus the few rules that need no model.

Start the model server first (see Getting Started in the README), then ``uv run pytest``. The
model picks the branch, so the chapter tests assert the contract and the clear-cut calls.
"""

from __future__ import annotations

import httpx
import pytest

from chapters import CHAPTERS
from cli import main
from decider import HttpDecider, NoulAnswer
from engine import CONFIDENCE_BAR, ChapterResult, Fate, finish_campaign, tally


@pytest.fixture(scope="module")
def decider() -> HttpDecider:
    """The local model server, or one clear message instead of a traceback per test."""
    live = HttpDecider()
    try:
        httpx.get(live.base_url, timeout=5.0)
    except httpx.HTTPError:
        pytest.exit(
            f"decider unreachable at {live.base_url}: start the model server first"
            " (see Getting Started in the README)",
            returncode=1,
        )
    return live


def _play(decider: HttpDecider, chapter: int, say: str | None = None) -> ChapterResult:
    spec = CHAPTERS[chapter]
    return spec.play(decider, say or spec.info.default_say, CONFIDENCE_BAR, 7)


# --- On the real model -----------------------------------------------------------------------


@pytest.mark.parametrize("chapter", sorted(CHAPTERS))
def test_every_chapter_plays(decider: HttpDecider, chapter: int) -> None:
    result = _play(decider, chapter)
    assert result.chapter == chapter
    assert result.round_trips == 1
    assert result.latency_ms > 0
    assert 0.0 <= result.confidence <= 1.0


def test_chapter_one_calls_for_a_check_when_the_adventurer_looks(decider: HttpDecider) -> None:
    assert _play(decider, 1).answers["needs_check"].summary.startswith("yes")


def test_chapter_one_skips_the_check_when_the_adventurer_walks_on(decider: HttpDecider) -> None:
    result = _play(decider, 1, "I ignore the noise and keep walking.")
    assert result.answers["needs_check"].summary.startswith("no")


def test_chapter_two_picks_the_rulebook(decider: HttpDecider) -> None:
    assert _play(decider, 2).answers["tool"].summary == "http_request"


def test_chapter_four_refuses_a_portal_with_no_destination(decider: HttpDecider) -> None:
    result = _play(decider, 4)
    assert result.answers["names_place"].summary.startswith("no")
    assert result.branch == "PORTAL_REFUSES"


def test_chapter_five_sends_a_rules_question_to_the_rules_agent(decider: HttpDecider) -> None:
    assert _play(decider, 5).answers["specialist"].summary == "rules_agent"


def test_campaign_finishes(decider: HttpDecider) -> None:
    campaign = finish_campaign([_play(decider, n) for n in sorted(CHAPTERS)])
    assert (campaign.round_trips, campaign.questions_asked) == (5, 7)


@pytest.mark.usefixtures("decider")
def test_cli_plays_chapter_one_as_the_post_shows(capsys: pytest.CaptureFixture[str]) -> None:
    # Seed 7 rolls the 3 the blog post shows.
    assert main(["chapter", "1"]) == 0
    assert "the d6 shows 3" in capsys.readouterr().out


# --- No model needed -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("p", "yes", "conf"), [(0.95, True, 0.9), (0.05, False, 0.9), (0.5, True, 0.0)]
)
def test_yes_no_confidence_is_two_p_minus_one(p: float, yes: bool, conf: float) -> None:
    answer = NoulAnswer(noul=p)
    assert answer.yes is yes
    assert answer.confidence == pytest.approx(conf)


@pytest.mark.parametrize(
    ("fates", "expected"),
    [
        ([Fate.GLORY, Fate.GLORY, Fate.CUNNING], Fate.GLORY),
        ([Fate.CUNNING, Fate.TABLE, Fate.CUNNING], Fate.CUNNING),
        ([Fate.GLORY, Fate.CUNNING], Fate.TABLE),
    ],
)
def test_a_tie_at_the_top_goes_to_the_table(fates: list[Fate], expected: Fate) -> None:
    assert tally(fates) == expected


def test_cli_reports_an_unreachable_decider(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("cli.DECIDER_URL", "http://127.0.0.1:9")
    assert main(["chapter", "1"]) == 2
    err = capsys.readouterr().err
    assert "decider unreachable" in err
    assert "Start the model server first" in err
