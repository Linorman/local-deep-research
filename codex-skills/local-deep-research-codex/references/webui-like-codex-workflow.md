# WebUI-Like Codex Workflow

Use this reference when the user wants results close to the official LDR WebUI while using Codex as the generation model.

## Equivalence Target

This mode approximates WebUI output shape and research discipline, not the exact WebUI execution path.

- Equivalent goal: same research intent, same LDR search engines where available, similar iterative evidence accumulation, citation-rich final output.
- Different generator: Codex writes plans, follow-up questions, current knowledge, and the final report.
- Not equivalent: WebUI queue state, database history, Socket.IO progress events, report export, LDR provider prompts, and LDR-side token accounting.

Use official WebUI/API generation only when the user explicitly wants exact WebUI behavior and accepts configuring an LDR model provider.

Only `ldr_exact` or `codex_bridge_exact` should be described as WebUI-pipeline parity. `codex_like` may produce comparable prose when Codex has a strong model and a good source ledger, but it must be labeled as approximate.

Same model id is not enough for equivalent output. Prompt templates, truncation rules, source filtering, citation handling, report section re-search, temperature, token limits, and tool ordering all affect quality.

## Mode Budgets

| Mode | Iterations | Subquestions | Searches | Output |
| --- | ---: | ---: | ---: | --- |
| Quick summary | 1 | 2-4 | 3-6 | Short answer with source list |
| Detailed research | 2-3 | 4-8 | 8-18 | Structured analysis with gaps |
| Full report | 3-5 | 6-12 | 15-35 | Report with methodology and limitations |

Adjust down when sources are sparse or the user wants speed. Adjust up only when the user asks for depth and LDR access is working.

## Research Packet

Maintain a compact packet during long research. Use `scripts/new_research_packet.py` when a file-backed packet helps avoid context loss.

Required sections:

- Objective: the user's research question and success criteria.
- Configuration: available LDR access, selected engines, strategy vocabulary, date/time assumptions.
- Plan: subquestions, search terms, and iteration budget.
- Source ledger: stable IDs such as `S01`, URL or local collection identifier, title, date, engine, credibility note.
- Claim table: claim, supporting source IDs, confidence, limitations.
- Current knowledge: compressed synthesis after each iteration.
- Gaps: unresolved questions and follow-up searches.

Never let final claims depend on untracked raw snippets. Either assign a source ID or omit the claim.

When a harness is driving the run, initialize the packet from `prepare_harness_run.py` output rather than re-inferring mode, engine, or iteration budget.

## Iteration Loop

1. Discover configuration with `list_search_engines`, `list_strategies`, and `get_configuration` when available.
2. Generate focused search questions from the current gaps, not from a generic keyword list.
3. Run raw LDR `search` calls first. Avoid `quick_research`, `detailed_research`, `generate_report`, and `analyze_documents` unless the user chooses LDR-provider-backed generation.
4. Normalize results into the source ledger. Merge duplicates by canonical URL, DOI, paper ID, repository, or local document identifier.
5. Extract evidence into the claim table. Separate observed source claims from Codex inference.
6. Update current knowledge in 5-10 bullets. Include source IDs and gaps.
7. Stop when the planned budget is exhausted, the evidence is sufficient, or additional retrieval is unlikely to change the answer.

## Context Handling

- Keep raw snippets short. Store only title, URL, date, snippet, and why it matters.
- Preserve source IDs across the whole task. Do not renumber sources after pruning.
- Compress after every iteration: current knowledge should replace raw result dumps in active context.
- For long reports, draft from the claim table and source ledger, not from memory.
- When the context is near saturation, summarize old iterations into current knowledge and keep the packet sections above.

## Subagent Pattern

Use subagents only if the runtime permits them and the user has authorized delegation or parallel agent work.

Good splits:

- By subquestion: each agent handles one independent research question.
- By source type: academic papers, official docs, news/current web, code repositories, local documents.
- By verification role: one agent checks citation support or identifies contradictions while the main agent drafts.

Rules:

- Give each agent a bounded search scope and expected output schema: source IDs, claims, confidence, gaps.
- Do not send private local documents to a subagent unless the user explicitly allows that in the current environment.
- Reconcile conflicts in the main thread. The final report must not paste agent conclusions without source review.
- Close agents when their contribution has been integrated.

## WebUI-Style Output

For a full report, use this structure unless the user asks otherwise:

1. Title
2. Scope and method
3. Executive summary
4. Key findings
5. Detailed analysis by section
6. Evidence table or source-backed claim list
7. Limitations and unresolved questions
8. Source list

For quick mode, collapse this into answer, evidence, limitations, and sources.

## Error Handling

- If LDR is not importable or MCP is unavailable, run the diagnostic helper and report the missing component.
- If an engine requires an API key, switch engines when possible and note the limitation.
- If no raw search path is available, do not invent WebUI-like results. Offer setup steps or ask whether to use web browsing outside LDR.
- If exact WebUI parity is requested, explain that it requires official WebUI/API generation with an LDR model provider.
- If a harness payload sets conflicting values, prefer explicit CLI fields over prompt directives and report the effective parameter set.
