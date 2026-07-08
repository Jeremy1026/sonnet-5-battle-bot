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
AIM_THRESHOLD = 0.95


def decide(state, memory):
    own_x = state["own_position"]["x"]
    own_y = state["own_position"]["y"]
    opp_x = state["opponent_position"]["x"]
    opp_y = state["opponent_position"]["y"]
    own_hp = state["own_hp"]
    opp_hp = state["opponent_hp"]
    cooldown = state["ranged_cooldown_remaining"]
    uses_left = state["ranged_uses_remaining"]
    facing_dx = state["own_facing"]["dx"]
    facing_dy = state["own_facing"]["dy"]

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

    action = _aim_gate(action, facing_dx, facing_dy, dx, dy)

    return action, {"phase": phase}


def _aligned(facing_dx, facing_dy, target_dx, target_dy):
    facing_length = math.hypot(facing_dx, facing_dy)
    target_length = math.hypot(target_dx, target_dy)
    if facing_length == 0 or target_length == 0:
        return True
    aim_dot = (facing_dx * target_dx + facing_dy * target_dy) / (facing_length * target_length)
    return aim_dot >= AIM_THRESHOLD


def _aim_gate(action, facing_dx, facing_dy, dx, dy):
    # attack_melee/attack_ranged need facing toward the opponent; defend
    # needs facing away from the opponent (the attacker). Movement/idle
    # don't depend on facing and pass through unchanged.
    action_type = action["type"]
    if action_type in ("attack_melee", "attack_ranged"):
        if not _aligned(facing_dx, facing_dy, dx, dy):
            return {"type": "rotate", "dx": dx, "dy": dy}
    elif action_type == "defend":
        if not _aligned(facing_dx, facing_dy, -dx, -dy):
            return {"type": "rotate", "dx": -dx, "dy": -dy}
    return action


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
    # opponent, giving no defined retreat direction). Walking straight
    # toward the arena center doesn't help here: an opponent chasing our
    # current position at matching speed closes the same straight-line gap
    # we're opening, so we stay pinned at the collision radius forever.
    # Stepping perpendicular to the opponent instead breaks that symmetry
    # -- the opponent's chase vector aims at where we *were*, not where
    # we're going, so a same-speed perpendicular step increases the gap
    # (Pythagorean: sqrt((gap - speed)^2 + speed^2) > gap for gap < 2 *
    # speed). Pick whichever perpendicular direction lands further from
    # the nearest wall, to actually escape the corner over time.
    if ax == 0.0 and ay == 0.0:
        ax, ay = 1.0, 0.0
    perp_options = ((-ay, ax), (ay, -ax))
    best = max(
        perp_options,
        key=lambda p: _distance_to_nearest_wall(
            _clamp(own_x + p[0] * MOVE_SPEED), _clamp(own_y + p[1] * MOVE_SPEED)
        ),
    )
    px, py = best
    return {"type": "move", "dx": px * MOVE_SPEED, "dy": py * MOVE_SPEED}


def _distance_to_nearest_wall(x, y):
    return min(x - ARENA_MIN, ARENA_MAX - x, y - ARENA_MIN, ARENA_MAX - y)


def _kite_action(own_x, own_y, opp_x, opp_y, dx, dy, gap, cooldown, uses_left):
    # Fire whenever ready, even at melee range: firing is a guaranteed 15
    # dmg dealt, whereas retreating from an adjacent opponent only avoids
    # damage if the retreat actually increases distance -- against a wall
    # (or an opponent matching your speed), it can't, which previously
    # deadlocked Peregrine into retreating forever while eating free melee
    # hits. Attacking first dominates that case and is never worse in the
    # open field either (15 dealt for at most 10 taken is a good trade).
    if cooldown == 0 and uses_left > 0:
        return {"type": "attack_ranged"}
    if gap <= MELEE_RANGE:
        return _move_away(own_x, own_y, opp_x, opp_y, dx, dy)
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
