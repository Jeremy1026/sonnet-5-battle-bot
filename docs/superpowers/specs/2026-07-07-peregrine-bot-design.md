# Peregrine — Bot Battle Platform bot design

## Context

This repo is a submission repo for the Bot Battle Platform (`llm-battle` at
`/Users/jcurcio/Development/llm-battle`), a 1v1 arena battle game where
bots are submitted as a `bot.py` + `bot.yaml` pair via a public HTTPS git
repo and run sandboxed inside the platform.

### Game mechanics (from platform source)

- Arena: 100×100, both bots start at 100 HP, ~80 units apart.
- Tick loop, up to 500 ticks: `decide()` runs for both bots → forfeit check
  → both moves apply → combat resolves against **post-move** positions →
  HP/cooldowns update → KO check.
- Actions (exactly one per tick): `move(dx, dy)` (magnitude clamped to 5),
  `attack_melee` (range 3, 10 dmg), `attack_ranged` (range 30, 15 dmg,
  10-tick cooldown, 5 uses total for the whole match), `defend` (halves
  damage taken that tick), `idle`.
- **Key mechanic**: since movement resolves before combat, and melee is a
  standing action (not combined with movement), a bot that retreats on the
  same tick an adjacent opponent commits to melee can dodge that attack
  for free.
- A bot that raises an exception or returns a malformed action 5 ticks in
  a row auto-forfeits.
- Sandbox: `decide(state: dict, memory: dict) -> (action: dict, memory:
  dict)`, subprocess-isolated, 0.1s timeout per tick, 64MB memory cap,
  only `math`/`itertools`/`functools`/`heapq`/`bisect` importable, no
  `eval`/`exec`/`open`/`getattr`/etc.

## Goal

Build a competitive bot ("Peregrine") that beats naive rushers (melee-only,
close-and-swing) and naive kiters (fire-then-flee, no phase awareness) by
combining risk-free ranged poking, opportunistic melee dodging, and a
deliberate finishing phase once ranged ammo is spent.

## Strategy: three-phase state machine

Phase is tracked in `memory["phase"]` and re-evaluated every tick from
current `state`.

### 1. `approach`

Active while `gap > RANGED_RANGE (30)`. Move straight at the opponent.
Stop closing at a buffer distance (~25) rather than the full 30, so a
single opponent retreat step doesn't put them back out of range before we
get a shot off.

### 2. `kite`

Default phase once in ranged range with `ranged_uses_remaining > 0`. Each
tick, in priority order:

1. If `gap <= MELEE_RANGE (3)`: retreat directly away from the opponent's
   position. This is the free-dodge window — if the opponent commits to
   melee this tick, our post-move position (hopefully) exceeds their
   range and we take no damage.
2. Else if ranged is off cooldown and has uses remaining: fire
   (`attack_ranged`).
3. Else (cooldown active, not melee-adjacent): hold a comfortable buffer
   distance (~15–25). Drift back if the opponent is closing faster than
   our comfort zone allows; hold position (`idle`) otherwise, to burn
   their approach time until the next shot is ready.

### 3. `finish`

Triggers once `ranged_uses_remaining == 0` (transition is one-way — once
ammo is spent it can't come back). By this point we may have landed 0–5
free ranged hits (0–75 dmg, or less if the opponent defended).

- If own HP is low (≤25) and the opponent is HP-favored (their HP > ours):
  `defend` rather than attack, mitigating damage while looking for an
  opening.
- Otherwise: close to melee range and commit to melee trades
  (`attack_melee` when in range, `move` toward the opponent otherwise).

## Wall handling

Retreat and hold vectors are computed relative to the opponent, then
blended toward the arena center (50, 50) when the bot is near an edge
(within ~15 units of any boundary). This prevents the bot from being
cornered and losing its ability to maintain kiting distance.

## Memory schema

```json
{"phase": "approach" | "kite" | "finish"}
```

Deliberately minimal — `state` already carries positions, HP, and cooldown
info every tick, so `memory` only needs to persist which phase we're in
(specifically, that we've committed to `finish` once ranged ammo is
spent — that decision must survive across ticks even though
`ranged_uses_remaining == 0` is itself derivable from `state`, so in
practice `memory["phase"]` is a cache/assertion of that fact rather than
new information. It's kept for readability and as a hook for future phase
logic that isn't purely a function of `state`).

## Testing approach (not part of the submitted repo)

A throwaway local script (not committed, or committed under `scripts/` but
excluded from what gets zipped/pointed at by `bot.yaml`/`bot.py`) that:

- Imports `battle_engine.run_match` directly from the platform repo
  (added to `sys.path` or run with `PYTHONPATH`).
- Wraps Peregrine's dict-based `decide()` into a `Decider` (`BotState ->
  Action`) using the same conversion helpers as
  `sandbox_runner/protocol.py`.
- Runs Peregrine against the platform's existing `tests/fixtures/
  rusher_bot.py` and `tests/fixtures/kiter_bot.py`, printing win/loss and
  final HP, so strategy tuning can be iterated on quickly without going
  through the sandboxed subprocess path.
- Optionally, a slower fidelity check runs the actual sandboxed
  `SandboxedDecider` against the same fixtures to confirm the bot also
  behaves correctly under the real timeout/sandbox constraints.

## Out of scope

- No opponent-modeling beyond the current tick's `state` (no tracking
  opponent velocity/history across ticks) — the phase state machine reacts
  to instantaneous state, not learned opponent behavior.
- No GitHub repo creation, push, or `/bots` submission — the user will
  handle publishing and submitting this repo themselves.
