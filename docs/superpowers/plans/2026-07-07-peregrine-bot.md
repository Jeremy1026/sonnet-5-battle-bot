# Peregrine Battle Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify `bot.py` + `bot.yaml` for the Bot Battle Platform: a three-phase (approach/kite/finish) state-machine bot named "Peregrine" that ranged-kites while ammo remains, then commits to melee.

**Architecture:** A single pure-function module (`bot.py`) exposing `decide(state: dict, memory: dict) -> (action: dict, memory: dict)`, following the platform's sandboxed bot contract. Phase is tracked in `memory["phase"]` and re-derived from `state` every tick. Unit tests exercise `decide()` directly with hand-built state dicts; integration tests run full matches via the platform's `battle_engine.run_match` against its `tests/fixtures/rusher_bot.py` and `tests/fixtures/kiter_bot.py`; a final test runs the real sandboxed subprocess path for fidelity.

**Tech Stack:** Python 3.14 (matches the platform's venv), `math` only (sandbox allowlist), `pytest` (via the platform's venv at `/Users/jcurcio/Development/llm-battle/venv/bin/pytest`, since this repo has no venv of its own).

## Global Constraints

- `bot.py` must define a top-level `decide(state, memory)` function taking exactly two positional parameters (checked by the platform's `web/bot_signature.py::check_decide_signature`).
- `bot.py` source must pass `sandbox_runner/validate.py::validate_bot_source`: only `math`, `itertools`, `functools`, `heapq`, `bisect` may be imported; no `eval`/`exec`/`open`/`compile`/`getattr`/`setattr`/`delattr`/`vars`/`dir`/`globals`/`locals`/`input`/`breakpoint`; no wildcard imports; no dunder attribute access; no `.format`/`.format_map` calls.
- `bot.yaml` must have non-empty string `name` and `llm` fields (checked by `web/bot_yaml.py::parse_bot_yaml`). Use `name: Peregrine`, `llm: claude-sonnet-5`.
- Per-tick action dicts must match `sandbox_runner/protocol.py::dict_to_action`'s expected shapes: `{"type": "move", "dx": <float>, "dy": <float>}`, `{"type": "attack_melee"}`, `{"type": "attack_ranged"}`, `{"type": "defend"}`, `{"type": "idle"}`.
- Game constants (from `battle_engine/types.py`, do not redefine differently): `ARENA_WIDTH=100.0`, `ARENA_HEIGHT=100.0`, `STARTING_HP=100`, `MAX_MOVE_DISTANCE=5.0`, `MELEE_RANGE=3.0`, `MELEE_DAMAGE=10`, `RANGED_RANGE=30.0`, `RANGED_DAMAGE=15`, `RANGED_COOLDOWN_TICKS=10`, `RANGED_MAX_USES=5`, `DEFEND_DAMAGE_MULTIPLIER=0.5`, `MAX_TICKS=500`.
- The platform repo lives at `/Users/jcurcio/Development/llm-battle` — its venv (`/Users/jcurcio/Development/llm-battle/venv/bin/python` / `pytest`) is used to run this repo's tests, since `battle_engine`, `sandbox_runner`, and the fixture bots it imports for integration tests live there.
- This repo (`/Users/jcurcio/Development/llm-battle-bot`) is already a git repo (`git init` was run during brainstorming) with one commit containing the design spec at `docs/superpowers/specs/2026-07-07-peregrine-bot-design.md`.

---

## File Structure

- `bot.py` — the submission: `decide()` plus private phase-logic helpers. This is the only game-logic file; kept small and flat since the platform only ever reads this one file.
- `bot.yaml` — submission metadata (`name`, `llm`).
- `.gitignore` — excludes `__pycache__/`, `*.pyc`.
- `tests/conftest.py` — puts this repo's root and the platform repo's root (plus its `tests/fixtures` dir) on `sys.path` so `import bot`, `import battle_engine`, `import rusher_bot` etc. all resolve regardless of invocation directory.
- `tests/test_bot.py` — unit tests calling `bot.decide()` directly with hand-built state dicts, covering all three phases and the corner/retreat edge case.
- `tests/test_platform_contract.py` — smoke test that runs the platform's own validators (`validate_bot_source`, `check_decide_signature`, `parse_bot_yaml`) against this repo's actual `bot.py`/`bot.yaml` files, so a regression that would make the platform reject the submission is caught locally.
- `tests/test_integration.py` — full-match tests via `battle_engine.run_match`, Peregrine vs. the platform's `rusher_bot` and `kiter_bot` fixtures.
- `tests/test_sandbox_fidelity.py` — one full match run through the platform's real `sandbox_runner.runner.SandboxedDecider` (subprocess-isolated), confirming `bot.py` behaves correctly under the actual sandbox constraints, not just in-process.

---

### Task 1: Repo scaffolding and platform-contract smoke test

**Files:**
- Create: `/Users/jcurcio/Development/llm-battle-bot/.gitignore`
- Create: `/Users/jcurcio/Development/llm-battle-bot/bot.yaml`
- Create: `/Users/jcurcio/Development/llm-battle-bot/bot.py` (minimal idle-only stub for this task)
- Create: `/Users/jcurcio/Development/llm-battle-bot/tests/conftest.py`
- Test: `/Users/jcurcio/Development/llm-battle-bot/tests/test_platform_contract.py`

**Interfaces:**
- Produces: `bot.decide(state: dict, memory: dict) -> tuple[dict, dict]` (stub returns `({"type": "idle"}, memory)` in this task; Tasks 2–4 replace the body).
- Produces: `tests/conftest.py` sets `sys.path` for every other test file in this plan — no test file needs its own `sys.path` manipulation.

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: Create `bot.yaml`**

```yaml
name: Peregrine
llm: claude-sonnet-5
```

- [ ] **Step 3: Create the minimal `bot.py` stub**

```python
def decide(state, memory):
    return {"type": "idle"}, memory
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM_ROOT = "/Users/jcurcio/Development/llm-battle"
FIXTURES_DIR = os.path.join(PLATFORM_ROOT, "tests", "fixtures")

for path in (REPO_ROOT, PLATFORM_ROOT, FIXTURES_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)
```

- [ ] **Step 5: Write the failing platform-contract test**

```python
from pathlib import Path

from sandbox_runner.validate import validate_bot_source
from web.bot_signature import check_decide_signature
from web.bot_yaml import parse_bot_yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_bot_py_passes_sandbox_static_validation():
    source = (REPO_ROOT / "bot.py").read_text()
    validate_bot_source(source)  # raises BotValidationError on failure


def test_bot_py_has_correct_decide_signature():
    source = (REPO_ROOT / "bot.py").read_text()
    check_decide_signature(source)  # raises BotSignatureError on failure


def test_bot_yaml_has_required_fields():
    source = (REPO_ROOT / "bot.yaml").read_text()
    data = parse_bot_yaml(source)
    assert data == {"name": "Peregrine", "llm": "claude-sonnet-5"}
```

This test can't "fail then pass" in the usual TDD sense since Steps 1-3 already created valid files — it's a contract guard, not new behavior. Skip the red step here; just confirm it's green.

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_platform_contract.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
cd /Users/jcurcio/Development/llm-battle-bot
git add .gitignore bot.yaml bot.py tests/conftest.py tests/test_platform_contract.py
git commit -m "Scaffold bot repo with idle stub and platform-contract smoke test"
```

---

### Task 2: Approach phase and shared movement primitives

**Files:**
- Modify: `bot.py`
- Test: `tests/test_bot.py` (new file)

**Interfaces:**
- Consumes: nothing beyond the `bot.py` stub from Task 1.
- Produces: `_normalize(dx, dy) -> (float, float)` — unit vector, `(0.0, 0.0)` if input magnitude is 0.
- Produces: `_move_toward(dx, dy) -> dict` — a `move` action dict scaled to `MOVE_SPEED` in the direction of `(dx, dy)`.
- Produces: module-level constants `ARENA_MIN=0.0`, `ARENA_MAX=100.0`, `ARENA_CENTER=50.0`, `MOVE_SPEED=5.0`, `MELEE_RANGE=3.0`, `RANGED_RANGE=30.0`, `APPROACH_BUFFER=25.0`, `KITE_MIN=15.0`, `KITE_MAX=25.0`, `LOW_HP_THRESHOLD=25`.
- Produces: `decide()` now computes `dx, dy, gap` from `state`, tracks `phase` in `memory["phase"]` (default `"approach"`), and transitions `"approach" -> "kite"` once `gap <= APPROACH_BUFFER`. The `"kite"` and `"finish"` branches are stubbed to return `{"type": "idle"}` in this task — Tasks 3 and 4 fill them in.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_bot.py -v`
Expected: FAIL — the stub always returns `{"type": "idle"}` and never sets `memory["phase"]`, so all three assertions on `action["type"]`/`memory["phase"]` fail.

- [ ] **Step 3: Replace `bot.py` with the approach-phase implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_bot.py -v`
Expected: 3 passed

- [ ] **Step 5: Run the full suite to confirm no regression**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/ -v`
Expected: all passing (platform-contract tests from Task 1 plus the 3 new ones)

- [ ] **Step 6: Commit**

```bash
cd /Users/jcurcio/Development/llm-battle-bot
git add bot.py tests/test_bot.py
git commit -m "Implement approach phase and shared movement primitives"
```

---

### Task 3: Kite phase — ranged fire, corner-safe retreat, buffer holding

**Files:**
- Modify: `bot.py`
- Modify: `tests/test_bot.py`

**Interfaces:**
- Consumes: `_normalize`, `_move_toward`, `decide()`'s phase-tracking from Task 2.
- Produces: `_clamp(value) -> float` — clamps to `[ARENA_MIN, ARENA_MAX]`.
- Produces: `_move_away(own_x, own_y, opp_x, opp_y, dx, dy) -> dict` — a `move` action dict that retreats from the opponent, falling back to a deterministic move toward `(ARENA_CENTER, ARENA_CENTER)` when direct retreat is wall-blocked (predicted gap gain `< MOVE_SPEED * 0.5`) or the opponent is exactly on top of us (zero-magnitude retreat vector).
- Produces: `_kite_action(own_x, own_y, opp_x, opp_y, dx, dy, gap, cooldown, uses_left) -> dict` — melee-adjacent retreat takes priority over firing; then fire if off cooldown with uses left; then hold the `[KITE_MIN, KITE_MAX]` buffer (retreat if closer, close if farther, `idle` inside the band).
- Produces: `decide()`'s `"kite"` branch now calls `_kite_action(...)` instead of returning a stub.

**Design note on `_move_away`'s wall-blocked check:** it must compare the actual gap-to-opponent before vs. after the move (`predicted_gap - current_gap`), not just how far the bot displaces. An earlier prototype measured raw displacement magnitude and let the bot slide step-by-step into a literal corner (a wall-clamped move can still "move" 3+ units on the unblocked axis alone, so the naive check never triggered the escape fallback) where it ended up exactly overlapping the opponent, returning a zero-vector "move" every tick while taking free melee hits. Comparing actual gap change avoids this.

- [ ] **Step 1: Write the failing tests (append to `tests/test_bot.py`)**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_bot.py -v`
Expected: FAIL on all 7 new tests — the `"kite"` branch still returns `{"type": "idle"}` unconditionally.

- [ ] **Step 3: Implement the kite phase in `bot.py`**

Add these functions and update `decide()`'s kite branch:

```python
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
```

In `decide()`, replace:

```python
    elif phase == "kite":
        action = {"type": "idle"}
```

with:

```python
    elif phase == "kite":
        action = _kite_action(own_x, own_y, opp_x, opp_y, dx, dy, gap, cooldown, uses_left)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_bot.py -v`
Expected: 10 passed (3 from Task 2 + 7 new)

- [ ] **Step 5: Commit**

```bash
cd /Users/jcurcio/Development/llm-battle-bot
git add bot.py tests/test_bot.py
git commit -m "Implement kite phase with corner-safe retreat"
```

---

### Task 4: Finish phase — melee commitment and low-HP defend

**Files:**
- Modify: `bot.py`
- Modify: `tests/test_bot.py`

**Interfaces:**
- Consumes: `_move_toward` from Task 2.
- Produces: `_finish_action(dx, dy, gap, own_hp, opp_hp) -> dict` — `defend` when `own_hp <= LOW_HP_THRESHOLD and opp_hp > own_hp`; else `attack_melee` when `gap <= MELEE_RANGE`; else close the distance.
- Produces: `decide()`'s `"finish"` branch now calls `_finish_action(...)` instead of returning a stub. The `uses_left == 0 -> phase = "finish"` transition already exists from Task 2 and needs no changes.

- [ ] **Step 1: Write the failing tests (append to `tests/test_bot.py`)**

```python
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
        _state(88.0, 50.0, 90.0, 50.0, own_hp=15, opp_hp=60, uses_left=0),
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_bot.py -v`
Expected: FAIL on the 5 new tests — the `"finish"` branch still returns `{"type": "idle"}` unconditionally (the phase-transition test passes already, since that logic landed in Task 2).

- [ ] **Step 3: Implement the finish phase in `bot.py`**

Add:

```python
def _finish_action(dx, dy, gap, own_hp, opp_hp):
    if own_hp <= LOW_HP_THRESHOLD and opp_hp > own_hp:
        return {"type": "defend"}
    if gap <= MELEE_RANGE:
        return {"type": "attack_melee"}
    return _move_toward(dx, dy)
```

In `decide()`, replace:

```python
    else:
        action = {"type": "idle"}
```

with:

```python
    else:
        action = _finish_action(dx, dy, gap, own_hp, opp_hp)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_bot.py -v`
Expected: 15 passed

- [ ] **Step 5: Run the full suite and the platform-contract test to confirm no regression**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/ -v`
Expected: all passing (18 tests: 3 contract + 15 unit)

- [ ] **Step 6: Commit**

```bash
cd /Users/jcurcio/Development/llm-battle-bot
git add bot.py tests/test_bot.py
git commit -m "Implement finish phase with melee commitment and low-HP defend"
```

---

### Task 5: Integration tests against the platform's fixture bots

**Files:**
- Test: `tests/test_integration.py` (new file)

**Interfaces:**
- Consumes: `bot.decide` (complete three-phase implementation from Tasks 2–4); `battle_engine.run_match`, `battle_engine.Position` (platform repo, already on `sys.path` via `tests/conftest.py`); `sandbox_runner.protocol.bot_state_to_dict`, `sandbox_runner.protocol.dict_to_action` (platform repo); `rusher_bot`, `kiter_bot` modules (platform repo's `tests/fixtures/`, already on `sys.path` via `tests/conftest.py`), each exposing the same `decide(state: dict, memory: dict) -> (dict, dict)` shape as `bot.py`.
- Produces: nothing consumed by later tasks — this is a terminal verification task.

This has already been prototyped and verified outside this repo: Peregrine beats `rusher_bot` 70–0 (55 ticks) and beats `kiter_bot` 25–0 (66 ticks), in both starting-side assignments. These are regression thresholds, not aspirational targets — the implementation from Tasks 2–4 is the exact logic that produced them.

- [ ] **Step 1: Write the integration tests**

```python
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
```

- [ ] **Step 2: Run the tests**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_integration.py -v`
Expected: 4 passed

If any test fails (e.g. after a future tuning change to `bot.py`'s constants), do not weaken the assertion — inspect the failure by printing the tick trace:

```python
result = run_match(_wrap(peregrine), _wrap(rusher_bot),
                    start_a=Position(10.0, 50.0), start_b=Position(90.0, 50.0))
for t in result.ticks:
    print(t.tick, t.position_a, t.hp_a, t.action_a, "|", t.position_b, t.hp_b, t.action_b)
```

and adjust `KITE_MIN`/`KITE_MAX`/`APPROACH_BUFFER`/`LOW_HP_THRESHOLD` in `bot.py` accordingly, then rerun.

- [ ] **Step 3: Commit**

```bash
cd /Users/jcurcio/Development/llm-battle-bot
git add tests/test_integration.py
git commit -m "Add integration tests: Peregrine vs platform fixture bots"
```

---

### Task 6: Sandbox fidelity check

**Files:**
- Test: `tests/test_sandbox_fidelity.py` (new file)

**Interfaces:**
- Consumes: `sandbox_runner.runner.SandboxedDecider` (platform repo), `battle_engine.run_match`, `battle_engine.Position`. Points `SandboxedDecider` directly at this repo's `bot.py` file path and the platform's `tests/fixtures/rusher_bot.py` file path — no wrapping needed, since `SandboxedDecider` already speaks the on-disk `decide(state, memory) -> (action, memory)` file contract.
- Produces: nothing — terminal verification task confirming `bot.py` runs correctly under the real subprocess sandbox (0.1s per-tick timeout, restricted builtins, AST-validated source) rather than only in-process.

This test is slower than the others (up to 500 ticks × 2 subprocess spawns per tick in the worst case) — expect it to take up to ~30s.

- [ ] **Step 1: Write the sandbox fidelity test**

```python
import os

from battle_engine import run_match, Position
from sandbox_runner.runner import SandboxedDecider

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM_ROOT = "/Users/jcurcio/Development/llm-battle"


def test_peregrine_runs_end_to_end_in_the_real_sandbox():
    peregrine_path = os.path.join(REPO_ROOT, "bot.py")
    rusher_path = os.path.join(PLATFORM_ROOT, "tests", "fixtures", "rusher_bot.py")

    result = run_match(
        SandboxedDecider(peregrine_path),
        SandboxedDecider(rusher_path),
        start_a=Position(10.0, 50.0), start_b=Position(90.0, 50.0),
    )

    assert result.winner == "a"
    assert len(result.ticks) > 0
```

- [ ] **Step 2: Run the test**

Run: `cd /Users/jcurcio/Development/llm-battle-bot && /Users/jcurcio/Development/llm-battle/venv/bin/pytest tests/test_sandbox_fidelity.py -v -s`
Expected: 1 passed (may take up to ~30s)

If it fails with a timeout or sandbox rejection (as opposed to a game-logic loss), that indicates `bot.py` is too slow or uses something outside the sandbox allowlist — re-run `tests/test_platform_contract.py` first to rule out a static-validation regression, then check for accidentally-introduced slow operations (there should be none; the implementation is O(1) arithmetic per tick).

- [ ] **Step 3: Commit**

```bash
cd /Users/jcurcio/Development/llm-battle-bot
git add tests/test_sandbox_fidelity.py
git commit -m "Add end-to-end sandbox fidelity test"
```

---

## After This Plan

All game logic and verification is complete and committed. Remaining steps are the user's to do manually (out of scope per the design spec):

1. Create a GitHub repo and push this repo's contents (at minimum `bot.py` and `bot.yaml` must be at the repo root).
2. Log into the platform via GitHub OAuth.
3. `POST /bots` with `repo_url` and `branch` (or use the platform's web UI submission form, which wraps the same endpoint).
4. Create matches via `POST /matches` with `bot_a_id`/`bot_b_id`, or through the UI.
