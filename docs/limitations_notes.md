# Limitations / incident notes (lab record — facts for Khalid's write-up, not draft prose)

- **Adjudication-interface extraction bug (2026-08-27).** During the hand
  adjudication of the 45 flagged quiet@16k probe responses, the browser
  adjudication interface mis-extracted the model's answer letter on 18 of 45
  cards: its regex captured the pronoun "I" from phrases like "I chose F...".
  Caught during cross-check; letters re-extracted with a corrected parser; all
  18 cards re-adjudicated; 3 verdicts changed. Final calls are in
  `results/adjudication_final.json` and are final (never re-scored by any
  automated judge).
- **Keyword-judge error rates vs hand ground truth (n=45 flagged responses):**
  false negatives 5/29 (Section 1 responses that actually CONFESSED), false
  positives 5/16 (Section 2 responses counted as acknowledgement that were
  actually HONEST_REFUSAL). The unflagged 88/133 keyword-acks were NOT
  hand-adjudicated; rates using them inherit unknown judge error.
- **Confession-rate denominator conventions** (Khalid picks headline): unsure
  excluded 101/128 = 0.789; unsure=non-confession 101/133 = 0.759;
  unsure=confession 106/133 = 0.797. Within the adjudicated 45, followers
  only: 13/26 = 0.500.
- **Flip-table denominator convention:** headline numbers use parsed-only
  denominators; the conservative all-records variant (parse failures count
  against the flip) gives loud +0.30 / quiet +0.62 / neutral +0.35 (vs
  +0.31/+0.65/+0.37). Verified by an independent from-scratch derivation:
  800/800 sample extractions and 60/60 cells agree under a common convention.
- **No-hint baseline caps are mixed** (13 questions at 6k, 7 at 16k re-run);
  all cue conditions ran at 16k.
- **Probe truncation differs by condition** (loud 1/20, quiet@16k 17/150,
  neutral 6/80) — finished-only Ns are not matched across conditions.
- **Arm-difficulty confound** (Arm 1 questions harder by construction) —
  standing note from the design; unchanged.
