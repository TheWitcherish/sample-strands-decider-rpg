"""Typed client for the Strands Decider decision models.

Strands Decider is a small, fast "system one" model: it does not generate text, it reads a state
plus typed questions and returns an answer with a calibrated confidence
(https://github.com/strands-labs/strands-decider, README fetched 2026-10-10). It answers three
question types over one state, all in a single forward pass:

- ``noul``: yes/no, returns P(yes).
- ``choice``: one of N named options, returns the pick, the probabilities and a confidence.
- ``score``: an ordered rubric, returns an expected level, the probabilities and a confidence.

The wire shapes below mirror ``strands_decider/schema.py`` in the pinned ``strands-decider==0.1.0``.
A story engine depends on the ``Decider`` Protocol and never imports a concrete backend.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Final, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

DEFAULT_DECIDER_MODEL: Final[str] = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"
DEFAULT_DECIDER_URL: Final[str] = "http://localhost:8000"

DECIDER_MODEL: Final[str] = os.environ.get("DECIDER_MODEL", DEFAULT_DECIDER_MODEL)
DECIDER_URL: Final[str] = os.environ.get("DECIDER_URL", DEFAULT_DECIDER_URL)

_FROZEN: Final[ConfigDict] = ConfigDict(frozen=True, extra="ignore")


# --- Questions -------------------------------------------------------------------------------


class YesNoQuestion(BaseModel):
    """A yes/no (``noul``) question.

    ``criteria`` optionally describes what counts as yes (``"true"``) and no (``"false"``); the
    decider README calls this sharpening the boundary, and it measurably lifts confidence.
    """

    model_config = _FROZEN

    key: str
    instructions: str
    criteria: Mapping[str, str] | None = None


class ChoiceQuestion(BaseModel):
    """Pick one of N named options. ``options`` maps option name to its description."""

    model_config = _FROZEN

    key: str
    instructions: str
    options: Mapping[str, str]


class ScoreQuestion(BaseModel):
    """Rate against an ordered rubric. ``rubric`` is ascending: index 0 is the low end."""

    model_config = _FROZEN

    key: str
    instructions: str
    rubric: tuple[str, ...]


Question = YesNoQuestion | ChoiceQuestion | ScoreQuestion


def _wire_question(question: Question) -> dict[str, object]:
    match question:
        case YesNoQuestion(criteria=None):
            return {"type": "noul", "instructions": question.instructions}
        case YesNoQuestion():
            return {
                "type": "noul",
                "instructions": question.instructions,
                "criteria": dict(question.criteria or {}),
            }
        case ChoiceQuestion():
            return {
                "type": "choice",
                "instructions": question.instructions,
                "criteria": dict(question.options),
            }
        case ScoreQuestion():
            return {
                "type": "score",
                "instructions": question.instructions,
                "criteria": list(question.rubric),
            }


# --- Answers ---------------------------------------------------------------------------------


class NoulAnswer(BaseModel):
    """The model's P(yes) for a yes/no question."""

    model_config = _FROZEN

    type: Literal["noul"] = "noul"
    noul: float = Field(ge=0.0, le=1.0)

    @property
    def yes(self) -> bool:
        """True when the answer leans yes."""
        return self.noul >= 0.5

    @property
    def confidence(self) -> float:
        """How decided the model is, in ``[0, 1]``: ``|2p - 1|``.

        The server returns no confidence for a yes/no question because P(yes) already carries
        it. ``|2p - 1|`` is the library's own normalised max-probability for two options, so a
        noul confidence reads on the same scale as a choice confidence: 0 is a coin flip, 1 is
        certain.
        """
        return abs(2.0 * self.noul - 1.0)

    @property
    def summary(self) -> str:
        """Short human-readable form of the answer."""
        return f"{'yes' if self.yes else 'no'} (p_yes={self.noul:.3f})"


class ChoiceAnswer(BaseModel):
    """The option the model picked, with its probabilities and calibrated confidence."""

    model_config = _FROZEN

    type: Literal["choice"] = "choice"
    choice: str
    probabilities: Mapping[str, float]
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def summary(self) -> str:
        """Short human-readable form of the answer."""
        return self.choice


