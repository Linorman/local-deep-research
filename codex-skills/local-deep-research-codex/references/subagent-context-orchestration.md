# Sub-Agent Context Orchestration

Use sub-agents as a Codex-side context management layer. They help split large evidence sets and independent review tasks; they do not make an approximate research mode exact.

## Mode Rules

- `codex_like`: sub-agents can run independent retrieval, evidence extraction, contradiction checks, and bounded section drafts.
- `ldr_exact`: sub-agents are outside the LDR run. Use them only before the run for code/config inspection or after the run for QA.
- `codex_bridge_exact`: the bridge coordinator owns each request/response pair. Sub-agents may audit large source packets, but they should not answer bridge requests unless a benchmark explicitly validates that workflow.

## Coordinator Ownership

The main Codex coordinator owns:

- Final mode labeling.
- Canonical source ledger.
- Citation numbering.
- Source deduplication.
- Final report decisions and wording.
- Merge decisions when sub-agent outputs conflict.

## Recommended Roles

```text
pipeline_mapper: inspect code paths and strategy-specific prompts.
retrieval_worker: run or summarize independent raw-search packets.
evidence_auditor: verify that claims are supported by source ledger entries.
section_worker: draft a bounded report subsection from supplied evidence.
benchmark_reviewer: compare completed outputs against the parity rubric.
```

## Merge Contract

Every sub-agent output must include:

```text
- task id
- input packet id
- sources touched
- claims supported
- unresolved gaps
- confidence notes
- canonical citation ids changed: no
```

## Failure Modes

Guard against:

- Duplicated sources.
- Renumbered citation ids.
- Unsupported claims.
- Hidden assumptions.
- Section drift away from the original research question.
- Pasted conclusions without source review.

Use `scripts/split_research_packet_for_subagents.py` to generate bounded packet files when a file-backed workflow is useful.
