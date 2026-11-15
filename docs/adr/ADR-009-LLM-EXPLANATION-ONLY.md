# ADR-009: LLM Restricted to Explanation

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ARC-07](../architecture/07_AI_AND_LLM_ARCHITECTURE.md) · [OPS-05](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## Context

LLMs are useful for turning structured analysis into plain language and answering questions, but they can hallucinate numbers and present speculation as fact. In a trading context invented levels or sizes could cause financial harm and regulatory exposure.

## Decision

The LLM is used **only** to explain computed results, summarise evidence and answer questions about the supplied analysis context. It never computes or modifies entry, stop, target, quantity, R:R, scores or classifications; its output is never written into analysis or trading tables or fed into any calculation. Responses use a structured schema and pass a deterministic validator (number and reference grounding, vocabulary consistency, banned claims). On failure, a deterministic template summary is shown. No PII or capital data is sent to the LLM.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| LLM-generated trade ideas/levels | High hallucination and advice risk; contradicts ADR-008. |
| No LLM at all | Safest, but loses accessible explanations for less experienced users. |
| LLM with tool access to compute | Increases attack surface (prompt injection) without benefit; the engine already computes. |

## Consequences

+ Explanations add value without compromising correctness; outages degrade gracefully.
− Validator may reject some acceptable outputs (fallback shown); prompt/model changes need evaluation.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
