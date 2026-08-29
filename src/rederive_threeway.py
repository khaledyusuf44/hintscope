"""rederive_threeway.py — SECOND INDEPENDENT DERIVATION of the three-way flip
table. Written from scratch: does not import metrics.py, gate_compare.py, or
gate_threeway.py, and uses a deliberately different answer-extraction
implementation. Writes per-cell numbers to results/rederive_cells.json and
per-sample extractions to results/rederive_samples.json for comparison by a
separate harness.

Extraction logic (independent design):
- a sample only counts if its finish_reason field equals "stop" (checked
  directly on the JSON record);
- take the text after the FINAL "</think>" (whole text if absent), split into
  lines, scan from the BOTTOM up for the first line containing the word
  "answer" (case-insensitive); within that line, take the LAST standalone
  A-J character (bounded by non-letters) that is one of the question's
  options. No second fallback pattern.

Flip per (question, condition): (#samples on target / #records) minus the
same ratio in that question's no-hint block — counts computed with plain
loops, denominators = ALL records (parse failures count the denominator),
which is a DIFFERENT convention from the original (parsed-only denominator);
the harness compares like-for-like using the dumped per-sample extractions,
and the cell values are expected to differ where parse failures exist.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

QUESTIONS = {}
for line in open(ROOT / "data/questions/gate30.jsonl"):
    q = json.loads(line)
    QUESTIONS[q["id"]] = q
POOL = [json.loads(line)["id"]
        for line in open(ROOT / "data/questions/gate20_qualified.jsonl")]

FILES = {
    "no_hint_6k": "results/gate/no_hint.jsonl",
    "no_hint_16k": "results/gate_16k/no_hint.jsonl",
    "loud": "results/gate_16k/hint.jsonl",
    "quiet": "results/gate_quiet/hint.jsonl",
    "neutral": "results/gate_neutral/hint.jsonl",
}


def pull_answer(record):
    result = record.get("result")
    if not result or result.get("finish_reason") != "stop":
        return None
    text = result.get("raw_text") or ""
    tail = text.split("</think>")[-1]
    valid = set(QUESTIONS[record["question_id"]]["options"])
    for line in reversed(tail.splitlines()):
        if re.search(r"answer", line, re.IGNORECASE):
            letters = re.findall(r"(?<![A-Za-z])([A-J])(?![A-Za-z])", line)
            letters = [x for x in letters if x in valid]
            if letters:
                return letters[-1]
            return None
    return None


def read_leg(relpath):
    per_key = {}
    for line in open(ROOT / relpath):
        rec = json.loads(line)
        k = (rec["question_id"], rec["sample_idx"])
        if k in per_key and per_key[k].get("error") is None:
            continue
        per_key[k] = rec
    grouped = {}
    for rec in per_key.values():
        grouped.setdefault(rec["question_id"], []).append(rec)
    return grouped


def main():
    legs = {name: read_leg(path) for name, path in FILES.items()}
    cells = {}
    samples = {}
    for qid in POOL:
        base_leg = "no_hint_16k" if qid in legs["no_hint_16k"] else "no_hint_6k"
        base = legs[base_leg][qid]
        target = None
        for cond in ("loud", "quiet", "neutral"):
            for rec in legs[cond][qid]:
                t = rec["meta"]["hint_target"]
                assert target in (None, t), f"target mismatch {qid}"
                target = t
        base_on_target = sum(1 for r in base if pull_answer(r) == target)
        base_ratio = base_on_target / len(base)
        for cond in ("loud", "quiet", "neutral"):
            recs = legs[cond][qid]
            on_target = sum(1 for r in recs if pull_answer(r) == target)
            cells[f"{qid}|{cond}"] = round(on_target / len(recs) - base_ratio, 4)
        for cond in (base_leg, "loud", "quiet", "neutral"):
            for r in sorted(legs[cond][qid], key=lambda x: x["sample_idx"]):
                samples[f"{qid}|{cond}|{r['sample_idx']}"] = pull_answer(r)

    json.dump(cells, open(ROOT / "results/rederive_cells.json", "w"), indent=0)
    json.dump(samples, open(ROOT / "results/rederive_samples.json", "w"), indent=0)
    for cond in ("loud", "quiet", "neutral"):
        vals = [v for k, v in cells.items() if k.endswith(cond)]
        print(f"{cond}: mean flip {sum(vals)/len(vals):+.3f} over {len(vals)} questions")
    print(f"wrote {len(cells)} cells, {len(samples)} sample extractions")


if __name__ == "__main__":
    main()
