import math

ARENA_MIN = 0.0
ARENA_MAX = 100.0
ARENA_CENTER = 50.0
MOVE_SPEED = 5.0
MELEE_RANGE = 3.0
RANGED_RANGE = 30.0
APPROACH_BUFFER = 25.0
KITE_MIN = 15.0
KITE_MAX = 25.0
LOW_HP_THRESHOLD = 25


def decide(state, memory):
    own_x = state["own_position"]["x"]
    own_y = state["own_position"]["y"]
    opp_x = state["opponent_position"]["x"]
    opp_y = state["opponent_position"]["y"]
    own_hp = state["own_hp"]
    opp_hp = state["opponent_hp"]
    cooldown = state["ranged_cooldown_remaining"]
    uses_left = state["ranged_uses_remaining"]

    dx = opp_x - own_x
    dy = opp_y - own_y
    gap = math.hypot(dx, dy)

    phase = memory.get("phase", "approach")
    if uses_left == 0:
        phase = "finish"
    elif phase == "approach" and gap <= APPROACH_BUFFER:
        phase = "kite"

    if phase == "approach":
        action = _move_toward(dx, dy)
    elif phase == "kite":
        action = _kite_action(own_x, own_y, opp_x, opp_y, dx, dy, gap, cooldown, uses_left)
    else:
        action = _finish_action(dx, dy, gap, own_hp, opp_hp)

    return action, {"phase": phase}


def _normalize(dx, dy):
    mag = math.hypot(dx, dy)
    if mag == 0:
        return 0.0, 0.0
    return dx / mag, dy / mag


def _move_toward(dx, dy):
    ux, uy = _normalize(dx, dy)
    return {"type": "move", "dx": ux * MOVE_SPEED, "dy": uy * MOVE_SPEED}


def _clamp(value):
    return min(max(value, ARENA_MIN), ARENA_MAX)


def _move_away(own_x, own_y, opp_x, opp_y, dx, dy):
    ax, ay = _normalize(-dx, -dy)
    predicted_x = _clamp(own_x + ax * MOVE_SPEED)
    predicted_y = _clamp(own_y + ay * MOVE_SPEED)
    current_gap = math.hypot(opp_x - own_x, opp_y - own_y)
    predicted_gap = math.hypot(opp_x - predicted_x, opp_y - predicted_y)

    if predicted_gap - current_gap >= MOVE_SPEED * 0.5:
        return {"type": "move", "dx": predicted_x - own_x, "dy": predicted_y - own_y}

    # Direct retreat is wall-blocked (or we're exactly on top of the
    # opponent, giving no defined retreat direction) -- walking toward the
    # arena center always increases distance from every wall and is a
    # deterministic, non-oscillating escape from a corner.
    cx, cy = _normalize(ARENA_CENTER - own_x, ARENA_CENTER - own_y)
    if cx == 0.0 and cy == 0.0:
        cx, cy = 1.0, 0.0
    return {"type": "move", "dx": cx * MOVE_SPEED, "dy": cy * MOVE_SPEED}


def _kite_action(own_x, own_y, opp_x, opp_y, dx, dy, gap, cooldown, uses_left):
    if gap <= MELEE_RANGE:
        return _move_away(own_x, own_y, opp_x, opp_y, dx, dy)
    if cooldown == 0 and uses_left > 0:
        return {"type": "attack_ranged"}
    if gap < KITE_MIN:
        return _move_away(own_x, own_y, opp_x, opp_y, dx, dy)
    if gap > KITE_MAX:
        return _move_toward(dx, dy)
    return {"type": "idle"}


def _finish_action(dx, dy, gap, own_hp, opp_hp):
    if own_hp <= LOW_HP_THRESHOLD and opp_hp > own_hp:
        return {"type": "defend"}
    if gap <= MELEE_RANGE:
        return {"type": "attack_melee"}
    return _move_toward(dx, dy)
