# Local Deep Research Codex Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a user-level Codex skill that lets Codex orchestrate Local Deep Research retrieval while Codex handles generation, synthesis, and report writing without requiring an LLM API key.

**Architecture:** The implementation creates a concise Codex skill in `C:\Users\Administrator\.codex\skills\local-deep-research-codex`. `SKILL.md` contains the always-loaded workflow, while three reference files hold project-specific LDR interfaces, repeatable research workflows, and the experimental Codex bridge notes. The repo itself only stores this plan; the skill is installed into the local Codex skills directory so Codex can discover it.

**Tech Stack:** Codex skills, Markdown, YAML skill metadata, Local Deep Research MCP/CLI/Python API references, PowerShell, Python validation scripts from `skill-creator`.

---

## File Structure

- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md`
  - Responsibility: trigger metadata and core workflow for Codex-led LDR research.
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\agents\openai.yaml`
  - Responsibility: Codex UI metadata for the installed skill.
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\ldr-interfaces.md`
  - Responsibility: stable LDR commands, APIs, MCP tools, and configuration boundaries.
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\research-workflows.md`
  - Responsibility: repeatable no-API-key research workflows.
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\codex-bridge-experimental.md`
  - Responsibility: explicit non-default bridge design, risks, and compliance limits.

## Task 1: Initialize The Skill Shell

**Files:**
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md`
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\agents\openai.yaml`
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\`

- [ ] **Step 1: Confirm the target directory does not already contain a different skill**

Run:

```powershell
if (Test-Path 'C:\Users\Administrator\.codex\skills\local-deep-research-codex') {
  Get-ChildItem -Force 'C:\Users\Administrator\.codex\skills\local-deep-research-codex'
} else {
  'skill directory is absent'
}
```

Expected: either `skill directory is absent`, or only files from an earlier unfinished `local-deep-research-codex` attempt.

- [ ] **Step 2: Initialize the skill with references support**

Run:

```powershell
python 'C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\init_skill.py' local-deep-research-codex --path 'C:\Users\Administrator\.codex\skills' --resources references --interface display_name='Local Deep Research Codex' --interface short_description='Use Codex to orchestrate Local Deep Research retrieval and synthesize results without an LLM API key.' --interface default_prompt='Use Local Deep Research for retrieval and use Codex for planning, evidence review, synthesis, and final reporting.'
```

Expected: command exits 0 and creates `C:\Users\Administrator\.codex\skills\local-deep-research-codex`.

- [ ] **Step 3: Verify the initialized structure**

Run:

```powershell
Get-ChildItem -Recurse -Force 'C:\Users\Administrator\.codex\skills\local-deep-research-codex' | Select-Object FullName
```

Expected output includes:

```text
C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md
C:\Users\Administrator\.codex\skills\local-deep-research-codex\agents\openai.yaml
C:\Users\Administrator\.codex\skills\local-deep-research-codex\references
```

- [ ] **Step 4: Commit the repo plan state before editing the user-level skill**

Run from `\\192.168.100.113\workspace\projects\local-deep-research`:

```powershell
git -c safe.directory='//192.168.100.113/workspace/projects/local-deep-research' status --short
```

Expected: only this plan file is uncommitted if it has not already been committed.

## Task 2: Write The Core Skill Instructions

**Files:**
- Modify: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md`
- Read: `\\192.168.100.113\workspace\projects\local-deep-research\docs\superpowers\specs\2026-05-17-local-deep-research-codex-skill-design.md`

- [ ] **Step 1: Replace `SKILL.md` with the final content**

Use `apply_patch` or an editor to make `C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md` exactly:

