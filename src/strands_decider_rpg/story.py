"""The Once Upon Agentic AI story graph, as frozen data.

Each chapter of the original Strands Agents workshop (a Game Master for a table-top role-playing
game) is replayed here with one decision point handed to the Strands Decider. The decider reads
the game state and answers a yes/no question; the engine routes on how *sure* it is, not only on
what it picked. Chapter 1 -- "The Art of Agent Summoning" -- is the first replay.
"""

from __future__ import annotations

from dataclasses import dataclass

from strands_decider_rpg.decider import YesNoQuestion


@dataclass(frozen=True, slots=True)
class Ending:
    """A terminal outcome of a chapter."""

    key: str
    title: str
    prose: str


@dataclass(frozen=True, slots=True)
class Branch:
    """One outcome of a chapter's decision point, with the ending it leads to."""

    label: str
    narration: str
    ending: Ending


@dataclass(frozen=True, slots=True)
class Chapter:
    """A replayed workshop chapter with a single decider-gated decision.

    Attributes:
        number: Chapter number in the adventure.
        title: Chapter title.
        opening: The scene narrated before the decision.
        state: The game state the decider reads.
        question: The yes/no question put to the decider.
        bold: Branch taken on a confident yes.
        cautious: Branch taken on a confident no.
        hesitate: Branch taken when confidence is below the bar -- the table decides.
    """

    number: int
    title: str
    opening: str
    state: str
    question: YesNoQuestion
    bold: Branch
    cautious: Branch
    hesitate: Branch


CHAPTER_ONE: Chapter = Chapter(
    number=1,
    title="The Art of Agent Summoning",
    opening=(
        "The tavern door is shut against the rain. Inside, a quest waits. You -- freshly summoned,"
        " your system prompt still warm -- step up to the threshold and declare your intent to the"
        " Game Master."
    ),
    state=(
        "The adventurer says: 'I kick the door open and stride in, blade drawn,"
        " ready for anything!'"
    ),
    question=YesNoQuestion(
        key="is_bold",
        instructions=(
            "Is the adventurer charging in boldly, rather than scouting the room carefully first?"
        ),
    ),
    bold=Branch(
        label="BOLD",
        narration=(
            "The Game Master grins. The door bangs off the wall, every head turns, and the quest"
            " comes to you -- loudly."
        ),
        ending=Ending(
            key="blaze_of_glory",
            title="A Blaze of Glory",
            prose=(
                "You never did learn subtlety. The bards will sing of the night you walked in like"
                " thunder. Short song. Great chorus."
            ),
        ),
    ),
    cautious=Branch(
        label="CAUTIOUS",
        narration=(
            "The Game Master nods slowly. You read the room before the room reads you, and slip in"
            " along the wall where the shadows are kind."
        ),
        ending=Ending(
            key="the_long_game",
            title="The Long Game",
            prose=(
                "Patience is a weapon too. You leave the tavern knowing three secrets nobody meant"
                " to tell you, and the night is still young."
            ),
        ),
    ),
    hesitate=Branch(
        label="HESITATE",
        narration=(
            "The Game Master pauses. The read is a coin-toss -- bold or careful, it is genuinely"
            " unclear -- so rather than guess, control goes back to the table."
        ),
        ending=Ending(
            key="the_table_decides",
            title="The Table Decides",
            prose=(
                "A good Game Master knows when not to improvise. The dice are offered to you, the"
                " player, because a confident wrong turn is worse than an honest question."
            ),
        ),
    ),
)
