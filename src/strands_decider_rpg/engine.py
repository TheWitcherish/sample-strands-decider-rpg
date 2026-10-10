"""The branching engine: ask the decider, route on confidence, return a typed result.

The whole experiment lives in :func:`play_chapter`. A chapter carries one yes/no question; the
decider answers it; and the ending is chosen by *how sure* the model is. Below the threshold the
Game Master hesitates -- mirroring the model card's own advice: at low confidence, ask a person.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

from strands_decider_rpg.decider import Decider, Decision
from strands_decider_rpg.story import Branch, Chapter

CONFIDENCE_BAR: Final[float] = 0.75
"""The 'sure enough to act' bar. Below it, the engine hands control back to the table."""


class PlayResult(BaseModel):
    """The boundary contract a frontend renders. Frozen: a result is a record, not a workspace.

    Attributes:
        chapter: Chapter number played.
        chapter_title: Chapter title.
        noul: Raw yes/no score the decider returned, in ``[0, 1]``.
        confidence: Derived reliability of the verdict, in ``[0.5, 1.0]``.
        acted_confidently: True when confidence cleared the bar and the engine acted on the
            verdict; False when it hesitated and handed control back to the table.
        branch: Branch label taken (``BOLD`` / ``CAUTIOUS`` / ``HESITATE``).
        narration: The narration shown for the chosen branch.
        ending_key: Stable key of the ending reached.
        ending_title: Human title of the ending.
        ending_prose: The ending text.
    """

    model_config = ConfigDict(frozen=True)

    chapter: int
    chapter_title: str
    noul: float
    confidence: float
    acted_confidently: bool
    branch: str
    narration: str
    ending_key: str
    ending_title: str
    ending_prose: str


def _choose_branch(chapter: Chapter, decision: Decision, *, bar: float) -> tuple[Branch, bool]:
    if decision.confidence < bar:
        return chapter.hesitate, False
    return (chapter.bold, True) if decision.yes else (chapter.cautious, True)


def play_chapter(chapter: Chapter, decider: Decider, *, bar: float = CONFIDENCE_BAR) -> PlayResult:
    """Play one chapter: put its question to the decider and route on the confidence.

    Args:
        chapter: The chapter to play (read-only; never mutated).
        decider: Any backend satisfying the ``Decider`` contract.
        bar: Confidence threshold to act on the verdict instead of hesitating.

    Returns:
        A frozen :class:`PlayResult` describing the branch taken and the ending reached.
    """
    (decision,) = decider.decide(chapter.state, (chapter.question,))
    branch, acted = _choose_branch(chapter, decision, bar=bar)
    return PlayResult(
        chapter=chapter.number,
        chapter_title=chapter.title,
        noul=decision.value,
        confidence=decision.confidence,
        acted_confidently=acted,
        branch=branch.label,
        narration=branch.narration,
        ending_key=branch.ending.key,
        ending_title=branch.ending.title,
        ending_prose=branch.ending.prose,
    )