```markdown
---
name: local-deep-research-codex
description: Use when Codex should conduct research with a deployed Local Deep Research installation while avoiding LLM API keys by using LDR for retrieval, discovery, local document search, MCP tools, and source collection, and using Codex itself for decomposition, evidence review, synthesis, and report writing. Trigger for requests to use Codex quota with Local Deep Research, replace LDR generation with Codex-led workflows, run LDR-assisted research without API keys, or explain compliant Codex/LDR integration boundaries.
---

# Local Deep Research With Codex

Use this skill to make Codex the research orchestrator and Local Deep Research (LDR) the retrieval substrate.

## Operating Model

- Use LDR for retrieval, discovery, local document access, strategy metadata, and source collection.
- Use Codex for decomposition, follow-up question design, evidence comparison, source conflict analysis, synthesis, and report writing.
- Prefer no-LLM LDR operations before any LDR operation that calls its configured model provider.
- Do not claim Codex is an OpenAI-compatible model endpoint or a drop-in `BaseChatModel`.
- Keep generated text attribution clear: Codex-generated synthesis is not the same as LDR provider-generated output.

## Start Every Task

1. Identify the user intent: fast fact check, deep research, report, local document analysis, strategy comparison, setup help, or provider replacement question.
2. Check available LDR access in this order:
   - Installed MCP tools or app-provided LDR tools.
   - Local `ldr-mcp`, `python -m local_deep_research.mcp`, or Python API from the project environment.
   - Repository documentation when tools are not runnable.
3. Prefer discovery calls before research calls:
   - `list_search_engines`
   - `list_strategies`
   - `get_configuration`
4. Pick retrieval tools that do not require an LDR LLM provider whenever possible.
5. Run retrieval in small rounds, inspect sources, then decide the next round.

## Tool Selection

- Use LDR `search` for raw search results without LLM processing.
- Use LDR search engines such as `arxiv`, `pubmed`, `wikipedia`, `semantic_scholar`, `github`, or `searxng` based on the user's domain and local configuration.
- Use local document collection workflows only when the user asks about local/private material or a collection is clearly relevant.
- Use `quick_research`, `detailed_research`, `generate_report`, or LDR-side document summarization only after confirming the user accepts that those paths require an LDR model provider.
- If an engine requires a missing API key, switch to a no-key engine when it can satisfy the task; otherwise report the missing setting.

## Research Workflow

1. Restate the research question as a working objective.
2. Break it into 2-6 focused subquestions.
3. Choose search engines and search terms for each subquestion.
4. Retrieve sources with LDR.
5. Track claims, source URLs, dates when relevant, and conflicts.
6. Iterate until the evidence is sufficient or the remaining uncertainty is clear.
7. Produce the final answer with citations, confidence notes, and unresolved gaps.

## When More Detail Is Needed

- Read `references/ldr-interfaces.md` for exact LDR commands, APIs, settings, and MCP boundaries.
- Read `references/research-workflows.md` for task-specific workflows.
- Read `references/codex-bridge-experimental.md` when the user asks for transparent provider replacement or a Codex `BaseChatModel` bridge.

## Compliance Boundaries

- Do not scrape Codex credentials.
- Do not call undocumented Codex inference endpoints.
- Do not build or recommend a fake OpenAI-compatible Codex endpoint.
- Do not send private local documents to external services unless the user explicitly requests that and the selected tool requires it.
- Treat any Codex bridge/provider as experimental and explicit, never as the default workflow.
```

- [ ] **Step 2: Validate frontmatter only**

Run:

```powershell
python 'C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py' 'C:\Users\Administrator\.codex\skills\local-deep-research-codex'
```

Expected:

```text
Skill is valid!
```

## Task 3: Write The LDR Interface Reference

**Files:**
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\ldr-interfaces.md`

- [ ] **Step 1: Write `ldr-interfaces.md`**

Create `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\ldr-interfaces.md` with:

```markdown
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
- `analyze_documents`: searches a local collection and may use LDR's model for summarization.

## No-API-Key Preference

Prefer these operations before generation-heavy tools:

1. `list_search_engines`
2. `list_strategies`
3. `get_configuration`
4. `search` with a no-key engine such as `wikipedia` when available
5. Local document retrieval where configured

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

settings = create_settings_snapshot(overrides={"llm.provider": "none"})
engines = search_config(settings_snapshot=settings)
strategies = get_available_strategies(show_all=True)
```

## Relevant Settings

- `LDR_LLM_PROVIDER`: default LLM provider for LDR-backed generation.
- `LDR_LLM_MODEL`: default LDR model name.
- `LDR_SEARCH_TOOL`: default search engine.
- `LDR_SEARCH_SEARCH_STRATEGY`: default strategy for MCP tools.
- `LDR_SEARCH_ITERATIONS`: default iteration count.
- `LDR_SEARCH_QUESTIONS_PER_ITERATION`: default generated questions per iteration.

Do not set an LLM provider unless the user wants LDR itself to perform generation.

## Docker Boundary

LDR web can run in Docker, but `ldr-mcp` uses STDIO and should run on the host where the AI assistant starts it. Do not assume a Dockerized web service exposes MCP over the network.

## Code Pointers

- MCP tools: `src/local_deep_research/mcp/server.py`
- Programmatic research functions: `src/local_deep_research/api/research_functions.py`
- Provider selection: `src/local_deep_research/config/llm_config.py`
- Custom LLM registry: `src/local_deep_research/llm/llm_registry.py`
- MCP guide: `docs/mcp-server.md`
- Custom LLM guide: `docs/CUSTOM_LLM_INTEGRATION.md`
```

