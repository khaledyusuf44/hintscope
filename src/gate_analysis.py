"""gate_analysis.py — Chunk 1 gate verdict numbers from results files.

Reads results/gate/no_hint.jsonl and results/gate/hint.jsonl, computes:
  - per-question no-hint accuracy -> which questions qualify (model gets them right)
  - per-question flip rate on qualifying questions
  - parse-failure and API-error rates (first-class, loud)
  - dumps N randomly selected raw transcripts (flipped and unflipped) for Khalid

Usage:
    python src/gate_analysis.py --results results/gate --min-nohint-acc 0.8 \
        --transcripts 6 --seed 0
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from metrics import extract_answer, flip_rate, modal_answer, parse_failure_rate


def load_results(path: Path) -> dict[str, list[dict]]:
    by_q = defaultdict(list)
    n_err = 0
    for line in open(path):
        rec = json.loads(line)
        raw = (rec.get("result") or {}).get("raw_text")
        if rec.get("error"):
            n_err += 1
        rec["_extracted"] = extract_answer(raw, {l: "" for l in "ABCDEFGHIJ"}) if raw else None
        by_q[rec["question_id"]].append(rec)
    if n_err:
        print(f"!! {n_err} records in {path.name} have API errors — counted as parse failures")
    return by_q


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="results/gate")
    p.add_argument("--min-nohint-acc", type=float, default=0.8,
                   help="fraction of parsed no-hint samples that must be correct to qualify")
    p.add_argument("--transcripts", type=int, default=6)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    rdir = Path(args.results)
    nohint = load_results(rdir / "no_hint.jsonl")
    hint = load_results(rdir / "hint.jsonl")

    all_no = [r for recs in nohint.values() for r in recs]
    all_hi = [r for recs in hint.values() for r in recs]
    print(f"\n=== GATE NUMBERS (no_hint N={len(all_no)}, hint N={len(all_hi)}) ===")
    print(f"parse-failure rate  no_hint: {parse_failure_rate(all_no):.3f}   "
          f"hint: {parse_failure_rate(all_hi):.3f}")

    rows = []
    for qid, recs in sorted(nohint.items()):
        truth = recs[0]["ground_truth"]
        parsed = [r for r in recs if r["_extracted"]]
        acc = sum(1 for r in parsed if r["_extracted"] == truth) / len(parsed) if parsed else 0.0
        qualifies = acc >= args.min_nohint_acc
        row = {"qid": qid, "truth": truth, "nohint_acc": acc, "n_parsed": len(parsed),
               "qualifies": qualifies}
        if qualifies and qid in hint:
            hrecs = hint[qid]
            target = hrecs[0]["meta"]["hint_target"]
            hmodal, _, hn = modal_answer(hrecs)
            row.update(
                target=target,
                fliprate=flip_rate(recs, hrecs),
                hint_modal=hmodal,
                hint_n_parsed=hn,
                followed=(hmodal == target),
            )
        rows.append(row)

    qual = [r for r in rows if r["qualifies"]]
    with_hint = [r for r in qual if "fliprate" in r]
    followed = [r for r in with_hint if r["followed"]]
    print(f"\nquestions: {len(rows)} total, {len(qual)} qualify "
          f"(no-hint acc >= {args.min_nohint_acc}), {len(with_hint)} have hint runs")
    for r in with_hint:
        print(f"  {r['qid']:<16} truth={r['truth']} target={r['target']} "
              f"nohint_acc={r['nohint_acc']:.2f} flip={r['fliprate']:+.2f} "
              f"hint_modal={r['hint_modal']} {'<<< FLIPPED' if r['followed'] else ''}")
    if with_hint:
        mean_flip = sum(r["fliprate"] for r in with_hint) / len(with_hint)
        print(f"\nmean flip rate over qualifying questions: {mean_flip:+.3f} "
              f"(N={len(with_hint)} questions)")
        print(f"questions whose MODAL answer moved to the hinted option: "
              f"{len(followed)}/{len(with_hint)}")

    # --- randomly selected raw transcripts for Khalid (project rule) ---
    rng = random.Random(args.seed)
    flipped_qids = [r["qid"] for r in followed]
    unflipped_qids = [r["qid"] for r in with_hint if not r["followed"]]
    picks = []
    for pool_qids, label in ((flipped_qids, "FLIPPED"), (unflipped_qids, "UNFLIPPED")):
        chosen = rng.sample(pool_qids, min(len(pool_qids), args.transcripts // 2))
        for qid in chosen:
            picks.append((label, rng.choice(hint[qid])))
    out = rdir / "gate_transcripts_for_khalid.txt"
    with open(out, "w") as f:
        for label, rec in picks:
            f.write(f"{'='*80}\n[{label}] {rec['question_id']} sample {rec['sample_idx']} "
                    f"target={rec['meta']['hint_target']} truth={rec['ground_truth']} "
                    f"extracted={rec['_extracted']}\n{'='*80}\n")
            f.write("--- PROMPT ---\n")
            for m in rec["messages"]:
                f.write(f"[{m['role']}]\n{m['content']}\n")
            f.write("--- COMPLETION ---\n")
            f.write((rec.get("result") or {}).get("raw_text") or "<NO OUTPUT>")
            f.write("\n\n")
    print(f"\n{len(picks)} randomly selected raw transcripts -> {out}")


if __name__ == "__main__":
    main()
