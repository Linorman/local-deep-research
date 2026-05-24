# LDR Interfaces

Use this reference when deciding how Codex should call or inspect Local Deep Research (LDR).

## Stable Project Surfaces

- MCP server entry point: `ldr-mcp`
- Module entry point: `python -m local_deep_research.mcp`
- Web entry point: `ldr-web`
- Programmatic API module: `local_deep_research.api`
- LLM config entry point: `local_deep_research.config.llm_config.get_llm`
- Custom LLM registry: `local_deep_research.llm.register_llm`

## MCP Tools

Use these when an LDR MCP server is available:

- `list_search_engines`: discover configured engines and API-key requirements.
- `list_strategies`: discover strategy names and descriptions.
- `get_configuration`: inspect current LDR provider, model, search tool, strategy, iterations, and question settings.
- `search`: retrieve raw search results without LLM processing.
- `quick_research`: LDR-backed fast summary; requires LDR to have a working model provider.
- `detailed_research`: LDR-backed detailed analysis; requires LDR to have a working model provider.
- `generate_report`: LDR-backed markdown report; requires LDR to have a working model provider.
- `analyze_documents`: searches a local collection and requires a working LDR model provider for normal successful summarization.

## No-API-Key Preference

Prefer these operations before generation-heavy tools:

1. `list_search_engines`
2. `list_strategies`
3. `get_configuration`
4. `search` with a no-key engine such as `wikipedia` when available
5. Local document retrieval only when a collection is exposed as a search engine via `list_search_engines`

Codex should synthesize the raw results itself.

## Python API

Use the Python API when MCP is unavailable but the project environment can import LDR.

```python
from local_deep_research.api.research_functions import (
    quick_summary,
    detailed_research,
    generate_report,
    analyze_documents,
)
from local_deep_research.api.settings_utils import create_settings_snapshot
```

For no-LLM discovery:

```python
from local_deep_research.api.settings_utils import create_settings_snapshot
from local_deep_research.search_system_factory import get_available_strategies
from local_deep_research.web_search_engines.search_engines_config import search_config

settings = create_settings_snapshot()
engines = search_config(settings_snapshot=settings)
strategies = get_available_strategies(show_all=True)
```

This discovery path should avoid LDR generation calls rather than disabling an LLM provider setting. Raw no-LLM local document retrieval is only available when a collection is exposed as a search engine via `list_search_engines`; `analyze_documents` is LLM-backed.

## Diagnostic Helper

When this skill is stored in an LDR repository, use the bundled diagnostic before making assumptions about available interfaces:

```powershell
python codex-skills/local-deep-research-codex/scripts/check_ldr_access.py --repo . --pretty
```

The script uses only the Python standard library until it probes LDR imports. It reports Python path setup, package import failures, installed entry points, MCP importability, and no-LLM discovery availability. A failed probe does not modify LDR settings and usually means the current shell lacks the project environment or dependencies.

## Relevant Settings

- `LDR_LLM_PROVIDER`: default LLM provider for LDR-backed generation.
- `LDR_LLM_MODEL`: default LDR model name.
- `LDR_SEARCH_TOOL`: default search engine.
- `LDR_SEARCH_SEARCH_STRATEGY`: default strategy for MCP tools.
- `LDR_SEARCH_ITERATIONS`: default iteration count.
- `LDR_SEARCH_QUESTIONS_PER_ITERATION`: default generated questions per iteration.

For raw retrieval and discovery workflows, avoid changing the LDR provider setting; configure an LDR provider only when the user wants LDR itself to perform generation.

## Docker Boundary

LDR web can run in Docker, but `ldr-mcp` uses STDIO and should run on the host where the AI assistant starts it. Do not assume a Dockerized web service exposes MCP over the network.

## Code Pointers

- MCP tools: `src/local_deep_research/mcp/server.py`
- Programmatic research functions: `src/local_deep_research/api/research_functions.py`
- Provider selection: `src/local_deep_research/config/llm_config.py`
- Custom LLM registry: `src/local_deep_research/llm/llm_registry.py`
- MCP guide: `docs/mcp-server.md`
- CLI tools guide: `docs/cli-tools.md`
- Custom LLM guide: `docs/CUSTOM_LLM_INTEGRATION.md`