- [ ] **Step 2: Check the reference contains the required public surfaces**

Run:

```powershell
Select-String -Path 'C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\ldr-interfaces.md' -Pattern 'ldr-mcp','list_search_engines','search','create_settings_snapshot','CUSTOM_LLM_INTEGRATION'
```

Expected: one or more matches for each requested pattern.

## Task 4: Write The Research Workflow Reference

**Files:**
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\research-workflows.md`

- [ ] **Step 1: Write `research-workflows.md`**

Create `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\research-workflows.md` with:

```markdown
# Research Workflows

Use these workflows to keep Codex-led LDR research consistent and no-API-key friendly.

## Fast Source Scan

Use for simple factual or background questions.

1. Call `list_search_engines` if engine availability is unknown.
2. Pick one no-key or already-configured engine.
3. Call raw `search` with 5-10 results.
4. Cluster results by source type and claim.
5. Answer with a short synthesis and cite the strongest sources.

## Evidence-Led Deep Research

Use for complex or disputed topics.

1. Turn the user query into 2-6 subquestions.
2. Pick engines by evidence type:
   - `arxiv` or `semantic_scholar` for research papers.
   - `pubmed` for biomedical literature.
   - `wikipedia` for background orientation.
   - `github` for code and repository evidence.
   - `searxng` or another web engine for broad coverage.
3. Run raw `search` for each subquestion.
4. Build an evidence table with claim, source, date, strength, and limitation.
5. Run follow-up searches only for gaps or conflicts.
6. Write the final synthesis with source citations and confidence notes.

## Local Document Analysis

Use when the user asks about uploaded files, private collections, PDFs, or local knowledge bases.

1. Identify the collection name from the user or available LDR configuration.
2. Prefer collection retrieval over web search for private material.
3. If LDR document summarization needs an LDR provider and none is configured, ask LDR only for retrievable document excerpts where possible and let Codex summarize.
4. Cite local document names, pages, metadata, or collection identifiers included in the retrieval result.
5. State when the answer is limited to the provided collection.

## Structured Report

Use when the user wants a research report.

1. Define the report question, scope, and audience.
2. Create an outline before retrieval.
3. Retrieve sources for each section using raw LDR search.
4. Track source coverage per section.
5. Draft the report in Codex.
6. Add a source list and note weakly supported sections.
7. Only call LDR `generate_report` when the user explicitly wants LDR's provider-backed report path.

## Strategy Selection

Use `list_strategies` to inspect LDR strategies when the user asks about LDR internals or wants to compare research approaches.

- Prefer Codex-led raw retrieval for no-API-key operation.
- Use LDR strategy names as planning vocabulary even when Codex performs synthesis.
- Treat LDR's `mcp` or agentic strategy as LDR-provider-backed unless configured otherwise.

## Output Standards

- Include direct source links when available.
- Separate evidence from inference.
- Mark uncertainty where sources conflict or retrieval is sparse.
- Do not hide whether synthesis was generated by Codex.
- Keep intermediate notes when the research spans several retrieval rounds.
```

- [ ] **Step 2: Check workflow coverage**

Run:

```powershell
Select-String -Path 'C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\research-workflows.md' -Pattern 'Fast Source Scan','Evidence-Led Deep Research','Local Document Analysis','Structured Report','Strategy Selection'
```

Expected: one match for each workflow heading.

## Task 5: Write The Experimental Bridge Reference

**Files:**
- Create: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\codex-bridge-experimental.md`

- [ ] **Step 1: Write `codex-bridge-experimental.md`**

Create `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\codex-bridge-experimental.md` with:

