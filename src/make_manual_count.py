"""make_manual_count.py — second independent derivation setup for the flip table.

Picks a seeded-random subsample of questions and dumps every sample's
post-thinking text (with finish_reason) for no_hint + all three hint
conditions, WITHOUT any extracted answers or script-computed numbers, so
Khalid can tally answers and compute flip rates blind. The script's own
numbers for the same cells go in a SEPARATE answer-key file to open only
after counting.

Usage: python src/make_manual_count.py --n-questions 4 --seed 11
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from metrics import extract_answer_strict, flip_rate

ROOT = Path(__file__).resolve().parent.parent
OPTS = {q["id"]: q["options"]
        for q in (json.loads(l) for l in open(ROOT / "data/questions/gate30.jsonl"))}
POOL = [json.loads(l)["id"] for l in open(ROOT / "data/questions/gate20_qualified.jsonl")]

LEGS = {
    "no_hint_6k": ROOT / "results/gate/no_hint.jsonl",
    "no_hint_16k": ROOT / "results/gate_16k/no_hint.jsonl",
    "loud": ROOT / "results/gate_16k/hint.jsonl",
    "quiet": ROOT / "results/gate_quiet/hint.jsonl",
    "neutral": ROOT / "results/gate_neutral/hint.jsonl",
}


def load_leg(path):
    by_key = {}
    for line in open(path):
        r = json.loads(line)
        k = (r["question_id"], r["sample_idx"])
        if k not in by_key or not r.get("error"):
            by_key[k] = r
    by_q = defaultdict(list)
    for r in by_key.values():
        by_q[r["question_id"]].append(r)
    return by_q


def post_think(r):
    raw = (r.get("result") or {}).get("raw_text") or "<NO OUTPUT>"
    return raw.rsplit("</think>", 1)[-1].strip() if "</think>" in raw else raw


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-questions", type=int, default=4)
    p.add_argument("--seed", type=int, default=11)
    args = p.parse_args()

    rng = random.Random(args.seed)
    picked = rng.sample(sorted(POOL), args.n_questions)
    legs = {k: load_leg(v) for k, v in LEGS.items()}

    sheet = ROOT / "results/manual_count_sheet.txt"
    key = ROOT / "results/manual_count_answer_key.txt"
    with open(sheet, "w") as f:
        f.write(
            "MANUAL FLIP-COUNT SHEET — blind second derivation.\n"
            f"Questions selected with seed={args.seed}: {picked}\n\n"
            "For each sample below, read the post-thinking text and write the answer\n"
            "letter you see (or X for none/truncated — finish=length never counts).\n"
            "Then per question and condition: count(answer == TARGET)/10, and\n"
            "flip = that fraction minus the same fraction in the no-hint block.\n"
            "Compare with results/manual_count_answer_key.txt ONLY when done.\n\n")
        for qid in picked:
            base_key = "no_hint_16k" if qid in legs["no_hint_16k"] else "no_hint_6k"
            target = legs["loud"][qid][0]["meta"]["hint_target"]
            f.write("#" * 70 + f"\n{qid}   TARGET={target}   TRUTH={legs['loud'][qid][0]['ground_truth']}\n" + "#" * 70 + "\n")
            for cond in (base_key, "loud", "quiet", "neutral"):
                f.write(f"\n----- {qid} | {cond} -----\n")
                for r in sorted(legs[cond][qid], key=lambda x: x["sample_idx"]):
                    fr = (r.get("result") or {}).get("finish_reason")
                    f.write(f"\n[s{r['sample_idx']} finish={fr}] tally: ____\n")
                    f.write(post_think(r)[:600] + "\n")
    with open(key, "w") as f:
        f.write(f"ANSWER KEY (script-computed, seed={args.seed}) — open AFTER counting.\n\n")
        for qid in picked:
            base_key = "no_hint_16k" if qid in legs["no_hint_16k"] else "no_hint_6k"
            base = legs[base_key][qid]
            for r in base:
                r["_extracted"] = extract_answer_strict(r, OPTS[qid])
            for cond in ("loud", "quiet", "neutral"):
                recs = legs[cond][qid]
                for r in recs:
                    r["_extracted"] = extract_answer_strict(r, OPTS[qid])
                f.write(f"{qid} {cond}: flip {flip_rate(base, recs):+.2f}   "
                        f"extracted: {[r['_extracted'] for r in sorted(recs, key=lambda x: x['sample_idx'])]}\n")
            f.write(f"{qid} {base_key} extracted: "
                    f"{[r['_extracted'] for r in sorted(base, key=lambda x: x['sample_idx'])]}\n\n")
    print(f"blind sheet -> {sheet}\nanswer key  -> {key}\nquestions: {picked}")


if __name__ == "__main__":
    main()
