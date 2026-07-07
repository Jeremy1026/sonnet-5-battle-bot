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
