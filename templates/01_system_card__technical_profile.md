# Template 01: System card

**Who fills it in:** technical lead, data scientist, or product/deployment owner.
**Approximate time:** 20-30 minutes.
**How:** write your answer below each question, in the `✍️` space. If something does
not apply or you do not know, write that too (it is also useful information).

> Remember: describe **what the system is like**, not its real users. No personal
> data (see privacy in the README).

---

## 0. Identification

- **System name:**
  ✍️
- **Domain / what it is used for:**
  ✍️
- **Status:** (idea / pilot / production / retired)
  ✍️
- **Who is it aimed at?** (which profile uses it to decide)
  ✍️

🎯 *What for:* to place the system and its user. Without this, any finding would be
generic.

---

## 1. What it does and what it does NOT do

- **What task does the model solve?** (in one or two sentences)
  ✍️
- **What exactly does it produce?** (a score, a category, a text, a recommendation...)
  ✍️
- **Does the system decide or suggest?** Can the person choose not to follow it?
  ✍️
- **What does it NOT do, even if someone might expect it to?**
  ✍️

🎯 *What for:* to check whether the scope and the split of responsibility (person vs
system) are clear. It is the root of many misunderstandings.

> Example: "Suggests high/medium/low priority for a ticket. It does not close or
> assign the ticket; the agent decides. It does not detect duplicate tickets, even
> though people sometimes think it does."

---

## 2. Performance and limits

- **How well does it work?** (any metrics you have: accuracy, etc.)
  ✍️
- **Where does it fail most or is least reliable?** (case types, populations, situations)
  ✍️
- **Is performance measured by subgroup?** (by case type, age, sex, language...)
  ✍️

🎯 *What for:* to see whether the system's limits are known and, later, whether they
are communicated to the person using it.

> Example: "Overall accuracy 0.82. Worse on tickets in Catalan. We do not measure
> performance by ticket category."

---

## 3. How the result is presented to the user

- **Where and how does the result appear?** (screen, pre-filled field, alert, email...)
  ✍️
- **What exactly does the person see?** Describe the screen or the message.
  ✍️
- **Does any context appear alongside the result** (factors, case data) or just the result on its own?
  ✍️

🎯 *What for:* how it is shown strongly conditions how the decision is made. A bare
number, pre-filled, pushes toward accepting it without thinking.

---

## 4. Confidence and uncertainty

- **Is it shown when the system is unsure?** How? (a %, a color, a text...)
  ✍️
- **Are all outputs presented as equally confident**, or is the doubtful set apart?
  ✍️

🎯 *What for:* to detect the risk of **over-trust** (automation bias): if everything
looks equally firm, the person does not know when to doubt.

---

## 5. The "why"

- **Can the person know why the system proposes what it proposes?** How do they see it?
  ✍️
- If there is an explanation, **is it useful for deciding** or is it technical/decorative?
  ✍️

🎯 *What for:* without an accessible "why", confidence cannot be calibrated.

---

## 6. When the person disagrees (override / correction)

This block is one of the most important.

- **Can the person change, overrule, or ignore the proposal?** How easy is it?
  ✍️
- **When they change it, is that change recorded anywhere?**
  ✍️
- **Is the reason for the change recorded?** Free-form or structured (categories)?
  ✍️
- **What is that record used for?** (oversight, retraining, nothing...) Does the person know?
  ✍️

🎯 *What for:* a poorly captured override (or one captured but unused, or without a
reason) is a classic, silent anti-pattern.

> Example: "They can change the priority with a dropdown. The change is saved, but not
> the reason. We assume it is for retraining, though nobody reviews it today."

---

## 7. Dismissal, timing, and alerts

- **Can they easily ignore or close the suggestion,** or does it reappear / nag?
  ✍️
- **Does the system interrupt?** At what point in the workflow does it appear?
  ✍️
- **How many alerts/warnings does it generate?** Is there a saturation risk (alert fatigue)?
  ✍️

🎯 *What for:* poor timing and too many alerts make people end up ignoring everything,
including what matters.

---

## 8. First contact (onboarding)

- **How does the person learn to use the system and understand what it does?** (training, intro text, nothing...)
  ✍️
- **Are the limitations explained up front?**
  ✍️

🎯 *What for:* a good start sets correct expectations; its absence breeds mistaken
mental models.

---

## 9. On insufficient data or failure

- **What does the system do if it lacks enough data or is unsure?** (does it abstain, warn, propose something anyway?)
  ✍️
- **If it fails or cannot act, what does the person see?** (clear message / technical error / nothing)
  ✍️

🎯 *What for:* to see whether the system "degrades gracefully" or fails silently / with
unjustified confidence.

---

## 10. Oversight and subgroups

- **Who watches that the system keeps working well once deployed?**
  ✍️
- **Is that oversight automatic or manual?** How often?
  ✍️
- **Is it watched that it does not harm some subgroup** more than others?
  ✍️

🎯 *What for:* manual or nonexistent subgroup oversight is a frequent weak spot and
hard to see from the inside.

---

## 11. Changes and controls

- **When the system changes behavior (an update), are users notified?**
  ✍️
- **Can the person configure anything** (thresholds, which alerts they get, enable/disable)?
  ✍️

🎯 *What for:* silent changes break trust; the lack of controls leaves the person with
no room to maneuver.

---

## 12. Feedback

- **Is there any way for the person to give their opinion on a proposal?** With what detail?
  ✍️

🎯 *What for:* without feedback channels (or ones that are too coarse), the system does
not improve with use.

---

## What you already suspect (optional, keep it apart from the rest)

If you have an intuition about what is wrong in the interaction, write it **here**, not
above. It helps us cross-check, but we want it separate from the description.

✍️
