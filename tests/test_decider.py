"""Tests for the decider contract, against the raw /v1/systemone wire shape."""

from __future__ import annotations

import json

import httpx
import pytest

from strands_decider_rpg.decider import (
    ChoiceQuestion,
    HttpDecider,
    NoulAnswer,
    ScoreQuestion,
    YesNoQuestion,
)

# The exact response shape strands-decider 0.1.0 serves (schema.py + latency_ms in server.py).
_RAW = {
    "model": "strands-decider-2B-qwen3.5-v1-2610",
    "answers": {
        "bold": {"type": "noul", "noul": 0.858},
        "tool": {
            "type": "choice",
            "choice": "shell",
            "probabilities": {"shell": 0.9, "http_request": 0.1},
            "confidence": 0.8,
        },
        "danger": {
            "type": "score",
            "score": 1.03,
            "legend": {"0": "low", "1": "high"},
            "probabilities": {"0": 0.2, "1": 0.8},
            "confidence": 0.5,
        },
    },
    "usage": {"input_tokens": 86, "output_tokens": 3},
    "latency_ms": 489.01,
}

_QS = (
    YesNoQuestion(key="bold", instructions="Bold?"),
    ChoiceQuestion(key="tool", instructions="Tool?", options={"shell": "a", "http_request": "b"}),
    ScoreQuestion(key="danger", instructions="Danger?", rubric=("low", "high")),
)


def test_http_decider_round_trips_all_three_types() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=_RAW)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        verdict = HttpDecider(client=client).decide("state", _QS)

    assert seen["questions"] == {
        "bold": {"type": "noul", "instructions": "Bold?"},
        "tool": {
            "type": "choice",
            "instructions": "Tool?",
            "criteria": {"shell": "a", "http_request": "b"},
        },
        "danger": {"type": "score", "instructions": "Danger?", "criteria": ["low", "high"]},
    }
    assert verdict.latency_ms == pytest.approx(489.01)
    assert verdict.noul("bold").yes is True
    assert verdict.choice("tool").choice == "shell"
    assert verdict.score("danger").level == 1


def test_wrong_answer_type_is_a_typed_error() -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_RAW))) as c:
        verdict = HttpDecider(client=c).decide("state", _QS)
    with pytest.raises(TypeError):
        verdict.choice("bold")


@pytest.mark.parametrize(
    ("p", "yes", "conf"), [(0.95, True, 0.9), (0.05, False, 0.9), (0.5, True, 0.0)]
)
def test_noul_confidence(p: float, yes: bool, conf: float) -> None:
    answer = NoulAnswer(noul=p)
    assert answer.yes is yes
    assert answer.confidence == pytest.approx(conf)


def test_noul_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        NoulAnswer(noul=1.5)
