# Local Deep Research Codex Skill Design

Date: 2026-05-17
Status: Approved for planning

## Context

Local Deep Research (LDR) already has the main primitives needed for a Codex-led workflow:

- A LangChain custom LLM registry in `src/local_deep_research/llm/llm_registry.py`.
- Provider selection in `src/local_deep_research/config/llm_config.py`.
- Programmatic research entry points in `src/local_deep_research/api/research_functions.py`.
- An MCP server in `src/local_deep_research/mcp/server.py`.
- MCP documentation in `docs/mcp-server.md`.
- Custom LLM integration documentation in `docs/CUSTOM_LLM_INTEGRATION.md`.

The core constraint is that Codex skills influence how Codex works. A skill does not turn Codex into an OpenAI-compatible model endpoint, and Codex does not expose a stable local inference API that LDR can call as a drop-in `BaseChatModel`. The compliant first design should therefore make Codex the research orchestrator and use LDR as the research substrate.

## Goals

- Let a deployed LDR installation be used without a paid LLM API key when Codex is available.
- Use Codex quota and Codex capabilities for planning, query generation, evidence review, synthesis, and report writing.
- Preserve LDR's value: search engines, MCP tools, local document search, research strategies, source collection, and configuration discovery.
- Keep the workflow compliant by avoiding hidden or unsupported Codex API assumptions.
- Leave room for a later experimental Codex bridge/provider without making it part of the first milestone.

## Non-Goals

- Do not pretend that a Codex skill can transparently replace every in-process LDR `model.invoke()` call.
- Do not build an OpenAI-compatible facade backed by an unsupported Codex interface.
- Do not require API keys for the first milestone.
- Do not modify LDR core code for the first milestone unless implementation planning later finds a small, necessary helper.

## Recommended Approach

Build a `local-deep-research-codex` Codex skill. The skill makes Codex the controller of the research workflow and instructs Codex to use LDR tools for retrieval and structured research support.

The first implementation should be a skill-only integration:

1. Install or reference the skill from `$CODEX_HOME/skills/local-deep-research-codex`.
2. Prefer LDR MCP tools when available.
3. Fall back to local CLI or Python programmatic entry points when MCP is not configured.
4. Prefer no-LLM LDR operations first, especially raw search and discovery tools.
5. Use Codex for all generation-heavy steps: decomposition, follow-up question design, evidence comparison, conflict resolution, final synthesis, and report writing.

This approach is stable because it uses public surfaces: Codex skills, local files, shell commands, MCP tools, and the documented LDR API.

## Skill Responsibilities

The skill should instruct Codex to:

- Detect the user's research task type: quick fact check, deep research, report, local document analysis, benchmark/strategy comparison, or troubleshooting.
- Discover available LDR capabilities before running a research flow:
  - `list_search_engines`
  - `list_strategies`
  - `get_configuration`
- Prefer raw retrieval before synthesis:
  - Use `search` for source discovery because it avoids LLM calls.
  - Use local document collection search when the user asks about private or uploaded material.
- Design the research plan itself:
  - Break the user question into subquestions.
  - Select search engines and strategies based on domain.
  - Track sources, claims, contradictions, and confidence.
- Use Codex to synthesize:
  - Summarize findings.
  - Compare evidence.
  - Generate the final answer or report.
  - Cite sources gathered through LDR.
- Only call LDR's LLM-backed tools when the user explicitly accepts that those tools still need a configured LDR LLM provider:
  - `quick_research`
  - `detailed_research`
  - `generate_report`
  - `analyze_documents` when configured to summarize through LDR's provider.

## Skill Package Shape

The skill should be concise and use references for project-specific detail.

```text
local-deep-research-codex/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── ldr-interfaces.md
    ├── research-workflows.md
    └── codex-bridge-experimental.md
```

`SKILL.md` should contain the trigger description and the core operating workflow. It should stay short enough to load on every relevant research request.

`references/ldr-interfaces.md` should summarize the stable LDR surfaces Codex should use:

