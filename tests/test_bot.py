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


def test_kite_fires_when_ranged_ready_and_in_range():
    action, memory = bot.decide(
        _state(70.0, 50.0, 90.0, 50.0, cooldown=0, uses_left=5),
        {"phase": "kite"},
    )
    assert action == {"type": "attack_ranged"}
    assert memory["phase"] == "kite"


def test_kite_retreats_when_opponent_melee_adjacent_in_open_field():
    action, _ = bot.decide(
        _state(88.0, 50.0, 90.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action["type"] == "move"
    assert action["dx"] < 0


def test_kite_holds_position_mid_buffer_on_cooldown():
    # gap = 20, between KITE_MIN (15) and KITE_MAX (25)
    action, _ = bot.decide(
        _state(70.0, 50.0, 90.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action == {"type": "idle"}


def test_kite_retreats_when_closer_than_kite_min_on_cooldown():
    # gap = 10 < KITE_MIN (15)
    action, _ = bot.decide(
        _state(80.0, 50.0, 90.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action["type"] == "move"
    assert action["dx"] < 0


def test_kite_closes_distance_when_beyond_kite_max_on_cooldown():
    # gap = 40 > KITE_MAX (25)
    action, _ = bot.decide(
        _state(50.0, 50.0, 90.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action["type"] == "move"
    assert action["dx"] > 0


def test_kite_retreat_slides_toward_center_when_direct_retreat_is_wall_blocked():
    # Pinned against the left wall (x=2); opponent adjacent to the right.
    # Direct retreat (further left) is fully clamped by the arena boundary.
    action, _ = bot.decide(
        _state(2.0, 50.0, 4.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action["type"] == "move"
    assert action["dx"] > 0  # moves right, toward center (50), not into the wall


def test_kite_retreat_handles_exact_overlap_with_opponent():
    # gap = 0: no defined "away from opponent" direction.
    action, memory = bot.decide(
        _state(5.0, 50.0, 5.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action["type"] == "move"
    assert (action["dx"], action["dy"]) != (0.0, 0.0)
