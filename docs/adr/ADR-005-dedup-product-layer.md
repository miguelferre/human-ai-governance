# ADR-005: Product layer, deterministic dedup by default

- **Status:** Accepted
- **Date:** 2026-06-30

## Context

P3 (and p3n) carry a live anti-pattern: they emit the SAME problem several times,
almost always citing a different guideline each time (in one run, "onboarding sin
reciclaje" appeared 7 times via HAX-G1, HAX-G12, PAIR-UN-2, PAIR-MM-1, PAIR-EF-2,
PAIR-DE-1...). ~50-100 findings for ~15 real problems. A human auditor does not want
to read the same problem five times. The false-positive control (C1) already showed
that the verbosity is **redundancy, not fabrication** -> it is fixed by consolidating,
not by cutting signal.

## Decision

A dedup step with **two layers, the deterministic one by default**:

1. **Deterministic** (`dedup.py`, `review --dedup`), **the default**. Groups by lexical
   similarity (Jaccard of title+locus + title ratio with an anti-template guard) and
   **merges the cluster's guidelines** (one finding per problem, annotated with all the
   ones it breaches). No LLM, does not see the golden (in production it does not exist).
   Validated offline: **coverage lost 0 across 6 scenarios**, impurity ~0, 13-26%
   reduction in p3, generalizes to held-out, does not harm what is already concise (b1/a4).
2. **Semantic with LLM** (`dedup_llm.py`, `review --dedup-llm`), **optional, NOT by default**.
   For the residual "same problem, different guideline" that the lexical layer does not
   join (calibration: real matches with Jaccard median 0.127 -> text is not enough). The
   LLM **proposes** groups; the code **guarantees** not losing or duplicating findings and
   applies a **guardrail** (`locus_floor`) that vetoes merges of disparate locus (the LLM
   proposes, the code checks).

**Why the LLM is not the default:** it is a fundamental trade-off, not a clean
improvement. Without a guardrail it collapses hard (~17 findings) but over-merges
(impurity 6/5/9); with a guardrail the impurity drops ~1/2 (Epic to 0) but conciseness
falls to ~28-31, barely better than the deterministic one.

**Routing by difficulty** (`router.py`, `review --approach auto`), **explored, NOT adopted
as a recommendation**. It runs b1 and escalates to p3+dedup if the gap-check detects holes
or b1 comes up short. The gap-check **over-escalates** (3/4) and does not discriminate
difficulty a priori (it stayed on b1 in HireVue, leaving 0.10 undetected). It remains a
*lean-safe* option (it does shield the instability of b1, the run to 0), but **p3+dedup is
the robust default**.

## Consequences

- **The minimum product = P3 + deterministic dedup.** Concise, safe, and with no LLM cost.
- `--dedup-llm` and `--approach auto` remain as documented options with their measured
  trade-offs.
- Lesson (consistent with ADR-001): the extra complexity (LLM-dedup, router) **does not pay
  for itself**; the robust choice is the fixed pipeline + deterministic dedup. The project's
  same thesis, again.
- Pending polish (does not change the recommendation): re-judge with the new judge (ADR-006)
  to measure the REAL impurity of the LLM-dedup; the current measure is an upper bound
  (contaminated by the old judge).
