"""Tests for the shared decider contract."""

from __future__ import annotations

import httpx
import pytest

from strands_decider_rpg.decider import (
    Decision,
    HttpDecider,
    ScriptedDecider,
    YesNoQuestion,
)

_Q = YesNoQuestion(key="is_bold", instructions="Is the adventurer bold?")


@pytest.mark.parametrize(
    ("value", "expected_yes", "expected_confidence"),
    [
        (0.90, True, 0.90),
        (0.05, False, 0.95),
        (0.50, True, 0.50),
    ],
)
def test_decision_properties(value: float, expected_yes: bool, expected_confidence: float) -> None:
    decision = Decision(key="k", value=value)
    assert decision.yes is expected_yes
    assert decision.confidence == pytest.approx(expected_confidence)


def test_decision_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        Decision(key="k", value=1.5)


def test_scripted_decider_returns_in_order() -> None:
    decider = ScriptedDecider(scores={"is_bold": 0.8})
    (decision,) = decider.decide("state", (_Q,))
    assert decision.key == "is_bold"
    assert decision.value == pytest.approx(0.8)


def test_http_decider_parses_raw_server_shape() -> None:
    # Raw boundary shape: the exact /v1/systemone JSON the live server returns for a noul.
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/systemone"
        return httpx.Response(200, json={"answers": {"is_bold": {"type": "noul", "noul": 0.858}}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    decider = HttpDecider(client=client)
    (decision,) = decider.decide("state", (_Q,))
    client.close()

    assert decision.key == "is_bold"
    assert decision.value == pytest.approx(0.858)
    assert decision.yes is True