class ScoreAnswer(BaseModel):
    """The expected rubric level, with its probabilities and calibrated confidence."""

    model_config = _FROZEN

    type: Literal["score"] = "score"
    score: float = Field(ge=0.0)
    probabilities: Mapping[str, float]
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def level(self) -> int:
        """The rubric index closest to the expected score."""
        return round(self.score)

    @property
    def summary(self) -> str:
        """Short human-readable form of the answer."""
        return f"score={self.score:.2f}"


Answer = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]


class Verdict(BaseModel):
    """Everything one round trip to the decider returned.

    Attributes:
        model: Model name the server reports.
        latency_ms: Server-side time for the whole request, all questions included.
        answers: Answer per question key.
    """

    model_config = _FROZEN

    model: str
    latency_ms: float = 0.0
    answers: Mapping[str, Answer]

    def noul(self, key: str) -> NoulAnswer:
        """Return the yes/no answer for ``key``.

        Raises:
            KeyError: If ``key`` is missing. TypeError: If its answer is not a yes/no.
        """
        answer = self.answers[key]
        if not isinstance(answer, NoulAnswer):
            raise TypeError(f"{key} is a {answer.type} answer, not noul")
        return answer

    def choice(self, key: str) -> ChoiceAnswer:
        """Return the choice answer for ``key``.

        Raises:
            KeyError: If ``key`` is missing. TypeError: If its answer is not a choice.
        """
        answer = self.answers[key]
        if not isinstance(answer, ChoiceAnswer):
            raise TypeError(f"{key} is a {answer.type} answer, not choice")
        return answer

    def score(self, key: str) -> ScoreAnswer:
        """Return the score answer for ``key``.

        Raises:
            KeyError: If ``key`` is missing. TypeError: If its answer is not a score.
        """
        answer = self.answers[key]
        if not isinstance(answer, ScoreAnswer):
            raise TypeError(f"{key} is a {answer.type} answer, not score")
        return answer


_VERDICT: Final[TypeAdapter[Verdict]] = TypeAdapter(Verdict)


# --- Backends --------------------------------------------------------------------------------


class Decider(Protocol):
    """Read-only contract: given a state and questions, answer them all in one round trip.

    Borrow-checker discipline: ``questions`` is a read-only ``Sequence`` the decider never
    mutates; the returned ``Verdict`` is a fresh frozen value.
    """

    def decide(self, state: str, questions: Sequence[Question]) -> Verdict: ...


@dataclass(frozen=True, slots=True)
class HttpDecider:
    """Talks to a ``strands-decider serve`` instance over ``POST /v1/systemone``.

    Attributes:
        base_url: Server base URL. Defaults to the ``DECIDER_URL`` env var or localhost:8000.
        timeout_s: Per-request timeout in seconds.
        client: Optional caller-owned client (used in tests). When omitted, a client is created
            and closed per call -- its lifetime is the ``decide`` scope.
    """

    base_url: str = DECIDER_URL
    timeout_s: float = 60.0
    client: httpx.Client | None = None

    def decide(self, state: str, questions: Sequence[Question]) -> Verdict:
        """Ask every question in one request and return the typed verdict.

        Raises:
            httpx.HTTPError: If the server is unreachable or returns a non-2xx status.
            pydantic.ValidationError: If the response is not the expected shape.
        """
        body = {"state": state, "questions": {q.key: _wire_question(q) for q in questions}}
        # Lifetimes are scopes: a client we create, we close; an injected one stays the caller's.
        client = self.client if self.client is not None else httpx.Client(timeout=self.timeout_s)
        try:
            response = client.post(f"{self.base_url}/v1/systemone", json=body)
            response.raise_for_status()
            payload: object = response.json()
        finally:
            if self.client is None:
                client.close()
        return _VERDICT.validate_python(payload)


@dataclass(frozen=True, slots=True)
class ScriptedDecider:
    """Deterministic decider for tests and the offline demo: no model, no GPU, no network.

    Attributes:
        answers: Read-only mapping of question key to the answer to return.
    """

    answers: Mapping[str, NoulAnswer | ChoiceAnswer | ScoreAnswer]

    def decide(self, state: str, questions: Sequence[Question]) -> Verdict:
        """Return the scripted answer for each question asked.

        Raises:
            KeyError: If a question has no scripted answer.
        """
        return Verdict(model="scripted", answers={q.key: self.answers[q.key] for q in questions})
