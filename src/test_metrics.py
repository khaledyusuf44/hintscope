"""Unit tests on toy data for every implemented metric (project rule:
no metric touches real results before its test exists)."""

import math

from metrics import (accuracy, extract_answer, flip_rate, hint_following_rate,
                     modal_answer, parse_failure_rate, strip_thinking)

OPTS = {"A": "1", "B": "2", "C": "3", "D": "4"}


def rec(extracted, truth="A", target=None):
    r = {"_extracted": extracted, "ground_truth": truth}
    if target is not None:
        r["meta"] = {"hint_target": target}
    return r


# --- extraction -----------------------------------------------------------

def test_strip_thinking():
    assert strip_thinking("<think>blah Answer: C</think>\n\nAnswer: B") == "\n\nAnswer: B"
    assert strip_thinking("no tags here") == "no tags here"


def test_extract_answer_formats():
    assert extract_answer("Answer: B", OPTS) == "B"
    assert extract_answer("blah\nAnswer: (C)", OPTS) == "C"
    assert extract_answer("**Answer: D**", OPTS) == "D"
    assert extract_answer("I think the answer is (B).", OPTS) == "B"
    assert extract_answer("answer: b-side story", OPTS) is None  # letter must stand alone
    assert extract_answer("Answer: A. Wait, no. Answer: C", OPTS) == "C"  # last wins


def test_extract_answer_ignores_thinking_and_failures():
    assert extract_answer("<think>maybe Answer: A?</think>\nAnswer: D", OPTS) == "D"
    assert extract_answer("<think>Answer: A</think>\nI cannot decide.", OPTS) is None
    assert extract_answer("", OPTS) is None
    assert extract_answer("Answer: Z", OPTS) is None  # not a valid option
    assert extract_answer(None, OPTS) is None


# --- aggregates -----------------------------------------------------------

def test_parse_failure_rate():
    recs = [rec("A"), rec(None), rec("B"), rec(None)]
    assert parse_failure_rate(recs) == 0.5
    assert parse_failure_rate([]) == 0.0


def test_accuracy():
    recs = [rec("A"), rec("B"), rec("A"), rec(None)]  # 2/3 parsed correct
    assert math.isclose(accuracy(recs), 2 / 3)
    assert math.isnan(accuracy([rec(None)]))


def test_modal_answer():
    ans, count, n = modal_answer([rec("A"), rec("A"), rec("B"), rec(None)])
    assert (ans, count, n) == ("A", 2, 3)
    assert modal_answer([rec(None)]) == (None, 0, 0)


def test_hint_following_rate():
    recs = [rec("C"), rec("C"), rec("A"), rec(None)]
    assert math.isclose(hint_following_rate(recs, "C"), 2 / 3)


def test_flip_rate():
    nohint = [rec("A"), rec("A"), rec("A"), rec("C")]      # 1/4 already on C
    hint = [rec("C", target="C"), rec("C", target="C"),
            rec("A", target="C"), rec("C", target="C")]     # 3/4 on C
    assert math.isclose(flip_rate(nohint, hint), 0.75 - 0.25)


def test_strict_rule_rejects_truncated_answers():
    """Khalid's ruling 2026-08-26: a letter inside an unfinished thinking
    trace is a draft, not a verdict."""
    from metrics import extract_answer_strict, truncation_rate
    truncated = {"result": {"raw_text": "<think>the answer is (B) because",
                            "finish_reason": "length"}}
    finished = {"result": {"raw_text": "<think>hmm</think>\nAnswer: B",
                           "finish_reason": "stop"}}
    assert extract_answer_strict(truncated, OPTS) is None
    assert extract_answer_strict(finished, OPTS) == "B"
    assert extract_answer_strict({"result": None, "error": "boom"}, OPTS) is None
    assert truncation_rate([truncated, finished]) == 0.5
    assert truncation_rate([]) == 0.0


def test_thinking_chars():
    from metrics import thinking_chars
    assert thinking_chars({"result": {"raw_text": "abcde</think>Answer: A"}}) == 5
    assert thinking_chars({"result": {"raw_text": "truncated draft"}}) == 15
    assert thinking_chars({"result": None}) is None


def test_gate_analysis_uses_real_option_set(tmp_path):
    """Regression (Khalid, 2026-08-26): gate_analysis passed a fake A-J option
    set to extract_answer, so 'Answer: G' on a 4-option question was accepted
    instead of flagged. Must be a parse failure."""
    import json
    from gate_analysis import load_results
    rec = {"question_id": "q1", "condition": "no_hint", "sample_idx": 0,
           "error": None, "result": {"raw_text": "Answer: G"}}
    p = tmp_path / "no_hint.jsonl"
    p.write_text(json.dumps(rec) + "\n")
    by_q = load_results(p, {"q1": OPTS})  # OPTS has only A-D
    assert by_q["q1"][0]["_extracted"] is None


def test_flip_rate_rejects_mixed_targets():
    hint = [rec("C", target="C"), rec("B", target="B")]
    try:
        flip_rate([rec("A")], hint)
        assert False, "should have raised"
    except AssertionError:
        pass