- MCP command: `ldr-mcp`
- MCP tools and expected inputs
- Python functions in `local_deep_research.api`
- Relevant settings such as `LDR_LLM_PROVIDER`, `LDR_SEARCH_TOOL`, and `LDR_SEARCH_SEARCH_STRATEGY`
- The fact that Dockerized LDR web service and host-side MCP are separate concerns

`references/research-workflows.md` should define repeatable workflows for:

- Fast source scan
- Evidence-led deep research
- Local document analysis
- Structured report generation
- Strategy selection

`references/codex-bridge-experimental.md` should document the optional future bridge, including risks and constraints.

## Primary Data Flow

The default workflow should be:

1. User asks Codex for research.
2. Skill activates and checks whether LDR is available through MCP or local commands.
3. Codex lists search engines and strategies when that context is useful.
4. Codex creates a research plan and chooses retrieval calls.
5. LDR returns raw search results, document hits, or configuration data.
6. Codex evaluates the sources, generates follow-up queries, and repeats retrieval as needed.
7. Codex writes the final synthesis with citations and confidence notes.

This keeps LDR responsible for retrieval and project-specific research infrastructure, while Codex owns the LLM generation layer.

## Optional Experimental Bridge

The bridge is a second-phase design, not the default skill behavior.

If pursued, the bridge should add a `codex` provider that behaves like a LangChain `BaseChatModel` from LDR's perspective. Internally, it would enqueue generation requests for Codex to answer through an explicit local workflow.

Minimum requirements:

- Use a transparent local queue or file protocol.
- Run one request at a time unless concurrency is deliberately designed.
- Include request IDs, timestamps, prompt hashes, and output logs.
- Enforce timeouts and cancellation.
- Return structured failures to LDR instead of hanging.
- Never rely on hidden Codex endpoints or credential extraction.
- Make the experimental nature visible in settings and documentation.

This bridge can improve compatibility with existing LDR strategies, but it should be treated as an automation helper rather than a guaranteed drop-in model API.

## Error Handling

The skill should guide Codex to handle these cases explicitly:

- MCP unavailable: fall back to documented CLI or Python API only if available.
- LDR not installed: report installation/configuration steps instead of inventing tool output.
- Search engine requires an API key: choose a no-key engine where possible, or tell the user what key is missing.
- LLM-backed LDR tool selected without an LDR provider: switch to Codex-led raw retrieval workflow.
- Source conflict: preserve competing claims and explain the evidence quality difference.
- Long-running research: checkpoint intermediate findings and continue iteratively.

## Compliance Boundaries

The skill must not instruct Codex to:

- Scrape Codex credentials.
- Call undocumented Codex inference endpoints.
- Claim that Codex is an OpenAI-compatible HTTP provider.
- Hide whether text was generated by Codex or by LDR's configured LLM provider.
- Send private local documents to external services unless the user explicitly asks and the selected tool requires it.

The skill should prefer local LDR tools and Codex's normal tool execution environment.

## Testing And Validation

Skill validation should include:

- `quick_validate.py` on the skill folder.
- A no-API-key smoke test that uses LDR raw `search` and Codex synthesis.
- A local document workflow test if a collection exists.
- A negative test where MCP is unavailable and the skill gives actionable setup guidance.
- A negative test where the user asks for transparent provider replacement and the skill routes them to the experimental bridge explanation.

Forward tests should ask a fresh Codex session to use the skill for realistic prompts:

- "Research recent advances in solid-state batteries using LDR but no API key."
- "Use my LDR document collection to answer a question and cite sources."
- "Explain whether Codex can replace LDR's LLM provider directly."

## Acceptance Criteria

- A Codex user can conduct an LDR-assisted research task without configuring an LLM API key.
- The workflow uses LDR for retrieval and Codex for generation.
- The skill clearly distinguishes stable first-phase behavior from the experimental bridge.
- The skill includes enough interface reference material for another Codex session to use LDR without rereading the whole repository.
- The skill validates successfully and has at least one smoke-tested workflow.

