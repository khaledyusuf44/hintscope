# Locked Research Plan — written by Khalid, verbatim. DO NOT EDIT OR REDESIGN.

## Decision

I'm locking the **black-box behavioral forensics project as the core**, with the CoT-guided internal analysis only as a stretch.

The main question is:

**Can simple behavioral tests distinguish ordinary model errors from errors that are causally driven by a hidden hint, without relying on chain-of-thought?**

## Setting

I'll use **hint-induced answer flipping** on multiple-choice reasoning questions.

The key comparison is between two arms:

### Arm 1: Organic errors

Questions the model gets wrong **without any hint**.

These are my no-planted-cue cases. I won't assume all of them are "confusion"; some may be noisy mistakes, while others may be stable misconceptions.

### Arm 2: Hint-induced errors

Questions the model gets right normally, but gets wrong after I introduce a misleading hint.

These are my known cue-driven cases.

The project asks whether simple behavioral signatures can separate these two groups.

## Predicted signatures

| Behavior type        | Resampling    | Paraphrases   | Cue intervention                             |
| -------------------- | ------------- | ------------- | -------------------------------------------- |
| Noisy error          | unstable      | sensitive     | does not systematically track cue            |
| Stable misconception | stable        | often stable  | remains largely cue-independent              |
| Cue-driven error     | may be stable | may be stable | **moves systematically when the hint moves** |

The important discriminator is therefore **not consistency by itself**.

It is **cue-tracking**.

If I move the hint from B to C and the model's answer systematically moves from B toward C, that is stronger evidence that the cue is causally driving the behavior.

## Main experiments

Priority order:

1. **Resampling**
2. **Cue interventions**
3. **Self-report / acknowledgement of hint use**
4. **Paraphrasing**, if time allows
5. Clarification experiments are the first thing I cut if scope gets tight

Primary metrics:

* hint-following rate
* answer flip rate
* consistency across resamples
* cue-tracking rate
* paraphrase sensitivity
* self-report / acknowledgement rate

## Hour-one kill gate

I'll begin with roughly **20–30 questions** on the chosen thinking model.

For each question:

1. Run without a hint.
2. Identify questions the model answers correctly.
3. Add a misleading hint.
4. Check whether the answer moves toward the hint.
5. Repeat enough times to verify that the effect is reproducible.
6. Check whether the model acknowledges that the hint influenced its answer.

The gate is:

**Can I reliably produce cases where the model answers correctly without the cue, moves toward a misleading answer when the cue is added, and often fails to report that influence?**

If no, I kill the setting.

If yes, I proceed.

## Where CoT fits

CoT is **not part of the minimum successful project**.

If the behavioral result works and time remains, I'll use CoT as a forensic lead.

The idea is:

**bad behavior → inspect reasoning → identify candidate important moments → resample around those moments → see whether they point toward stronger internal signals**

If a reasoning moment appears causally important under resampling, I can then do an internals-lite follow-up such as logits or activation inspection around that region.

The claim would not be that CoT explains the behavior.

It would be:

**CoT may act as a map that points toward where stronger mechanistic evidence is worth looking for.**

## Novelty / framing

Prior work already shows that models can use hints without admitting their influence.

My question is different:

**Can black-box behavioral signatures diagnose cue-driven errors versus ordinary model mistakes without needing access to chain-of-thought?**

The CoT-guided internal analysis is only a stretch extension if the behavioral diagnostic works cleanly.

## 16-hour spine

**Replicate → build both arms → resample → intervene on cue → measure cue-tracking → compare signatures → evaluate diagnostic → optional CoT-guided mechanistic follow-up**

That is the version I'm locking.
