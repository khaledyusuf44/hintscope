"""gate_compare.py — side-by-side loud (authority) vs quiet (metadata_leak)
hint comparison over the 20-question qualified pool, identical per-question
cue targets, strict answer rule throughout.

Baselines: each question's no-hint records come from the run where it
qualified — the original 6k run for the 13 strict-clean questions, the 16k
re-run for the held-cohort questions (their 6k data was truncation-broken).

Usage: python src/gate_compare.py
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from metrics import extract_answer_strict, flip_rate, modal_answer, thinking_chars

ROOT = Path(__file__).resolve().parent.parent
OPTS = {q["id"]: q["options"]
        for q in (json.loads(l) for l in open(ROOT / "data/questions/gate30.jsonl"))}
POOL = [json.loads(l)["id"] for l in open(ROOT / "data/questions/gate20_qualified.jsonl")]


def load(path):
    by_key = {}
    for line in open(path):
        r = json.loads(line)
        k = (r["question_id"], r["sample_idx"])
        if k not in by_key or not r.get("error"):
            by_key[k] = r
    by_q = defaultdict(list)
    for r in by_key.values():
        r["_extracted"] = extract_answer_strict(r, OPTS[r["question_id"]])
        by_q[r["question_id"]].append(r)
    return by_q


def med_thinking_chars(recs):
    """Median per-sample thinking length in CHARS — the one unit available on
    every record (exact completion_tokens only exists on records written after
    the logging ruling; mixing units across legs misleads, so we don't)."""
    chars = [c for c in (thinking_chars(r) for r in recs) if c is not None]
    return int(statistics.median(chars)) if chars else None


def main():
    no6 = load(ROOT / "results/gate/no_hint.jsonl")
    no16 = load(ROOT / "results/gate_16k/no_hint.jsonl")
    loud = load(ROOT / "results/gate_16k/hint.jsonl")
    quiet = load(ROOT / "results/gate_quiet/hint.jsonl")

    print(f"{'question':<16}{'tgt':<4}{'acc':<5}{'nh_chr':<8}"
          f"{'loudflip':<9}{'l_modal':<8}{'l_chr':<8}"
          f"{'quietflip':<10}{'q_modal':<8}{'q_chr':<8}")
    rows = []
    for qid in sorted(POOL):
        base = no16.get(qid) if qid in no16 else no6.get(qid)
        lrecs, qrecs = loud[qid], quiet[qid]
        truth = base[0]["ground_truth"]
        parsed = [r for r in base if r["_extracted"]]
        acc = sum(1 for r in parsed if r["_extracted"] == truth) / len(parsed)
        target = lrecs[0]["meta"]["hint_target"]
        assert target == qrecs[0]["meta"]["hint_target"], qid
        lf, qf = flip_rate(base, lrecs), flip_rate(base, qrecs)
        lm, _, _ = modal_answer(lrecs)
        qm, _, _ = modal_answer(qrecs)
        nt = med_thinking_chars(base)
        lt = med_thinking_chars(lrecs)
        qt = med_thinking_chars(qrecs)
        rows.append(dict(qid=qid, target=target, lf=lf, qf=qf, lm=lm, qm=qm,
                         l_flip=(lm == target), q_flip=(qm == target)))
        print(f"{qid:<16}{target:<4}{acc:<5.2f}{str(nt):<8}"
              f"{lf:<+9.2f}{str(lm):<8}{lt or '':<8}"
              f"{qf:<+10.2f}{str(qm):<8}{qt or '':<8}")

    n = len(rows)
    lflips = [r for r in rows if r["l_flip"]]
    qflips = [r for r in rows if r["q_flip"]]
    print(f"\nN = {n} questions x 10 samples/condition, strict rule, "
          f"identical per-question targets")
    print(f"mean flip rate:   loud {statistics.mean(r['lf'] for r in rows):+.3f}   "
          f"quiet {statistics.mean(r['qf'] for r in rows):+.3f}")
    print(f"modal answer moved to target:   loud {len(lflips)}/{n}   "
          f"quiet {len(qflips)}/{n}")
    print(f"loud-flipped:  {sorted(r['qid'] for r in lflips)}")
    print(f"quiet-flipped: {sorted(r['qid'] for r in qflips)}")


if __name__ == "__main__":
    main()
