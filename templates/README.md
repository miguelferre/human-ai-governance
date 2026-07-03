# Templates to describe your AI system

Thank you for helping to review your system. These templates serve to
describe **what your AI system is like and, above all, how the person who uses
it experiences it**. With what is provided, a structured review of the
*interaction layer* is built and specific findings and recommendations are returned.

No technical knowledge is needed for most of the questions. Write in
plain words: an honest, specific answer is better than a
"perfect" one.

---

## What exactly is being reviewed?

It is not whether the model "gets it right" (that is already measured by other tools).
What is reviewed is the **interaction layer**: everything that happens between the model's
output and the person's decision. For example:

- Is it clear what the system does and what it does **not** do?
- Does the person understand **why** it proposes what it proposes?
- Is it shown when the system is **not very confident**?
- When the person **disagrees**, can they change it? Is there a record? Does it serve any purpose?
- Does it interrupt at the wrong moment? Are there too many alerts?

> Simple example: a system suggests the priority of a support ticket. If
> the agent almost always accepts the suggestion without looking at it and, when they change it,
> that change is not saved anywhere, that is a problem of the interaction
> layer, even if the model is very accurate.

---

## What is needed from you?

Three templates (fill in the ones that apply to your role) and, if available,
some documents:

| Template | What it captures | Who fills it in best |
|---|---|---|
| [`01_system_card__technical_profile.md`](01_system_card__technical_profile.md) | What the system does, how it presents the result, override, alerts, oversight | Technical lead, data scientist, product/deployment lead |
| [`02_usage_experience__end_user.md`](02_usage_experience__end_user.md) | How the system is experienced day to day | End user (whoever uses the tool to decide) |
| [`03_document_inventory.md`](03_document_inventory.md) | What documents exist and can be provided | Anyone with access to the documentation |

A single person does not have to fill in everything. In fact, **it is better they do not**:
the interest is in contrasting the technical view with that of the end user.

---

## Who is each thing needed from, and why?

- **From the technical / product profile** -> how the system is built and designed
  on the inside (the "intent"). Template 01 + technical documents.
- **From the end user** -> how it is really experienced (the "reality of use").
  Template 02.
- **The contrast between the two** is one of the most valuable things sought.
  When the technical side believes that "the user's change is saved and serves to
  improve" but the user says "I don't know if changing it does any good", there is an
  important signal there. That is why the two voices are requested separately.

---

## What will what you provide be used for?

- To build a **dossier** of the system (its normalized description) and put it
  through the review.
- To produce **anchored findings**: each observation will be tied to a recognized
  guideline (Microsoft's HAX-18, Google's PAIR) and to a specific point in your
  system, with the evidence of what was reported.
- It is **not** shared with third parties or used for anything else.

---

## Privacy (important)

- **Do not include personal data** (patients, clients, real users): no
  names, no identifiers, no identifiable specific cases. To review the
  interaction they **are not needed**. Describe the system, not its users.
- If a document contains sensitive data, **anonymize it or remove it** before
  sending it. When in doubt, better not send it and describe it in words.
- If your system is clinical, the above applies all the more.

---

## A nuance that helps a lot

Describe **what the system is like**, not **what you think is wrong** with it. The point of the
review is for it to detect the problems on its own from a faithful description. If
you want to share your own diagnosis in advance ("I think the override is poorly captured"),
that is fine, but note it **at the end, in the "What you already suspect" section** of
each template, separate from the rest. That way it does not get mixed with the description.

---

## How to deliver it

There are two options, whichever is more convenient:

1. **Fill in the `.md` files** (these templates) by writing under each question, and
   send them back.
2. **Fill in [`dossier_plantilla.json`](dossier_plantilla.json)** if a structured
   format is preferred (or if it is going to be integrated directly with the tool).

Also attach the documents marked in template 03.

---

<details>
<summary><strong>Internal traceability map (evaluating team use)</strong></summary>

The templates deliberately avoid guideline jargon. This is the internal
correspondence between each block and the guidelines it covers, to build anchored
findings:

| Template block | Main guidelines |
|---|---|
| What it does / does not do | HAX-G1, PAIR-MM-1, PAIR-UN-1 |
| Performance and limits | HAX-G2, PAIR-MM-2 |
| How the result is presented | HAX-G4 |
| Confidence / uncertainty | HAX-G2, PAIR-ET-2, PAIR-ET-3 |
| Explanation of the "why" | HAX-G11, PAIR-ET-1 |
| Override / correction | HAX-G9, HAX-G16, PAIR-FC-1, PAIR-FC-2 |
| Dismissal and timing / alerts | HAX-G3, HAX-G8 |
| Onboarding | HAX-G1, PAIR-MM-1 |
| On uncertainty / failure | HAX-G10, PAIR-EF-1, PAIR-EF-2 |
| Oversight / subgroups | PAIR-DE-1, HAX-G6 |
| Changes and controls | HAX-G14, HAX-G17, HAX-G18 |
| Feedback | HAX-G15, PAIR-FC-1 |

The "answer key" (known problems to validate the tool) is collected **separately**
and never within these templates, so as not to contaminate the blind run.

</details>
