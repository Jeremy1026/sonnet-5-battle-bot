from battle_engine import run_match, Position

from sandbox_runner.protocol import bot_state_to_dict, dict_to_action

import bot as peregrine
import rusher_bot
import kiter_bot


def _wrap(module):
    memory = {}

    def decider(state):
        nonlocal memory
        action_dict, memory = module.decide(bot_state_to_dict(state), memory)
        return dict_to_action(action_dict)

    return decider


def test_peregrine_beats_rusher_as_side_a():
    result = run_match(
        _wrap(peregrine), _wrap(rusher_bot),
        start_a=Position(10.0, 50.0), start_b=Position(90.0, 50.0),
    )
    assert result.winner == "a"


def test_peregrine_beats_rusher_as_side_b():
    result = run_match(
        _wrap(rusher_bot), _wrap(peregrine),
        start_a=Position(10.0, 50.0), start_b=Position(90.0, 50.0),
    )
    assert result.winner == "b"


def test_peregrine_beats_kiter_as_side_a():
    result = run_match(
        _wrap(peregrine), _wrap(kiter_bot),
        start_a=Position(10.0, 50.0), start_b=Position(90.0, 50.0),
    )
    assert result.winner == "a"


def test_peregrine_beats_kiter_as_side_b():
    result = run_match(
        _wrap(kiter_bot), _wrap(peregrine),
        start_a=Position(10.0, 50.0), start_b=Position(90.0, 50.0),
    )
    assert result.winner == "b"
