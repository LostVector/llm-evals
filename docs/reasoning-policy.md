# Reasoning budget and handling

Reasoning is a run parameter alongside quantization, backend, harness and sampling settings. `reasoning_effort` is a provider hint, not a numeric token budget. `max_tokens` is the total output cap when the backend counts thinking and final output together; a 256k context window does not enlarge that cap.

Record a `reasoning` object in private runner configuration and public export metadata. GPQA and coding runners freeze it in their manifests and reject resuming into a directory with a different policy. Terminal-Bench runs must record the same policy in their run metadata, with `budget_scope: per_turn`. These metadata fields describe verified configuration; they do not send engine flags or change server behavior.

Example for a prospective, separately labeled run (not the settings of any completed run):

```json
{
  "reasoning": {
    "budget_tokens": 24576,
    "budget_scope": "per_request",
    "budget_enforcement": "server",
    "budget_exhaustion": "force_close_then_answer",
    "final_answer_reserve_tokens": 8192,
    "output_cap_includes_reasoning": true,
    "parser": "unknown",
    "chat_template_sha256": null,
    "verification": "configured"
  }
}
```

`budget_tokens: null` means unknown; `-1` means explicitly unlimited; `0` means no thinking allowance. Reserve tokens describe intended output headroom, not a guaranteed answer length. Record parser name and template hash when known. Verification is `configured`, `observed`, or `unknown`; configure the engine and verify returned final content before claiming observed forced closure.

Handling options are `force_close_then_answer`, `stop_generation`, `none`, or `unknown`; enforcement is `server`, `client`, `none`, or `unknown`. Record total output cap separately in `generation.max_tokens`. Always retain truncation, unparsed-answer and forced-closure counts. Score final content only, without recovering answers from private reasoning.

Historical Halogen runs reported 31 GPQA and 49 coding forced closures, all at generated-token position 27,853 and attributed to `answer_room`. Those observed thresholds are recorded in the published metadata; the exact closing message and model template identity remain unknown. The original GSQ-RCO run had total-cap truncations. Its corrected-policy continuation explicitly sends a 27,853-token reasoning budget to the verified llama.cpp endpoint; forwarding and final-content delivery were tested through the gateway. See the [GSQ-RCO run disclosure](gsq-rco-evaluation.md) for partial-regeneration selection and sampling caveats.

A changed budget, closure policy, parser or template requires a new run identity and output directory. Keep the original score and any new run separate; do not rerun only failed questions and splice the results. Frontier records with unreported reasoning settings remain contextual references. The comparison page retains distinct generation/reasoning profiles rather than deduplicating them as one result.

Closure counts require backend telemetry. Halogen supplies `reasoning_closed_by`; llama.cpp responses in this run do not. Public exports with `reasoning_closure_telemetry: not_reported` omit the forced-closure count instead of treating missing markers as proof of zero closures.
