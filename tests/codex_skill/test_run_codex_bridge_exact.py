import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = (
    Path(__file__).resolve().parents[2]
    / "codex-skills"
    / "local-deep-research-codex"
    / "scripts"
)


@pytest.fixture(autouse=True)
def reset_all_singletons():
    yield


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_codex_bridge_exact",
        SCRIPT_DIR / "run_codex_bridge_exact.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_settings_overrides_include_exact_bridge_contract(tmp_path):
    module = load_runner()
    run_dir = tmp_path / "run"
    config = module.RunConfig(
        query="test query",
        run_dir=run_dir,
        model="gpt-5.5",
        search_tool="auto",
        iterations=5,
        questions_per_iteration=4,
        timeout_seconds=1200,
    )

    overrides = module.build_settings_overrides(config)

    assert overrides["llm.provider"] == "codex_bridge"
    assert overrides["llm.model"] == "gpt-5.5"
    assert overrides["llm.codex_bridge.bridge_dir"] == str(run_dir / "codex_bridge")
    assert overrides["llm.codex_bridge.timeout_seconds"] == 1200
    assert overrides["search.tool"] == "auto"
    assert overrides["search.iterations"] == 5
    assert overrides["search.questions_per_iteration"] == 4
    assert overrides["search.questions"] == 4
    assert overrides["api.allow_file_output"] is True


def test_prepare_run_dir_creates_bridge_and_status_files(tmp_path):
    module = load_runner()
    config = module.RunConfig(query="test query", run_dir=tmp_path / "run")

    module.prepare_run_dir(config)

    assert (config.run_dir / "codex_bridge" / "requests").is_dir()
    assert (config.run_dir / "codex_bridge" / "responses").is_dir()
    assert (config.run_dir / "status.json").exists()
    assert (config.run_dir / "run_config.json").exists()


def test_background_child_command_reexecutes_with_execute_flag(tmp_path):
    module = load_runner()
    config = module.RunConfig(query="test query", run_dir=tmp_path / "run")

    command = module.build_child_command(config)

    assert command[0] == sys.executable
    assert "--execute" in command
    assert "--background" not in command
    assert str(config.run_dir) in command
