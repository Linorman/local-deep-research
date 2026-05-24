# WebUI Pipeline Parity

Use this reference when the user asks whether Codex can reproduce the Local Deep Research WebUI pipeline.

## Exact WebUI Call Graph

```text
research.html / research.js
  -> /research/api/start
  -> research_routes.start_research()
  -> start_research_process()
  -> research_service.run_research_process()
  -> get_llm() + get_search()
  -> AdvancedSearchSystem(strategy=...)
  -> strategy.analyze_topic()
  -> question generation
  -> iterative searches
  -> filtering and citation synthesis
  -> quick mode: save formatted findings
  -> detailed/report mode: IntegratedReportGenerator.generate_report()
  -> section structure
  -> subsection re-search
  -> report formatting
  -> history, sources, metadata, progress, errors, exports
```

## Mode Matrix

| Mode | Generator | LDR internals used | Exact WebUI pipeline | Main use |
| --- | --- | --- | --- | --- |
| `codex_like` | Codex | Discovery and raw retrieval | No | Research without an LDR model provider |
| `ldr_exact` | LDR configured provider | Existing WebUI/API generation path | Yes, for research output path | Exact WebUI behavior with an LDR provider |
| `codex_bridge_exact` | Codex through explicit file bridge | Existing LDR pipeline and prompts | Experimental yes | Exact LDR internals with Codex as the model |

## Non-Equivalent Surfaces

`codex_like` does not reproduce:

- WebUI queue state.
- Database history and active research records.
- Socket.IO progress event timing.
- LDR provider prompt templates.
- Strategy-specific source ordering.
- Citation offset behavior from `all_links_of_system`.
- LDR-side token accounting.
- Report export behavior.

## Decision Rule

```text
If exact WebUI result shape matters, use ldr_exact.
If exact WebUI internals plus Codex-as-model matters, use codex_bridge_exact after bridge validation and start it with scripts/run_codex_bridge_exact.py.
If no LDR model provider is available, use codex_like and label the result as approximate.
```

Same model id is not enough for parity. Prompt templates, context packing, truncation, source filtering, report section re-search, citation formatting, temperature, and tool ordering all affect output quality.

For Codex-only use, no WebUI JavaScript or settings UI changes are required. The necessary parity boundary is the LDR Python pipeline plus `llm.provider=codex_bridge`, a bridge responder loop, and strict adherence to each internal prompt's response contract.
