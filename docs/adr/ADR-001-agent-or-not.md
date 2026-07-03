# ADR-001: Start without an agent; build an approach ladder of baselines

- **Status:** Accepted
- **Date:** 2026-06-27

## Context

The goal is a reviewer of the human-AI interaction layer. The default temptation
is to build "an agent". But the complexity of an agentic system (loops, tool use,
autonomous decisions) is only justified if it **measurably improves** over simpler
alternatives. There is no evidence that it is needed.

## Decision

No agent is built in v1. An **approach ladder** of complexity is defined, and a
rung is only climbed when the evaluation demands it:

1. **B0** - deterministic checklist (no LLM). The floor.
2. **B1** - single zero-shot prompt.
3. **B2** - single few-shot prompt.
4. **P3** - deterministic pipeline (fixed control flow, NOT an agent).
5. **A4** - agent (autonomous decisions, tool use, loop).

"Agent" is not synonymous with "more complex": B1 < B2 < P3 < A4. Each jump must
**beat** the previous rung on the primary metric by a margin larger than the
variance across runs (see `metrics.beats` and ADR-002). Otherwise it is discarded
and the reason is documented.

## Consequences

- v1 delivers B0 (and, in F2, B1/B2) and an evaluation harness, not an agent.
- Over-engineering is avoided: the cost of complexity is only paid when there is data.
- Risk: perhaps no rung beats B1; that would be a **valid result** of the experiment
  (the agent is unnecessary for this task), not a failure.