```markdown
# Codex Bridge Experimental Reference

Use this reference only when the user asks whether Codex can transparently replace LDR's in-process LLM provider or asks for a Codex `BaseChatModel`.

## Default Answer

The stable integration is Codex-led orchestration: LDR retrieves sources and Codex performs generation. A Codex skill cannot by itself become a network model endpoint or a LangChain `BaseChatModel` inside the LDR process.

## Why A Direct Provider Is Not The Default

- Codex skills guide Codex behavior; they do not expose a stable inference API to arbitrary local processes.
- LDR expects synchronous or async `model.invoke()` and `model.ainvoke()` behavior from LangChain chat models.
- Many LDR strategies issue multiple model calls and sometimes concurrent calls.
- A bridge must handle request identity, timeouts, cancellation, logging, and user visibility.
- A fake OpenAI-compatible endpoint backed by hidden Codex behavior is not a compliant design.

## Acceptable Experimental Shape

An explicit bridge can be considered only as a local automation helper:

1. LDR registers a `codex` provider implementing `BaseChatModel`.
2. The provider writes each prompt to a local queue with a request ID.
3. Codex reads queued requests in the active user session.
4. Codex writes responses to a response file.
5. The provider reads the response, enforces timeout, and returns a LangChain `ChatResult`.

## Minimum Requirements

- The user must explicitly enable the bridge.
- Requests must include request ID, timestamp, prompt hash, and source process metadata.
- Responses must include request ID, timestamp, model attribution, and completion status.
- The bridge must be serial by default.
- Timeouts must return structured LDR errors.
- Logs must not include private document text unless the user accepts local prompt logging.
- The bridge must not call undocumented Codex endpoints.

## Recommended Response To Provider-Replacement Requests

Explain that the compliant path is:

1. Use the `local-deep-research-codex` skill for Codex-led research now.
2. Use LDR's raw search, MCP discovery tools, and document retrieval for source gathering.
3. Treat a `codex` provider as experimental engineering work with explicit user approval.

## Code Pointers If Engineering Work Is Approved

- Provider interface: `src/local_deep_research/llm/providers/base.py`
- Provider auto-discovery: `src/local_deep_research/llm/providers/auto_discovery.py`
- Provider implementations: `src/local_deep_research/llm/providers/implementations/`
- LLM creation path: `src/local_deep_research/config/llm_config.py`
- Custom LLM registry: `src/local_deep_research/llm/llm_registry.py`
```

- [ ] **Step 2: Check compliance language is present**

Run:

```powershell
Select-String -Path 'C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\codex-bridge-experimental.md' -Pattern 'cannot by itself','not a compliant design','explicitly enable','undocumented Codex endpoints'
```

Expected: one match for each requested pattern.

## Task 6: Verify Skill Metadata And UI File

**Files:**
- Modify: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\agents\openai.yaml`
- Test: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md`

- [ ] **Step 1: Inspect `agents/openai.yaml`**

Run:

```powershell
Get-Content -Raw 'C:\Users\Administrator\.codex\skills\local-deep-research-codex\agents\openai.yaml'
```

Expected content has these values or equivalent generated YAML fields:

```yaml
display_name: Local Deep Research Codex
short_description: Use Codex to orchestrate Local Deep Research retrieval and synthesize results without an LLM API key.
default_prompt: Use Local Deep Research for retrieval and use Codex for planning, evidence review, synthesis, and final reporting.
```

- [ ] **Step 2: Regenerate the UI metadata if the values are missing**

Run only if Step 1 does not show the expected values:

```powershell
python 'C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\generate_openai_yaml.py' 'C:\Users\Administrator\.codex\skills\local-deep-research-codex' --interface display_name='Local Deep Research Codex' --interface short_description='Use Codex to orchestrate Local Deep Research retrieval and synthesize results without an LLM API key.' --interface default_prompt='Use Local Deep Research for retrieval and use Codex for planning, evidence review, synthesis, and final reporting.'
```

Expected: command exits 0 and `agents/openai.yaml` contains the values from Step 1.

- [ ] **Step 3: Run full quick validation**

Run:

```powershell
python 'C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py' 'C:\Users\Administrator\.codex\skills\local-deep-research-codex'
```

Expected:

```text
Skill is valid!
```

## Task 7: Run Local Smoke Checks

**Files:**
- Test: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md`
- Test: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\*.md`
- Read: `\\192.168.100.113\workspace\projects\local-deep-research\src\local_deep_research\mcp\server.py`

- [ ] **Step 1: Assert all required skill files exist**

Run:

```powershell
$paths = @(
  'C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md',
  'C:\Users\Administrator\.codex\skills\local-deep-research-codex\agents\openai.yaml',
  'C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\ldr-interfaces.md',
  'C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\research-workflows.md',
  'C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\codex-bridge-experimental.md'
)
$missing = $paths | Where-Object { -not (Test-Path $_) }
if ($missing) { $missing; exit 1 }
'all required skill files exist'
```

Expected:

```text
all required skill files exist
```

