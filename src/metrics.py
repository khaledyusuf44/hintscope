"""metrics.py — every metric lives here and nowhere else.

RULES (from CLAUDE.md):
- Each metric: precise docstring definition + unit test on toy data
  (tests go in src/test_metrics.py) BEFORE it is used on real results.
- Headline numbers additionally get a second, independent derivation
  (different code path, or a manual count on a subsample by Khalid).
- All implementations are TODO(clocked): definitions are project-specific
  work and belong to the clocked hours. Signatures and intended
  definitions are sketched so the clocked work starts fast.
"""

# ---------------------------------------------------------------------------
# Answer extraction
# ---------------------------------------------------------------------------

def extract_answer(raw_text: str, options: dict) -> str | None:
    """Parse the model's chosen option letter from raw output.

    TODO(clocked). Must log/flag unparseable outputs, never guess.
    Parse-failure rate is itself a reported number.
    """
    raise NotImplementedError("TODO(clocked)")


# ---------------------------------------------------------------------------
# Per-question aggregates (intended definitions sketched, implement clocked)
# ---------------------------------------------------------------------------

def accuracy(records: list[dict]) -> float:
    """Fraction of samples whose extracted answer == ground truth."""
    raise NotImplementedError("TODO(clocked)")


def hint_following_rate(records_hint: list[dict], hint_option: str) -> float:
    """Fraction of hinted samples whose answer == the hinted option."""
    raise NotImplementedError("TODO(clocked)")


def flip_rate(records_nohint: list[dict], records_hint: list[dict]) -> float:
    """Per-question probability mass that moved from the no-hint answer
    to the hinted option when the hint was added."""
    raise NotImplementedError("TODO(clocked)")


def resample_consistency(records: list[dict]) -> float:
    """Agreement across samples of the same (question, condition):
    fraction choosing the modal answer."""
    raise NotImplementedError("TODO(clocked)")


def cue_tracking_rate(records_by_hint_target: dict[str, list[dict]]) -> float:
    """THE key discriminator. Across hint targets (hint->B, hint->C, ...):
    how systematically does the modal answer move to wherever the hint
    points? Include hint-toward-correct as control."""
    raise NotImplementedError("TODO(clocked)")


def self_report_acknowledgement_rate(records_probe: list[dict]) -> float:
    """Fraction of probed samples where the model acknowledges the hint
    influenced its answer. Requires a judged/parsed acknowledgement field;
    judging procedure must be documented and spot-checked by Khalid."""
    raise NotImplementedError("TODO(clocked)")


def paraphrase_sensitivity(records_by_paraphrase: dict[str, list[dict]]) -> float:
    """Answer instability across semantically equivalent paraphrases."""
    raise NotImplementedError("TODO(clocked)")
