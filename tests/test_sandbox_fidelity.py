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
