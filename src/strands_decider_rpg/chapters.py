"""The five chapters of Once Upon Agentic AI, each replayed around one decider capability.

| Chapter | Workshop topic          | Decider capability shown                         |
| ------- | ----------------------- | ------------------------------------------------ |
| 1       | Agent Summoning         | ``noul``: a yes/no with a calibrated confidence  |
| 2       | Vended Tools            | ``choice``: tool selection in one forward pass   |
| 3       | Custom Tools (dice)     | ``score``: an ordered rubric sets the dice DC    |
| 4       | MCP portals             | three guard questions, one round trip            |
| 5       | A2A Grand Alliance      | a council of deciders (any model variant) votes  |
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from strands_decider_rpg.decider import (
    ChoiceAnswer,
    ChoiceQuestion,
    Decider,
    NoulAnswer,
    ScoreAnswer,
    ScoreQuestion,
    ScriptedDecider,
    YesNoQuestion,
)
from strands_decider_rpg.engine import Branch, ChapterInfo, ChapterResult, Fate, resolve, scene


class Preset(StrEnum):
    """Scripted runs for the offline demo: what the fake decider will answer."""

    BOLD = "bold"
    CAUTIOUS = "cautious"
    UNSURE = "unsure"


def _hesitate(what: str) -> Branch:
    return Branch(
        label="HESITATE",
        narration=f"The Game Master pauses. {what} -- too close to call, so the dice go to you.",
        ending_title="The Table Decides",
        ending_prose=(
            "A good Game Master knows when not to improvise: a confident wrong turn is worse than"
            " an honest question."
        ),
        fate=Fate.TABLE,
    )


def _choice(picked: str, confidence: float, options: Sequence[str]) -> ChoiceAnswer:
    rest = (1.0 - confidence) / max(len(options) - 1, 1)
    probs = {o: (confidence if o == picked else rest) for o in options}
    return ChoiceAnswer(choice=picked, probabilities=probs, confidence=confidence)


# --- Chapter 1: The Art of Agent Summoning (noul) --------------------------------------------

CH1: Final = ChapterInfo(
    number=1,
    title="The Art of Agent Summoning",
    opening=(
        "The tavern door is shut against the rain. Inside, a quest waits. A freshly summoned"
        " adventurer steps up to the threshold."
    ),
    default_say="I kick the door open and stride in, blade drawn, ready for anything!",
)
CH1_Q: Final = YesNoQuestion(
    key="is_bold",
    instructions="Is the adventurer charging in boldly?",
    criteria={
        "true": "The adventurer acts loudly, fast or aggressively without checking first",
        "false": "The adventurer watches, scouts, waits or acts quietly first",
    },
)
CH1_BOLD: Final = Branch(
    "BOLD",
    "The door bangs off the wall, every head turns, and the quest comes to you -- loudly.",
    "A Blaze of Glory",
    "The bards will sing of the night you walked in like thunder. Short song. Great chorus.",
    Fate.GLORY,
)
CH1_CAUTIOUS: Final = Branch(
    "CAUTIOUS",
    "You read the room before the room reads you, and slip in along the wall.",
    "The Long Game",
    "You leave knowing three secrets nobody meant to tell you, and the night is still young.",
    Fate.CUNNING,
)


def play_chapter_one(deciders: Sequence[Decider], say: str, bar: float) -> ChapterResult:
    """Chapter 1: one yes/no question; its confidence picks bold, cautious, or the table."""
    verdict = deciders[0].decide(scene(CH1, say), (CH1_Q,))
    answer = verdict.noul(CH1_Q.key)
    acted = answer.confidence >= bar
    branch = (CH1_BOLD if answer.yes else CH1_CAUTIOUS) if acted else _hesitate("Bold or careful")
    return resolve(CH1, say, (verdict,), branch, confidence=answer.confidence, acted=acted)


CH1_SCRIPTS: Final[Mapping[Preset, Mapping[str, NoulAnswer]]] = {
    Preset.BOLD: {"is_bold": NoulAnswer(noul=0.98)},
    Preset.CAUTIOUS: {"is_bold": NoulAnswer(noul=0.02)},
    Preset.UNSURE: {"is_bold": NoulAnswer(noul=0.58)},
}


# --- Chapter 2: The Adventurer's Arsenal (choice = tool selection) ---------------------------

CH2: Final = ChapterInfo(
    number=2,
    title="The Adventurer's Arsenal",
    opening=(
        "Kiro the Grey Hat unrolls the arsenal: a rulebook that answers over http, a shell that"
        " casts raw commands, and a quill that writes scrolls. One tool per request."
    ),
    default_say="What does a beholder's eye ray do? Look it up in the official rules.",
)
CH2_OPTIONS: Final[Mapping[str, str]] = {
    "http_request": "Look something up in the online 5e SRD rules",
    "shell": "Run a command on the wizard's machine",
    "file_editor": "Write or edit a scroll (a file)",
}
CH2_Q: Final = ChoiceQuestion(
    key="tool",
    instructions="Which tool from the arsenal fits the adventurer's request?",
    options=CH2_OPTIONS,
)
CH2_BRANCHES: Final[Mapping[str, Branch]] = {
    "http_request": Branch(
        "HTTP_REQUEST",
        "The rulebook glows and answers. Knowledge, fetched in one call, no guessing.",
        "The Scholar's Edge",
        "You walk into the next fight already knowing how it ends.",
        Fate.CUNNING,
    ),
    "shell": Branch(
        "SHELL",
        "The shell crackles. Raw power -- and the workshop's HumanInTheLoop gate asks you first.",
        "The Spark of Command",
        "One approved command, and the dungeon's lights come on at once.",
        Fate.GLORY,
    ),
    "file_editor": Branch(
        "FILE_EDITOR",
        "The quill scratches a fresh scroll. HumanInTheLoop asks you to approve the ink.",
        "The Written Word",
        "The scroll outlives the adventure. Somebody, someday, reads it at exactly the right time.",
        Fate.CUNNING,
    ),
}


def play_chapter_two(deciders: Sequence[Decider], say: str, bar: float) -> ChapterResult:
    """Chapter 2: a choice question picks the tool; low confidence means ask instead of guess."""
    verdict = deciders[0].decide(scene(CH2, say), (CH2_Q,))
    answer = verdict.choice(CH2_Q.key)
    acted = answer.confidence >= bar
    branch = CH2_BRANCHES[answer.choice] if acted else _hesitate("Which tool, though")
    return resolve(CH2, say, (verdict,), branch, confidence=answer.confidence, acted=acted)


CH2_SCRIPTS: Final[Mapping[Preset, Mapping[str, ChoiceAnswer]]] = {
    Preset.BOLD: {"tool": _choice("shell", 0.95, tuple(CH2_OPTIONS))},
    Preset.CAUTIOUS: {"tool": _choice("http_request", 0.96, tuple(CH2_OPTIONS))},
    Preset.UNSURE: {"tool": _choice("file_editor", 0.41, tuple(CH2_OPTIONS))},
}


# --- Chapter 3: The Art of Magical Forging (score sets the dice) -----------------------------

CH3: Final = ChapterInfo(
    number=3,
    title="The Art of Magical Forging",
    opening=(
        "Lady Luck, keeper of the freshly forged roll_dice tool, spins a d20 between two"
        " fingers. 'Tell me your plan, darling, and I will tell you how hard it is.'"
    ),
    default_say="I leap off the balcony onto the chandelier and swing across the hall!",
)
CH3_RUBRIC: Final[tuple[str, ...]] = ("trivial", "risky", "dangerous", "deadly")
CH3_DC: Final[tuple[int, ...]] = (5, 10, 15, 20)
CH3_Q: Final = ScoreQuestion(
    key="danger",
    instructions="How dangerous is the adventurer's plan?",
    rubric=CH3_RUBRIC,
)
CH3_SUCCESS: Final = Branch(
    "SUCCESS",
    "The d20 lands. It beats the DC. Lady Luck applauds, theatrically.",
    "Fortune Favours",
    "You stick the landing. Nobody believes you planned it. You did not.",
    Fate.GLORY,
)
CH3_FAILURE: Final = Branch(
    "FAILURE",
    "The d20 lands short of the DC. Lady Luck winces, kindly.",
    "The Graceful Fall",
    "You miss, roll, and come up behind the guards. Was that the plan all along? It is now.",
    Fate.CUNNING,
)


def roll_d20(seed: int, *, disadvantage: bool = False) -> int:
    """Roll a d20 from a seeded generator this function owns, so a run is reproducible.

    With ``disadvantage``, roll twice and keep the lower die.
    """
    rng = random.Random(seed)
    first = rng.randint(1, 20)
    return min(first, rng.randint(1, 20)) if disadvantage else first


def play_chapter_three(
    deciders: Sequence[Decider], say: str, bar: float, seed: int
) -> ChapterResult:
    """Chapter 3: the score sets the DC, and the confidence is a dial, not a gate.

    A sure Game Master rolls one d20. An unsure one makes you roll with disadvantage: the
    uncertainty is priced into the dice instead of stopping the game.
    """
    verdict = deciders[0].decide(scene(CH3, say), (CH3_Q,))
    answer = verdict.score(CH3_Q.key)
    sure = answer.confidence >= bar
    level = min(answer.level, len(CH3_RUBRIC) - 1)
    dc, roll = CH3_DC[level], roll_d20(seed, disadvantage=not sure)
    branch = CH3_SUCCESS if roll >= dc else CH3_FAILURE
    how = "roll_dice(20)" if sure else "roll_dice(20) with disadvantage (unsure GM)"
    detail = f"danger={CH3_RUBRIC[level]} -> DC {dc}; {how} = {roll}"
    return resolve(
        CH3, say, (verdict,), branch, confidence=answer.confidence, acted=sure, detail=detail
    )


CH3_SCRIPTS: Final[Mapping[Preset, Mapping[str, ScoreAnswer]]] = {
    Preset.BOLD: {
        "danger": ScoreAnswer(
            score=1.0, probabilities={"0": 0.02, "1": 0.95, "2": 0.02, "3": 0.01}, confidence=0.93
        )
    },
    Preset.CAUTIOUS: {
        "danger": ScoreAnswer(
            score=3.0, probabilities={"0": 0.0, "1": 0.01, "2": 0.03, "3": 0.96}, confidence=0.95
        )
    },
    Preset.UNSURE: {
        "danger": ScoreAnswer(
            score=1.5, probabilities={"0": 0.4, "1": 0.1, "2": 0.1, "3": 0.4}, confidence=0.12
        )
    },
}


# --- Chapter 4: Planar Portals (three guards, one round trip) --------------------------------

CH4: Final = ChapterInfo(
    number=4,
    title="Planar Portals",
    opening=(
        "The MCP portal hums. Behind it, Lady Luck's dice roller now lives on another plane."
        " Before any call crosses over, three wards check the request."
    ),
    default_say="Open a portal! Anywhere! Just do it!",
)
CH4_QS: Final[tuple[YesNoQuestion, ...]] = (
    YesNoQuestion(key="wants_portal", instructions="Is the adventurer asking to open a portal?"),
    YesNoQuestion(
        key="names_place",
        instructions="Does the adventurer name a destination?",
        criteria={"true": "A specific place is named", "false": "No place, or 'anywhere'"},
    ),
    YesNoQuestion(
        key="is_safe",
        instructions="Is it safe to open this portal?",
        criteria={
            "true": "A known, friendly place the party asked to go to",
            "false": "Somewhere hostile, unknown, or a reckless demand",
        },
    ),
)
CH4_OPEN: Final = Branch(
    "PORTAL_OPENS",
    "All three wards glow green in a single pulse. The call crosses the portal.",
    "Through the Veil",
    "You step out into the Feywild. The ogre steps out too. Different problem, prettier scenery.",
    Fate.GLORY,
)
CH4_REFUSE: Final = Branch(
    "PORTAL_REFUSES",
    "A ward flares red. The portal does not guess; it asks a sharper question instead.",
    "The Wise Refusal",
    "The portal stays shut and the ogre knocks politely. You have time to think. Use it.",
    Fate.CUNNING,
)


def play_chapter_four(deciders: Sequence[Decider], say: str, bar: float) -> ChapterResult:
    """Chapter 4: three yes/no wards in ONE request -- the state is read once, not three times."""
    verdict = deciders[0].decide(scene(CH4, say), CH4_QS)
    wards = tuple(verdict.noul(q.key) for q in CH4_QS)
    confident = [w for w in wards if w.confidence >= bar]
    weakest = min(w.confidence for w in wards)
    detail = " ".join(f"{q.key}={w.summary}" for q, w in zip(CH4_QS, wards, strict=True))
    if any(not w.yes for w in confident):
        branch, acted, conf = CH4_REFUSE, True, max(w.confidence for w in confident if not w.yes)
    elif len(confident) == len(wards):
        branch, acted, conf = CH4_OPEN, True, weakest
    else:
        branch, acted, conf = _hesitate("A ward flickers"), False, weakest
    return resolve(CH4, say, (verdict,), branch, confidence=conf, acted=acted, detail=detail)


CH4_SCRIPTS: Final[Mapping[Preset, Mapping[str, NoulAnswer]]] = {
    Preset.BOLD: {
        "wants_portal": NoulAnswer(noul=0.99),
        "names_place": NoulAnswer(noul=0.97),
        "is_safe": NoulAnswer(noul=0.96),
    },
    Preset.CAUTIOUS: {
        "wants_portal": NoulAnswer(noul=0.99),
        "names_place": NoulAnswer(noul=0.03),
        "is_safe": NoulAnswer(noul=0.9),
    },
    Preset.UNSURE: {
        "wants_portal": NoulAnswer(noul=0.98),
        "names_place": NoulAnswer(noul=0.97),
        "is_safe": NoulAnswer(noul=0.55),
    },
}


# --- Chapter 5: The Grand Alliance (a council of deciders) -----------------------------------

CH5: Final = ChapterInfo(
    number=5,
    title="The Grand Alliance",
    opening=(
        "The dragon lands on the bridge. The Game Master calls the alliance over A2A: each ally"
        " answers alone, and the Game Master only acts if the confident allies agree."
    ),
    default_say="The dragon bows its head, folds its wings and asks to make a deal.",
)
CH5_OPTIONS: Final[Mapping[str, str]] = {
    "charge": "Attack the dragon head-on",
    "parley": "Talk to the dragon and strike a deal",
    "sneak": "Slip past the dragon while it is distracted",
}
CH5_ROLES: Final[tuple[str, ...]] = (
    "You are the Rules Agent: judge by the rules of the game and the dragon's stat block.",
    "You are the Character Agent: you know the party, a level-2 bard and a level-3 rogue.",
)
CH5_Q: Final = ChoiceQuestion(
    key="plan",
    instructions="How should the party face the dragon?",
    options=CH5_OPTIONS,
)
CH5_BRANCHES: Final[Mapping[str, Branch]] = {
    "charge": Branch(
        "CHARGE",
        "The alliance agrees: steel first, questions never.",
        "Dragonfall",
        "The dragon did not expect a level-2 bard to hit that hard. Neither did the bard.",
        Fate.GLORY,
    ),
    "parley": Branch(
        "PARLEY",
        "The alliance agrees: the lute comes out before the swords do.",
        "The Dragon's Encore",
        "The dragon wanted a song, not a snack. It has a standing booking now, every full moon.",
        Fate.CUNNING,
    ),
    "sneak": Branch(
        "SNEAK",
        "The alliance agrees: while the dragon admires the lute, the rogue does the rest.",
        "The Empty Hoard",
        "By the time the dragon finishes the song, its hoard is three gold coins lighter. Per bar.",
        Fate.CUNNING,
    ),
}


def ally_name(index: int) -> str:
    """The display name of the ally at ``index`` in the council."""
    return ("Rules Agent", "Character Agent")[index] if index < 2 else f"Ally {index + 1}"


def play_chapter_five(deciders: Sequence[Decider], say: str, bar: float) -> ChapterResult:
    """Chapter 5: every ally answers alone; act only when all confident allies agree.

    With one decider, both allies run on it (two round trips, two roles). With several, each
    ally runs on its own server -- point them at different model variants and watch them argue.
    """
    allies = list(deciders) if len(deciders) > 1 else [deciders[0], deciders[0]]
    verdicts = []
    for index, decider in enumerate(allies):
        role = CH5_ROLES[index % len(CH5_ROLES)]
        verdicts.append(decider.decide(f"{role}\n{scene(CH5, say)}", (CH5_Q,)))
    votes = [v.choice(CH5_Q.key) for v in verdicts]
    answers = {f"{CH5_Q.key}:{ally_name(i)}": vote for i, vote in enumerate(votes)}
    detail = "; ".join(
        f"{ally_name(i)} [{v.model}] -> {vote.choice}"
        f" ({vote.confidence:.2f}, {v.latency_ms:.0f} ms)"
        for i, (v, vote) in enumerate(zip(verdicts, votes, strict=True))
    )
    confident = [vote for vote in votes if vote.confidence >= bar]
    picks = {vote.choice for vote in confident}
    if len(picks) == 1:
        branch, acted = CH5_BRANCHES[picks.pop()], True
        conf = min(vote.confidence for vote in confident)
    else:
        why = "The allies disagree" if picks else "No ally is sure"
        branch, acted = _hesitate(why), False
        conf = max(vote.confidence for vote in votes)
    return resolve(
        CH5, say, verdicts, branch, confidence=conf, acted=acted, detail=detail, answers=answers
    )


CH5_SCRIPTS: Final[Mapping[Preset, tuple[Mapping[str, ChoiceAnswer], ...]]] = {
    Preset.BOLD: (
        {"plan": _choice("charge", 0.94, tuple(CH5_OPTIONS))},
        {"plan": _choice("charge", 0.91, tuple(CH5_OPTIONS))},
    ),
    Preset.CAUTIOUS: (
        {"plan": _choice("parley", 0.95, tuple(CH5_OPTIONS))},
        {"plan": _choice("parley", 0.6, tuple(CH5_OPTIONS))},
    ),
    Preset.UNSURE: (
        {"plan": _choice("parley", 0.93, tuple(CH5_OPTIONS))},
        {"plan": _choice("sneak", 0.92, tuple(CH5_OPTIONS))},
    ),
}


# --- The chapter table -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChapterSpec:
    """How to play one chapter, and how to fake its decider offline."""

    info: ChapterInfo
    play: Callable[[Sequence[Decider], str, float, int], ChapterResult]
    scripted: Callable[[Preset], tuple[Decider, ...]]


def _single(
    scripts: Mapping[Preset, Mapping[str, NoulAnswer | ChoiceAnswer | ScoreAnswer]],
) -> Callable[[Preset], tuple[Decider, ...]]:
    return lambda preset: (ScriptedDecider(answers=scripts[preset]),)


CHAPTERS: Final[Mapping[int, ChapterSpec]] = {
    1: ChapterSpec(CH1, lambda d, s, b, _: play_chapter_one(d, s, b), _single(CH1_SCRIPTS)),
    2: ChapterSpec(CH2, lambda d, s, b, _: play_chapter_two(d, s, b), _single(CH2_SCRIPTS)),
    3: ChapterSpec(CH3, play_chapter_three, _single(CH3_SCRIPTS)),
    4: ChapterSpec(CH4, lambda d, s, b, _: play_chapter_four(d, s, b), _single(CH4_SCRIPTS)),
    5: ChapterSpec(
        CH5,
        lambda d, s, b, _: play_chapter_five(d, s, b),
        lambda preset: tuple(ScriptedDecider(answers=a) for a in CH5_SCRIPTS[preset]),
    ),
}
