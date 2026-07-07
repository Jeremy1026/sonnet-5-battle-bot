import math

import bot


def _state(own_x, own_y, opp_x, opp_y, own_hp=100, opp_hp=100,
           cooldown=0, uses_left=5, tick=0):
    return {
        "own_position": {"x": own_x, "y": own_y},
        "own_hp": own_hp,
        "opponent_position": {"x": opp_x, "y": opp_y},
        "opponent_hp": opp_hp,
        "ranged_cooldown_remaining": cooldown,
        "ranged_uses_remaining": uses_left,
        "tick": tick,
    }


def test_approach_moves_toward_opponent_when_far():
    action, memory = bot.decide(_state(10.0, 50.0, 90.0, 50.0), {})
    assert action["type"] == "move"
    assert action["dx"] > 0
    assert math.isclose(action["dy"], 0.0, abs_tol=1e-9)
    assert math.isclose(math.hypot(action["dx"], action["dy"]), 5.0, rel_tol=1e-6)
    assert memory["phase"] == "approach"


def test_approach_transitions_to_kite_within_buffer():
    # gap = 24 <= APPROACH_BUFFER (25)
    _, memory = bot.decide(_state(66.0, 50.0, 90.0, 50.0), {"phase": "approach"})
    assert memory["phase"] == "kite"


def test_approach_stays_in_approach_outside_buffer():
    # gap = 26 > APPROACH_BUFFER (25)
    _, memory = bot.decide(_state(64.0, 50.0, 90.0, 50.0), {"phase": "approach"})
    assert memory["phase"] == "approach"
