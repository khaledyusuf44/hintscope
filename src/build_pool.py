"""build_pool.py — build data/questions/pool.jsonl from MMLU-Pro (unclocked, generic data prep).

Pulls MCQ reasoning questions from TIGER-Lab/MMLU-Pro (test split), stratified
across categories, deterministic seed. Output schema matches run_grid.load_questions:
    id, question, options (dict letter->text), answer (letter)
plus provenance fields: category, source.

Usage:
    python src/build_pool.py --n 400 --seed 0 --out data/questions/pool.jsonl
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from datasets import load_dataset

LETTERS = "ABCDEFGHIJ"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=400)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="data/questions/pool.jsonl")
    args = p.parse_args()

    ds = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
    by_cat = defaultdict(list)
    for row in ds:
        opts = [o for o in row["options"] if o and o.strip().upper() != "N/A"]
        # keep only questions whose answer index survives option filtering and
        # which have >=4 options (need multiple wrong options for cue moves)
        if len(opts) < 4 or row["answer_index"] >= len(row["options"]):
            continue
        if row["options"][row["answer_index"]] not in opts:
            continue
        by_cat[row["category"]].append(row)

    rng = random.Random(args.seed)
    cats = sorted(by_cat)
    per_cat = max(1, args.n // len(cats))
    picked = []
    for c in cats:
        rows = sorted(by_cat[c], key=lambda r: r["question_id"])
        rng.shuffle(rows)
        picked.extend(rows[:per_cat])
    rng.shuffle(picked)
    picked = picked[: args.n]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for row in picked:
            opts = [o for o in row["options"] if o and o.strip().upper() != "N/A"]
            answer_text = row["options"][row["answer_index"]]
            options = {LETTERS[i]: o for i, o in enumerate(opts)}
            answer_letter = LETTERS[opts.index(answer_text)]
            rec = {
                "id": f"mmlupro-{row['question_id']}",
                "question": row["question"],
                "options": options,
                "answer": answer_letter,
                "category": row["category"],
                "source": "TIGER-Lab/MMLU-Pro:test",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[build_pool] wrote {len(picked)} questions -> {out}")
    counts = defaultdict(int)
    for row in picked:
        counts[row["category"]] += 1
    for c in sorted(counts):
        print(f"  {c}: {counts[c]}")


if __name__ == "__main__":
    main()
