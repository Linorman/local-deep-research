# Codex Bridge Experimental Reference

Use this reference only when the user asks whether Codex can transparently replace LDR's in-process LLM provider or asks for a Codex `BaseChatModel`.

## Default Answer

The stable fallback remains Codex-led orchestration: LDR retrieves sources and Codex performs generation. When the installed LDR build exposes `codex_bridge`, the supported experimental exact path is `codex_bridge_exact`: LDR uses its normal pipeline and a local file queue, while Codex answers each request in the active session.

A Codex skill still cannot become a network model endpoint, and this bridge must stay explicit and local.

## Why A Direct Provider Is Not The Default

- Codex skills guide Codex behavior; they do not expose a stable inference API to arbitrary local processes.
- LDR expects synchronous or async `model.invoke()` and `model.ainvoke()` behavior from LangChain chat models.
- Many LDR strategies issue multiple model calls and sometimes concurrent calls.
- A bridge must handle request identity, timeouts, cancellation, logging, and user visibility.
- A fake OpenAI-compatible endpoint backed by hidden Codex behavior is not a compliant design.

## Accepted Experimental Shape

An explicit bridge is acceptable only as a user-visible local automation loop. It is not a hidden background service, and it is not an HTTP/OpenAI-compatible model endpoint.

1. LDR registers a `codex_bridge` provider implementing `BaseChatModel`.
2. The provider writes each prompt to a local queue with a request ID.
3. Codex reads queued requests in the active user session.
4. Codex writes responses to a response file.
5. The provider reads the response, enforces timeout, and returns a LangChain `ChatResult`.

## Minimum Requirements

- The user must explicitly enable the bridge.
- Requests must include request ID, timestamp, prompt hash, and source process metadata.
- Responses must include request ID, timestamp, model attribution, and completion status.
- Cancelled or expired request IDs must not receive normal completions; cancellation must return a structured LDR error/status.
- The bridge must be serial by default.
- Timeouts must return structured LDR errors.
- Queue and response files must be local-only, access-controlled where feasible, cleaned up by retention policy, and kept out of external sync folders.
- Each request must be visible or auditable in the active Codex session.
- Response attribution must identify Codex session generation rather than an LDR-native provider response.
- Logs must not include private document text unless the user accepts local prompt logging.
- The bridge must not call undocumented Codex endpoints.

## Recommended Response To Provider-Replacement Requests

Explain that the compliant path is:

1. Use `codex_bridge_exact` when exact LDR pipeline behavior with Codex generation is required.
2. Use `codex_like` when the bridge is unavailable or the user only needs LDR retrieval plus Codex synthesis.
3. Keep the bridge explicit, local, auditable, and never exposed as a fake OpenAI-compatible endpoint.

## Code Pointers If Engineering Work Is Approved

- Provider interface: `src/local_deep_research/llm/providers/base.py`
- Provider auto-discovery: `src/local_deep_research/llm/providers/auto_discovery.py`
- Provider implementations: `src/local_deep_research/llm/providers/implementations/`
- LLM creation path: `src/local_deep_research/config/llm_config.py`
- Custom LLM registry: `src/local_deep_research/llm/llm_registry.py`
- Codex exact runner: `codex-skills/local-deep-research-codex/scripts/run_codex_bridge_exact.py`
- Bridge responder helper: `codex-skills/local-deep-research-codex/scripts/respond_to_codex_bridge.py`
