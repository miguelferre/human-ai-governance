# ADR-008: Regulatory mapping (EU AI Act / NIST AI RMF)

- **Status:** Accepted
- **Date:** 2026-07-01

## Context

The reviewer produces findings tied to HAX-18 and PAIR. They are the de facto standard
of human-AI design, but **the buyer does not know them**: whoever decides the purchase
in an institution is governance, quality, or compliance, and that profile reasons in
terms of a **regulatory framework** (EU AI Act, NIST AI RMF), not academic guidelines.
A report that says "breaches HAX-G2" does not make it into their file; one that says
"this touches Art. 13 of the AI Act and MEASURE 2.9 of the NIST AI RMF" does. The
go-to-market called for turning the report from *design critique* into *evidence of
conformity* that the buyer recognizes.

## Decision

An **indicative mapping** of each HAX/PAIR guideline to AI Act articles and NIST AI RMF
subcategories/characteristics, in `guidelines/regulatory_map.yaml`, exposed in the report
with `review --crosswalk`. The `regulatory.py` module loads the map and aggregates, for a
set of findings, which requirements they touch and via which guideline (`crosswalk`).

**Level of granularity:** AI Act article (and sub-point **only** where it is unambiguous and
sellable, e.g. Art. 14(4)(b), which names *automation bias* explicitly, or Art. 86, the
right to explanation of individual decisions). NIST at the subcategory level (MAP 3.5,
MEASURE 2.9, …) and at the trustworthy-AI characteristic level (Explainable & Interpretable,
etc.).

**It is not a legal opinion.** The notice goes in the YAML, in the report section, and here:
the actual applicability of the AI Act depends on whether the system is high-risk (Annex III),
on the role (provider vs deployer), and on the case. The mapping **situates**, it does not
adjudicate; before using it as formal conformity, legal review.

## Consequences

- The report goes from academic to **situated in the framework the buyer handles** without
  changing the engine: it is a translation layer over the `guideline_ids` that the findings
  already emit.
- **Risk:** giving a false sense of legal conformity. It is mitigated with the explicit
  disclaimer and with honest granularity (dubious sub-sections are not invented).
- **Integrity verified by test** (`test_regulatory.py`): all the real guidelines are mapped
  (`unmapped_guidelines() == []`) and the map does not cite phantom ids (`unknown_map_ids() ==
  []`). If a new guideline is added, the test forces mapping it.
- **Maintenance:** if the articles change (Regulation corrections) or NIST AI RMF 2.0 comes out,
  only the YAML is updated; the code does not depend on the specific numbers.
- The option is **opt-in** (`--crosswalk`): it does not clutter the base report for whoever only
  wants the design review.
