import math

import bot


def _state(own_x, own_y, opp_x, opp_y, own_hp=100, opp_hp=100,
           cooldown=0, uses_left=5, tick=0, own_facing=None, opponent_facing=None):
    # Default facing: aimed straight at the opponent, so existing
    # non-facing-focused tests exercise phase logic without being blocked
    # by the aim-gate.
    if own_facing is None:
        own_facing = _unit(opp_x - own_x, opp_y - own_y)
    if opponent_facing is None:
        opponent_facing = _unit(own_x - opp_x, own_y - opp_y)
    return {
        "own_position": {"x": own_x, "y": own_y},
        "own_hp": own_hp,
        "opponent_position": {"x": opp_x, "y": opp_y},
        "opponent_hp": opp_hp,
        "own_facing": {"dx": own_facing[0], "dy": own_facing[1]},
        "opponent_facing": {"dx": opponent_facing[0], "dy": opponent_facing[1]},
        "ranged_cooldown_remaining": cooldown,
        "ranged_uses_remaining": uses_left,
        "tick": tick,
    }


def _unit(dx, dy):
    mag = math.hypot(dx, dy)
    if mag == 0:
        return (1.0, 0.0)
    return (dx / mag, dy / mag)


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


def test_kite_retreat_steps_perpendicular_when_direct_retreat_is_wall_blocked():
    # Pinned against the left wall (x=2); opponent adjacent to the right,
    # directly along the x-axis. Direct retreat (further left) is fully
    # clamped by the arena boundary, so the bot should step perpendicular
    # (along y) toward whichever side has more room, rather than trying
    # to push into the wall.
    action, _ = bot.decide(
        _state(2.0, 50.0, 4.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action["type"] == "move"
    assert math.isclose(action["dx"], 0.0, abs_tol=1e-9)
    assert abs(action["dy"]) > 0


def test_kite_retreat_handles_exact_overlap_with_opponent():
    # gap = 0: no defined "away from opponent" direction.
    action, memory = bot.decide(
        _state(5.0, 50.0, 5.0, 50.0, cooldown=5, uses_left=3),
        {"phase": "kite"},
    )
    assert action["type"] == "move"
    assert (action["dx"], action["dy"]) != (0.0, 0.0)


def test_finish_phase_triggers_when_ammo_exhausted():
    _, memory = bot.decide(
        _state(70.0, 50.0, 90.0, 50.0, uses_left=0),
        {"phase": "kite"},
    )
    assert memory["phase"] == "finish"


def test_finish_attacks_melee_in_range():
    action, _ = bot.decide(
        _state(88.0, 50.0, 90.0, 50.0, own_hp=80, opp_hp=40, uses_left=0),
        {"phase": "finish"},
    )
    assert action == {"type": "attack_melee"}


def test_finish_closes_distance_out_of_melee_range():
    action, _ = bot.decide(
        _state(70.0, 50.0, 90.0, 50.0, own_hp=80, opp_hp=40, uses_left=0),
        {"phase": "finish"},
    )
    assert action["type"] == "move"
    assert action["dx"] > 0


def test_finish_defends_when_low_hp_and_behind():
    action, _ = bot.decide(
        _state(88.0, 50.0, 90.0, 50.0, own_hp=15, opp_hp=60, uses_left=0,
               own_facing=(-1.0, 0.0)),
        {"phase": "finish"},
    )
    assert action == {"type": "defend"}


def test_finish_still_attacks_when_low_hp_but_ahead():
    # own_hp is low, but opponent HP is lower still -- press the advantage.
    action, _ = bot.decide(
        _state(88.0, 50.0, 90.0, 50.0, own_hp=15, opp_hp=10, uses_left=0),
        {"phase": "finish"},
    )
    assert action == {"type": "attack_melee"}


def test_kite_rotates_instead_of_firing_when_facing_away_from_opponent():
    # In ranged range and off cooldown, but facing straight up instead of
    # at the opponent (who is to the east) -- should rotate, not fire.
    action, _ = bot.decide(
        _state(70.0, 50.0, 90.0, 50.0, cooldown=0, uses_left=3,
               own_facing=(0.0, 1.0)),
        {"phase": "kite"},
    )
    assert action == {"type": "rotate", "dx": 20.0, "dy": 0.0}


def test_finish_rotates_instead_of_melee_when_facing_away_from_opponent():
    action, _ = bot.decide(
        _state(88.0, 50.0, 90.0, 50.0, own_hp=80, opp_hp=40, uses_left=0,
               own_facing=(0.0, -1.0)),
        {"phase": "finish"},
    )
    assert action == {"type": "rotate", "dx": 2.0, "dy": 0.0}


def test_finish_rotates_to_face_away_before_defending_when_facing_opponent():
    # Low HP and behind, but currently facing the opponent -- defend
    # requires facing away, so rotate away first instead of defending.
    action, _ = bot.decide(
        _state(88.0, 50.0, 90.0, 50.0, own_hp=15, opp_hp=60, uses_left=0,
               own_facing=(1.0, 0.0)),
        {"phase": "finish"},
    )
    assert action == {"type": "rotate", "dx": -2.0, "dy": 0.0}


