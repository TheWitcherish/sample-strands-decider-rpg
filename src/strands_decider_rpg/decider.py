"""Typed client for the Strands Decider 2B decision model.

Strands Decider is a small, fast "system one" model: it does not generate text, it reads a
state plus typed questions and returns an answer with a calibrated confidence
(https://strandsagents.com/blog/introducing-strands-decider/, fetched 2026-10-09).

This module exposes the one decision shape the experiments need so far -- a yes/no (``noul``)
question -- behind a ``Decider`` Protocol, so a story engine depends on the contract and never
imports a concrete backend. Two backends ship: ``HttpDecider`` talks to a local
``strands-decider serve`` instance; ``ScriptedDecider`` is deterministic for tests and the
offline demo.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_DECIDER_MODEL: Final[str] = "strands-decider-2B-qwen3.5-v1-2610"
DEFAULT_DECIDER_URL: Final[str] = "http://localhost:8000"

DECIDER_MODEL: Final[str] = os.environ.get("DECIDER_MODEL", DEFAULT_DECIDER_MODEL)
DECIDER_URL: Final[str] = os.environ.get("DECIDER_URL", DEFAULT_DECIDER_URL)


class YesNoQuestion(BaseModel):
    """A yes/no (``noul``) question put to the decider.

    Frozen Pydantic model: the question is data at the boundary, never mutated after it is built.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    instructions: str


class Decision(BaseModel):
    """The decider's verdict on one yes/no question.

    Attributes:
        key: The question key this verdict answers.
        value: The raw ``noul`` score in ``[0, 1]``; closer to 1 leans yes.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    value: float = Field(ge=0.0, le=1.0)

    @property
    def yes(self) -> bool:
        """True when the score leans yes (at or above the 0.5 midpoint)."""
        return self.value >= 0.5

    @property
    def confidence(self) -> float:
        """Reliability of the verdict in ``[0.5, 1.0]``.

        The model returns only the ``noul`` score for a yes/no question, so confidence is derived
        as the probability it assigns to the side it picked: ``max(value, 1 - value)``. A score of
        0.5 is a coin flip (0.5); a score of 0.0 or 1.0 is full confidence (1.0). This matches the
        model card's guidance that answers at confidence 0.9 or more are right about 95% of the
        time.
        """
        return max(self.value, 1.0 - self.value)


class Decider(Protocol):
    """Read-only contract: given a state and yes/no questions, return one decision each.

    Borrow-checker discipline: ``questions`` is a read-only ``Sequence`` the decider never
    mutates, and it returns a fresh tuple in the same order.
    """

    def decide(self, state: str, questions: Sequence[YesNoQuestion]) -> tuple[Decision, ...]: ...


class _NoulAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    noul: float


class _SystemOneResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    answers: Mapping[str, _NoulAnswer]


@dataclass(frozen=True, slots=True)
class HttpDecider:
    """Talks to a local ``strands-decider serve`` instance over its ``/v1/systemone`` endpoint.

    Start the server first (installs the ``decider`` extra, then serves the model locally):

        uv sync --extra decider
        uv run strands-decider serve "$DECIDER_MODEL" --port 8000

    Attributes:
        base_url: Server base URL. Defaults to the ``DECIDER_URL`` env var or localhost:8000.
        model: Model id, surfaced for logging. Defaults to the ``DECIDER_MODEL`` env var.
        timeout_s: Per-request timeout in seconds.
        client: Optional caller-owned client (used in tests). When omitted, a client is created
            and closed per call -- its lifetime is the ``decide`` scope.
    """

    base_url: str = DECIDER_URL
    model: str = DECIDER_MODEL
    timeout_s: float = 30.0
    client: httpx.Client | None = None

    def decide(self, state: str, questions: Sequence[YesNoQuestion]) -> tuple[Decision, ...]:
        """Ask the live model every question in one pass and return the decisions in order.

        Raises:
            httpx.HTTPError: If the server is unreachable or returns a non-2xx status.
            pydantic.ValidationError: If the response is not the expected ``/v1/systemone`` shape.
        """
        questions_payload: dict[str, dict[str, str]] = {
            q.key: {"type": "noul", "instructions": q.instructions} for q in questions
        }
        body = {"state": state, "questions": questions_payload}

        # Lifetimes are scopes: a client we create, we close; an injected client stays the
        # caller's to own and close (single owner).
        client = self.client if self.client is not None else httpx.Client(timeout=self.timeout_s)
        try:
            response = client.post(f"{self.base_url}/v1/systemone", json=body)
            response.raise_for_status()
            payload = response.json()
        finally:
            if self.client is None:
                client.close()

        parsed = _SystemOneResponse.model_validate(payload)
        return tuple(Decision(key=q.key, value=parsed.answers[q.key].noul) for q in questions)


@dataclass(frozen=True, slots=True)
class ScriptedDecider:
    """Deterministic decider for tests and the offline demo.

    Maps each question key to a fixed ``noul`` score, so a run reproduces with no model, no GPU
    and no network -- the 30-second-kickoff path.

    Attributes:
        scores: Read-only mapping of question key to a fixed score in ``[0, 1]``.
    """

    scores: Mapping[str, float]

    def decide(self, state: str, questions: Sequence[YesNoQuestion]) -> tuple[Decision, ...]:
        """Return a decision per question from the scripted scores, in order."""
        return tuple(Decision(key=q.key, value=self.scores[q.key]) for q in questions)
