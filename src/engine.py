"""The shared engine: chapter metadata, the typed result contract, and the campaign tally.

Every chapter asks the decider something, then routes on *how sure* it is. Below the bar the AI
Game Master hesitates and hands the dice to the table -- the model card's own advice: at a
confidence of 0.9 or more answers are right about 95% of the time; below that, ask a person.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from decider import Answer, Verdict

CONFIDENCE_BAR: Final[float] = 0.8
"""The 'sure enough to act' bar.

The decider README's line for acting automatically is 0.9 (about 95% right). A game can afford a
little more risk -- a wrong call costs a story beat, not a refund -- so the default is 0.8.
Pass ``--bar 0.9`` to play by the README's rule.
"""


class Fate(StrEnum):
    """What a chapter's outcome adds to the campaign's final ending."""

    GLORY = "glory"
    CUNNING = "cunning"
    TABLE = "table"


@dataclass(frozen=True, slots=True)
class ChapterInfo:
    """Static description of a chapter."""

    number: int
    title: str
    opening: str
    default_say: str


@dataclass(frozen=True, slots=True)
class Branch:
    """One outcome of a chapter, and the fate it adds to the campaign."""

    label: str
    narration: str
    ending_title: str
    ending_prose: str
    fate: Fate


class ChapterResult(BaseModel):
    """The boundary contract a frontend renders for one chapter. Frozen: a record, not a workspace.

    Attributes:
        chapter: Chapter number.
        title: Chapter title.
        opening: Scene narrated before the decision.
        say: What the adventurer said.
        model: Model name that answered.
        latency_ms: Server-side decider time for this chapter.
        round_trips: Requests sent to the decider.
        answers: Every answer the decider returned, by question key.
        confidence: The confidence the routing was decided on.
        acted: True when the AI Game Master acted; False when it handed control to the table.
        branch: Branch label taken.
        detail: One line of chapter-specific evidence (a dice roll, the agents called).
        narration: Narration for the branch.
        ending_title: Title of the chapter ending.
        ending_prose: Text of the chapter ending.
        fate: What this chapter adds to the campaign ending.
    """

    model_config = ConfigDict(frozen=True)

    chapter: int
    title: str
    opening: str
    say: str
    model: str
    latency_ms: float
    round_trips: int
    answers: Mapping[str, Answer]
    confidence: float
    acted: bool
    branch: str
    detail: str
    narration: str
    ending_title: str
    ending_prose: str
    fate: Fate


def scene(info: ChapterInfo, say: str) -> str:
    """Build the state the decider reads: the scene, then the adventurer's words."""
    return f'{info.opening}\nThe adventurer says: "{say}"'


def resolve(
    info: ChapterInfo,
    say: str,
    verdict: Verdict,
    branch: Branch,
    *,
    confidence: float,
    acted: bool,
    detail: str = "",
) -> ChapterResult:
    """Fold a chapter's verdict and chosen branch into its frozen result."""
    return ChapterResult(
        chapter=info.number,
        title=info.title,
        opening=info.opening,
        say=say,
        model=verdict.model,
        latency_ms=verdict.latency_ms,
        round_trips=1,  # every chapter asks all its questions in one request
        answers=verdict.answers,
        confidence=confidence,
        acted=acted,
        branch=branch.label,
        detail=detail,
        narration=branch.narration,
        ending_title=branch.ending_title,
        ending_prose=branch.ending_prose,
        fate=branch.fate,
    )


# --- The campaign ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CampaignEnding:
    """The final ending of the five-chapter campaign."""

    title: str
    prose: str


CAMPAIGN_ENDINGS: Final[Mapping[Fate, CampaignEnding]] = {
    Fate.GLORY: CampaignEnding(
        title="The Legend of the Loud",
        prose=(
            "Five chapters, and the decider never once flinched. The bards run out of rhymes for"
            " 'reckless'. Your statue has its sword drawn and a bramblehoot beside it."
        ),
    ),
    Fate.CUNNING: CampaignEnding(
        title="The Quiet Crown",
        prose=(
            "Nobody saw you coming, and that was the plan. The kingdom changes hands without a"
            " single song written about it. You prefer it that way."
        ),
    ),
    Fate.TABLE: CampaignEnding(
        title="The Table Remembers",
        prose=(
            "The decider knew what it did not know, so the players made the calls that mattered."
            " Nobody remembers the dragon. Everybody remembers the night the table decided."
        ),
    ),
}


class CampaignResult(BaseModel):
    """The boundary contract for a full five-chapter run."""

    model_config = ConfigDict(frozen=True)

    chapters: tuple[ChapterResult, ...]
    fate: Fate
    ending_title: str
    ending_prose: str
    questions_asked: int
    round_trips: int
    decider_ms: float


def tally(fates: Sequence[Fate]) -> Fate:
    """Pick the campaign fate: the most frequent one; a tie at the top goes to the table.

    Raises:
        ValueError: If ``fates`` is empty.
    """
    if not fates:
        raise ValueError("cannot tally an empty campaign")
    ranked = Counter(fates).most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return Fate.TABLE
    return ranked[0][0]


def finish_campaign(chapters: Sequence[ChapterResult]) -> CampaignResult:
    """Tally the chapters into the campaign ending.

    Raises:
        ValueError: If ``chapters`` is empty.
    """
    fate = tally([c.fate for c in chapters])
    ending = CAMPAIGN_ENDINGS[fate]
    return CampaignResult(
        chapters=tuple(chapters),  # explicit copy: the result owns its own sequence
        fate=fate,
        ending_title=ending.title,
        ending_prose=ending.prose,
        questions_asked=sum(len(c.answers) for c in chapters),
        round_trips=sum(c.round_trips for c in chapters),
        decider_ms=sum(c.latency_ms for c in chapters),
    )
