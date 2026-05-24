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


def load_prepare_harness_run():
    sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location(
        "prepare_harness_run", SCRIPT_DIR / "prepare_harness_run.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_exact_webui_without_exact_backend_fails():
    module = load_prepare_harness_run()
    config = module.HarnessConfig(query="test", exact_webui=True)

    with pytest.raises(ValueError, match="exact_webui=true requires"):
        module.finalize_config(config)


def test_allow_ldr_generation_selects_ldr_exact():
    module = load_prepare_harness_run()
    config = module.HarnessConfig(
        query="test",
        exact_webui=True,
        allow_ldr_generation=True,
    )

    module.finalize_config(config)

    assert config.execution_mode == "ldr_exact"
    assert "Exact LDR WebUI/API generation is allowed" in module.build_codex_prompt(
        config
    )


def test_codex_bridge_selects_codex_bridge_exact():
    module = load_prepare_harness_run()
    config = module.HarnessConfig(
        query="test",
        exact_webui=True,
        codex_bridge=True,
    )

    module.finalize_config(config)

    assert config.execution_mode == "codex_bridge_exact"
    assert "Codex bridge exact mode is selected" in module.build_codex_prompt(
        config
    )


def test_default_selects_codex_like_and_forbids_exact_claims():
    module = load_prepare_harness_run()
    config = module.HarnessConfig(query="test")

    module.finalize_config(config)
    prompt = module.build_codex_prompt(config)

    assert config.execution_mode == "codex_like"
    assert "Do not claim exact WebUI parity" in prompt
