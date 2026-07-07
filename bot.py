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
        action = {"type": "idle"}
    else:
        action = {"type": "idle"}

    return action, {"phase": phase}


def _normalize(dx, dy):
    mag = math.hypot(dx, dy)
    if mag == 0:
        return 0.0, 0.0
    return dx / mag, dy / mag


def _move_toward(dx, dy):
    ux, uy = _normalize(dx, dy)
    return {"type": "move", "dx": ux * MOVE_SPEED, "dy": uy * MOVE_SPEED}