- [ ] **Step 2: Assert the skill has no forbidden bridge instructions**

Run:

```powershell
Select-String -Path 'C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md','C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\*.md' -Pattern 'scrape Codex credentials','undocumented Codex inference','fake OpenAI-compatible Codex endpoint'
```

Expected: matches appear only in negative compliance instructions.

- [ ] **Step 3: Verify no-LLM LDR discovery imports from the project checkout**

Run from `\\192.168.100.113\workspace\projects\local-deep-research`:

```powershell
@'
from local_deep_research.api.settings_utils import create_settings_snapshot
from local_deep_research.search_system_factory import get_available_strategies
from local_deep_research.web_search_engines.search_engines_config import search_config

settings = create_settings_snapshot(overrides={"llm.provider": "none"})
engines = search_config(settings_snapshot=settings)
strategies = get_available_strategies(show_all=True)
print(f"engines={len(engines)}")
print(f"strategies={len(strategies)}")
assert len(engines) > 0
assert len(strategies) > 0
'@ | python -
```

Expected output has positive counts:

```text
engines=<positive integer>
strategies=<positive integer>
```

- [ ] **Step 4: Verify MCP entry point can be imported if MCP extras are installed**

Run from `\\192.168.100.113\workspace\projects\local-deep-research`:

```powershell
@'
try:
    from local_deep_research.mcp.server import list_search_engines, list_strategies
except ModuleNotFoundError as exc:
    print(f"mcp_import_unavailable={exc.name}")
else:
    print(f"list_search_engines={callable(list_search_engines)}")
    print(f"list_strategies={callable(list_strategies)}")
'@ | python -
```

Expected when MCP extras are installed:

```text
list_search_engines=True
list_strategies=True
```

Expected when MCP extras are not installed:

```text
mcp_import_unavailable=mcp
```

This second output is acceptable because the skill reference includes a non-MCP fallback.

## Task 8: Final Review And Commit Plan Tracking

**Files:**
- Review: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md`
- Review: `C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\*.md`
- Review: `\\192.168.100.113\workspace\projects\local-deep-research\docs\superpowers\plans\2026-05-17-local-deep-research-codex-skill.md`

- [ ] **Step 1: Scan the installed skill for wording that violates the design**

Run:

```powershell
Select-String -Path 'C:\Users\Administrator\.codex\skills\local-deep-research-codex\SKILL.md','C:\Users\Administrator\.codex\skills\local-deep-research-codex\references\*.md' -Pattern 'drop-in','OpenAI-compatible model endpoint','undocumented Codex endpoints','LLM API key'
```

Expected:

- `drop-in` appears only in wording that says Codex is not a drop-in model.
- `OpenAI-compatible model endpoint` appears only in wording that says Codex is not one.
- `undocumented Codex endpoints` appears only in wording that forbids them.
- `LLM API key` appears in no-API-key workflow descriptions.

- [ ] **Step 2: Check repo status**

Run from `\\192.168.100.113\workspace\projects\local-deep-research`:

```powershell
git -c safe.directory='//192.168.100.113/workspace/projects/local-deep-research' status --short
```

Expected: this plan file is the only repo change if it has not yet been committed.

- [ ] **Step 3: Commit the plan file if uncommitted**

Run from `\\192.168.100.113\workspace\projects\local-deep-research`:

```powershell
git -c safe.directory='//192.168.100.113/workspace/projects/local-deep-research' add -- docs/superpowers/plans/2026-05-17-local-deep-research-codex-skill.md
git -c safe.directory='//192.168.100.113/workspace/projects/local-deep-research' commit -m "docs: add codex skill implementation plan"
```

Expected: commit succeeds with this plan file.

## Self-Review

Spec coverage:

- No-API-key workflow is covered by Tasks 2, 3, 4, and 7.
- Codex-led generation and LDR retrieval split is covered by Tasks 2 and 4.
- LDR interface references are covered by Task 3.
- Experimental bridge boundaries are covered by Task 5.
- Compliance boundaries are covered by Tasks 2, 5, and 8.
- Validation and smoke checks are covered by Tasks 6 and 7.

Completeness scan:

- This plan contains concrete file paths, content blocks, validation commands, and expected outputs.
- No undefined function names or unspecified file edits are required.

Type and naming consistency:

- Skill name is consistently `local-deep-research-codex`.
- Skill path is consistently `C:\Users\Administrator\.codex\skills\local-deep-research-codex`.
- Reference filenames match the approved design.
