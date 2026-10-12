"""The five chapters of Once Upon Agentic AI, each replayed around one decider capability.

| Chapter | Workshop topic          | Decider capability shown                         |
| ------- | ----------------------- | ------------------------------------------------ |
| 1       | Agent Summoning         | ``noul``: does this need a perception check?     |
| 2       | Vended Tools            | ``choice``: tool selection in one forward pass   |
| 3       | Custom Tools (dice)     | ``score``: an ordered rubric sets the d6 target  |
| 4       | MCP portals             | three guard questions, one round trip            |
| 5       | A2A Grand Alliance      | ``choice``: which specialist agent to call       |
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
        narration=f"The AI Game Master pauses. {what} -- too close to call, so the dice go to you.",
        ending_title="The Table Decides",
        ending_prose=(
            "A good AI Game Master knows when not to improvise: a confident wrong turn is worse"
            " than an honest question."
        ),
        fate=Fate.TABLE,
    )


def _choice(picked: str, confidence: float, options: Sequence[str]) -> ChoiceAnswer:
    rest = (1.0 - confidence) / max(len(options) - 1, 1)
    probs = {o: (confidence if o == picked else rest) for o in options}
    return ChoiceAnswer(choice=picked, probabilities=probs, confidence=confidence)


def roll_d6(seed: int, *, keep_lower: bool = False) -> int:
    """Roll a d6 from a seeded generator this function owns, so a run is reproducible.

    With ``keep_lower``, roll twice and keep the lower die.
    """
    rng = random.Random(seed)
    first = rng.randint(1, 6)
    return min(first, rng.randint(1, 6)) if keep_lower else first


# --- Chapter 1: The Art of Agent Summoning (noul = does this need a check?) ------------------

CH1: Final = ChapterInfo(
    number=1,
    title="The Art of Agent Summoning",
    opening=(
        "Your first adventure. The AI Game Master explains the only rule: you say what your"
        " character does, and it tells you what happens. You walk a forest path at dusk. Far off"
        " in the trees, something goes CRACK."
    ),
    default_say="Wait, what was that? I stop and look toward the sound.",
)
CH1_Q: Final = YesNoQuestion(
    key="needs_check",
    instructions="Does the adventurer's action call for a perception check, a roll to notice?",
    criteria={
        "true": "The adventurer actively stops, looks, listens or heads toward the sound",
        "false": "The adventurer chooses to ignore the sound and carries on without looking",
    },
)
CH1_NEEDS: Final[int] = 4
CH1_SPOTS_FIRST: Final = Branch(
    "SPOTS_FIRST",
    "The d6 beats the number. Between the trees you see it before it sees you: a bramblehoot,"
    " a bear with an owl's face.",
    "First Sight",
    "You have never met one before. It is sniffing the air, and it has smelled your coffee.",
    Fate.CUNNING,
)
CH1_SEEN_FIRST: Final = Branch(
    "SEEN_FIRST",
    "The d6 lands short of the number. Something big steps out of the brambles, and it saw you"
    " first: a bramblehoot, a bear with an owl's face.",
    "Face to Beak",
    "It tilts its head all the way sideways and hoots. You decide that was hello.",
    Fate.GLORY,
)
CH1_SURPRISED: Final = Branch(
    "SURPRISED",
    "No check, no roll. You walk on, and the noise steps onto the path: a bramblehoot, a bear"
    " with an owl's face.",
    "Some Squirrel",
    "You have never met one before. It has never met coffee before. You are about to be friends.",
    Fate.GLORY,
)


def play_chapter_one(deciders: Sequence[Decider], say: str, bar: float, seed: int) -> ChapterResult:
    """Chapter 1: decide whether the action needs a perception check, and only then roll.

    Sure it does: roll a d6 and beat the number. Sure it does not: no roll, the creature finds
    you. Unsure: the AI Game Master asks the player instead of guessing.
    """
    verdict = deciders[0].decide(scene(CH1, say), (CH1_Q,))
    answer = verdict.noul(CH1_Q.key)
    acted = answer.confidence >= bar
    detail = ""
    if not acted:
        branch = _hesitate("Roll or no roll")
    elif answer.yes:
        roll = roll_d6(seed)
        branch = CH1_SPOTS_FIRST if roll >= CH1_NEEDS else CH1_SEEN_FIRST
        detail = f"perception check -> needs {CH1_NEEDS}+; the d6 shows {roll}"
    else:
        branch = CH1_SURPRISED
    return resolve(
        CH1, say, (verdict,), branch, confidence=answer.confidence, acted=acted, detail=detail
    )


CH1_SCRIPTS: Final[Mapping[Preset, Mapping[str, NoulAnswer]]] = {
    Preset.BOLD: {"needs_check": NoulAnswer(noul=0.02)},
    Preset.CAUTIOUS: {"needs_check": NoulAnswer(noul=0.98)},
    Preset.UNSURE: {"needs_check": NoulAnswer(noul=0.58)},
}


# --- Chapter 2: The Adventurer's Arsenal (choice = tool selection) ---------------------------

CH2: Final = ChapterInfo(
    number=2,
    title="The Adventurer's Arsenal",
    opening=(
        "The bramblehoot is still sniffing your coffee when a Wizard steps out of the trees and"
        " unrolls the arsenal: a rulebook that answers over http, a shell that casts raw"
        " commands, and a quill that writes scrolls. One tool per request."
    ),
    default_say="What is a bramblehoot, and is it friendly? Look it up in the rulebook.",
)
CH2_OPTIONS: Final[Mapping[str, str]] = {
    "http_request": "Look something up in the rulebook",
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
        "The rulebook glows and answers: bramblehoots are gentle, curious, and follow anyone"
        " who carries coffee.",
        "The Scholar's Edge",
        "You walk on with a new friend at your side. It walks on with its nose in your coffee.",
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
        "Lady Luck, keeper of the freshly forged roll_dice tool, spins a d6 between two"
        " fingers. 'Tell me your plan, darling, and I will tell you how hard it is.'"
    ),
    default_say="I leap off the balcony onto the chandelier and swing across the hall!",
)
CH3_RUBRIC: Final[tuple[str, ...]] = ("trivial", "risky", "dangerous", "deadly")
CH3_NEEDS: Final[tuple[int, ...]] = (2, 3, 4, 5)
CH3_Q: Final = ScoreQuestion(
    key="danger",
    instructions="How dangerous is the adventurer's plan?",
    rubric=CH3_RUBRIC,
)
CH3_SUCCESS: Final = Branch(
    "SUCCESS",
    "The d6 lands. It beats the number. Lady Luck applauds, theatrically.",
    "Fortune Favours",
    "You stick the landing. Nobody believes you planned it. You did not.",
    Fate.GLORY,
)
CH3_FAILURE: Final = Branch(
    "FAILURE",
    "The d6 lands short of the number. Lady Luck winces, kindly.",
    "The Graceful Fall",
    "You miss, roll, and come up behind the guards. Was that the plan all along? It is now.",
    Fate.CUNNING,
)


def play_chapter_three(
    deciders: Sequence[Decider], say: str, bar: float, seed: int
) -> ChapterResult:
    """Chapter 3: the score sets the number to beat, and the confidence is a dial, not a gate.

    A sure AI Game Master rolls one d6. An unsure one rolls twice and keeps the lower die:
    the uncertainty is priced into the dice instead of stopping the game.
    """
    verdict = deciders[0].decide(scene(CH3, say), (CH3_Q,))
    answer = verdict.score(CH3_Q.key)
    sure = answer.confidence >= bar
    level = min(answer.level, len(CH3_RUBRIC) - 1)
    needs, roll = CH3_NEEDS[level], roll_d6(seed, keep_lower=not sure)
    branch = CH3_SUCCESS if roll >= needs else CH3_FAILURE
    how = "roll_dice(6)" if sure else "roll_dice(6) twice, keep the lower (unsure AI Game Master)"
    detail = f"danger={CH3_RUBRIC[level]} -> needs {needs}+; {how} = {roll}"
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
    "You step into the faerie wilds. The ogre steps out too. Different problem, prettier scenery.",
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


# --- Chapter 5: The Grand Alliance (the orchestrator picks its specialist agents) -----------

CH5: Final = ChapterInfo(
    number=5,
    title="The Grand Alliance",
    opening=(
        "The dragon lands on the bridge, the bramblehoot at your side. The AI Game Master"
        " orchestrates two specialist agents: a Rules Agent that knows how the game works, and a"
        " Character Agent that knows the party and what it carries."
    ),
    default_say="Can I leap from the bridge onto the dragon's back?",
)
CH5_OPTIONS: Final[Mapping[str, str]] = {
    "rules_agent": "A question about the game's rules: is it allowed, how does it work, does it"
    " need a roll",
    "character_agent": "A question about the party: what they carry, who they are, what they"
    " can do",
    "no_agent": "Plain talk the AI Game Master can answer directly",
}
CH5_Q: Final = ChoiceQuestion(
    key="specialist",
    instructions="Which specialist agent should the AI Game Master call before answering?",
    options=CH5_OPTIONS,
)
CH5_BRANCHES: Final[Mapping[str, Branch]] = {
    "rules_agent": Branch(
        "RULES_AGENT",
        "The AI Game Master calls the Rules Agent, then comes back to you with the ruling: a"
        " leap that far needs a roll.",
        "By the Book",
        "You decide the dragon's back can wait. The dragon looks quietly relieved.",
        Fate.CUNNING,
    ),
    "character_agent": Branch(
        "CHARACTER_AGENT",
        "The AI Game Master calls the Character Agent, then comes back to you: one sword, one"
        " coffee, one very loyal bramblehoot.",
        "The Dragon's Coffee",
        "The dragon wanted company, not a snack. It joins you for coffee every full moon now.",
        Fate.CUNNING,
    ),
    "no_agent": Branch(
        "NO_AGENT",
        "No specialist needed: the AI Game Master answers you on the spot.",
        "Straight Talk",
        "The dragon likes a quick answer. It lets you pass with a roar the whole valley hears.",
        Fate.GLORY,
    ),
}


def play_chapter_five(deciders: Sequence[Decider], say: str, bar: float) -> ChapterResult:
    """Chapter 5: the orchestrator picks which specialist agent to call before answering.

    Sure of the pick: call that one agent, then answer the player. Unsure: go back to the
    player with a question before any specialist is called.
    """
    verdict = deciders[0].decide(scene(CH5, say), (CH5_Q,))
    answer = verdict.choice(CH5_Q.key)
    acted = answer.confidence >= bar
    branch = CH5_BRANCHES[answer.choice] if acted else _hesitate("Which specialist to call")
    return resolve(CH5, say, (verdict,), branch, confidence=answer.confidence, acted=acted)


CH5_SCRIPTS: Final[Mapping[Preset, Mapping[str, ChoiceAnswer]]] = {
    Preset.BOLD: {"specialist": _choice("no_agent", 0.94, tuple(CH5_OPTIONS))},
    Preset.CAUTIOUS: {"specialist": _choice("character_agent", 0.95, tuple(CH5_OPTIONS))},
    Preset.UNSURE: {"specialist": _choice("rules_agent", 0.45, tuple(CH5_OPTIONS))},
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
    1: ChapterSpec(CH1, play_chapter_one, _single(CH1_SCRIPTS)),
    2: ChapterSpec(CH2, lambda d, s, b, _: play_chapter_two(d, s, b), _single(CH2_SCRIPTS)),
    3: ChapterSpec(CH3, play_chapter_three, _single(CH3_SCRIPTS)),
    4: ChapterSpec(CH4, lambda d, s, b, _: play_chapter_four(d, s, b), _single(CH4_SCRIPTS)),
    5: ChapterSpec(CH5, lambda d, s, b, _: play_chapter_five(d, s, b), _single(CH5_SCRIPTS)),
}
