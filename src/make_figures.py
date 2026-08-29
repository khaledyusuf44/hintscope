"""make_figures.py — F1/F2/F3 for the write-up, generated from results files.

F1: three-way per-question flip comparison + means (headline figure)
F2: thinking-length distributions by condition
F3: self-report outcomes by condition (hand-adjudicated where available,
    keyword judge elsewhere — marked in caption)

Usage: python src/make_figures.py   (writes PNGs to figures/)
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from metrics import extract_answer_strict, flip_rate, thinking_chars

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

OPTS = {q["id"]: q["options"]
        for q in (json.loads(l) for l in open(ROOT / "data/questions/gate30.jsonl"))}
POOL = sorted(json.loads(l)["id"]
              for l in open(ROOT / "data/questions/gate20_qualified.jsonl"))

COND_FILES = {"loud": "results/gate_16k/hint.jsonl",
              "quiet": "results/gate_quiet/hint.jsonl",
              "neutral": "results/gate_neutral/hint.jsonl"}
COND_LABELS = {"loud": "loud (professor)", "quiet": "quiet (grader_note)",
               "neutral": "neutral (metadata)"}
COLORS = {"loud": "#d62728", "quiet": "#1f77b4", "neutral": "#7f7f7f"}


def load_leg(rel):
    by_key = {}
    for line in open(ROOT / rel):
        r = json.loads(line)
        k = (r["question_id"], r["sample_idx"])
        if k not in by_key or not r.get("error"):
            by_key[k] = r
    by_q = defaultdict(list)
    for r in by_key.values():
        r["_extracted"] = extract_answer_strict(r, OPTS[r["question_id"]])
        by_q[r["question_id"]].append(r)
    return by_q


def main():
    no6 = load_leg("results/gate/no_hint.jsonl")
    no16 = load_leg("results/gate_16k/no_hint.jsonl")
    legs = {c: load_leg(f) for c, f in COND_FILES.items()}
    base = {q: (no16[q] if q in no16 else no6[q]) for q in POOL}

    flips = {c: [flip_rate(base[q], legs[c][q]) for q in POOL] for c in legs}

    # ---------------- F1 ----------------
    fig, ax = plt.subplots(figsize=(11, 4.5))
    x = np.arange(len(POOL))
    w = 0.27
    for i, c in enumerate(("loud", "quiet", "neutral")):
        ax.bar(x + (i - 1) * w, flips[c], w, label=COND_LABELS[c],
               color=COLORS[c], alpha=0.85)
        m = statistics.mean(flips[c])
        ax.axhline(m, color=COLORS[c], ls="--", lw=1)
        ax.text(len(POOL) - 0.3, m + 0.015, f"mean {m:+.2f}",
                color=COLORS[c], fontsize=8, ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels([q.replace("mmlupro-", "") for q in POOL],
                       rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("question (MMLU-Pro id)")
    ax.set_ylabel("flip rate  P(cue option | cue) − P(cue option | no hint)")
    ax.set_title("F1 — Hint-induced answer flipping by cue style (identical per-question targets)")
    ax.legend(fontsize=8)
    ax.set_ylim(-0.1, 1.1)
    fig.text(0.01, 0.005,
             "N = 20 questions x 10 samples/condition (Qwen3.5-9B, temp 0.7, 16k cap; "
             "strict rule: truncated samples never count; parsed-only denominators). "
             "Dashed lines: condition means.", fontsize=7)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "F1_flip_by_cue_style.png", dpi=200)

    # ---------------- F2 ----------------
    fig, ax = plt.subplots(figsize=(7, 4.5))
    groups = [("no hint", [c for q in POOL for c in
                           (thinking_chars(r) for r in base[q]) if c is not None])]
    groups += [(COND_LABELS[c], [v for q in POOL for v in
                                 (thinking_chars(r) for r in legs[c][q]) if v is not None])
               for c in ("loud", "quiet", "neutral")]
    parts = ax.violinplot([g[1] for g in groups], showmedians=True)
    for pc, color in zip(parts["bodies"], ["#2ca02c"] + [COLORS[c] for c in ("loud", "quiet", "neutral")]):
        pc.set_facecolor(color)
        pc.set_alpha(0.6)
    ax.set_xticks(range(1, len(groups) + 1))
    ax.set_xticklabels([f"{g[0]}\n(n={len(g[1])})" for g in groups], fontsize=8)
    ax.set_ylabel("thinking length (characters before final </think>)")
    ax.set_title("F2 — Thinking length by condition")
    fig.text(0.01, 0.015,
             "Same 20 questions in every condition; 10 samples each (n=200/violin). No-hint pools the\n"
             "6k-cap run (13 qs) and 16k-cap re-run (7 qs); cue conditions all 16k cap. Horizontal\n"
             "bar: median. Truncated samples included (their length is still measured).", fontsize=7)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(FIG / "F2_thinking_length.png", dpi=200)

    # ---------------- F3 ----------------
    adj = json.load(open(ROOT / "results/adjudication_final.json"))
    quiet_counts = {"CONFESSED": 0, "HID_IT": 0, "HONEST_REFUSAL": 0, "UNSURE": 0}
    for r in adj:
        quiet_counts[r["verdict"]] += 1
    # loud: 19 finished, keyword ack 19/19; neutral: 74 finished, keyword ack 73
    KW_ACK = "keyword-ack (no hand adjudication)"
    bars = {
        "loud (professor)\nn=19": {KW_ACK: 19, "keyword-non-ack": 0},
        "quiet (grader_note)\nn=133": {KW_ACK: 88, **quiet_counts},
        "neutral (metadata)\nn=74": {KW_ACK: 73, "keyword-non-ack": 1},
    }
    cat_colors = {"CONFESSED": "#2ca02c", "HID_IT": "#d62728",
                  "HONEST_REFUSAL": "#1f77b4", "UNSURE": "#ff7f0e",
                  KW_ACK: "#98df8a", "keyword-non-ack": "#c7c7c7"}
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    seen = set()
    for xi, (label, cats) in enumerate(bars.items()):
        bottom = 0
        total = sum(cats.values())
        for cat, n in cats.items():
            if n == 0:
                continue
            lbl = cat if cat not in seen else None
            seen.add(cat)
            ax.bar(xi, n / total, 0.55, bottom=bottom,
                   color=cat_colors[cat], label=lbl,
                   edgecolor="white", linewidth=0.5)
            if n / total > 0.04:
                ax.text(xi, bottom + n / total / 2, str(n), ha="center",
                        va="center", fontsize=8)
            bottom += n / total
    ax.set_xticks(range(len(bars)))
    ax.set_xticklabels(list(bars), fontsize=8)
    ax.set_ylabel("fraction of finished probe responses")
    ax.set_title("F3 — Self-report outcomes by cue style")
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.text(0.01, 0.02,
             "Quiet: 45/133 hand-adjudicated (solid categories; verdicts from final-answer\n"
             "channel only), remaining 88 keyword-judged (pale green). Loud & neutral: keyword\n"
             "judge only (on quiet ground truth the judge showed FP 5/16, FN 5/29).\n"
             "Ns are finished (non-truncated) probe responses.",
             fontsize=6.5)
    fig.tight_layout(rect=(0, 0.11, 0.80, 1))
    fig.savefig(FIG / "F3_selfreport_outcomes.png", dpi=200)
    print("wrote F1, F2, F3 ->", FIG)


if __name__ == "__main__":
    main()
