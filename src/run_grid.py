"""run_grid.py — the single harness entrypoint.

Generic batch sampler against an OpenAI-compatible endpoint (vLLM).
GENERIC parts are complete. PROJECT-SPECIFIC parts are marked
TODO(clocked) and must only be implemented during clocked hours.

Usage:
    python src/run_grid.py \
        --questions data/questions/pool.jsonl \
        --condition no_hint \
        --n-samples 20 \
        --model <served-model-name> \
        --endpoint http://localhost:8000/v1 \
        --out results/

Design rules (from CLAUDE.md):
- Batch-first: scaling N is a config change, not new code.
- Deterministic seeds, resumable, every raw completion saved.
- Nothing in results/ is ever deleted or overwritten.
"""

import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path

from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Question loading (generic)
# ---------------------------------------------------------------------------

def load_questions(path: str) -> list[dict]:
    """Load MCQ pool: one JSON object per line.

    Expected fields: id, question, options (dict letter->text), answer (letter).
    """
    questions = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    for q in questions:
        for field in ("id", "question", "options", "answer"):
            assert field in q, f"question missing field {field}: {q}"
    return questions


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_prompt(question: dict, condition: str, condition_cfg: dict) -> list[dict]:
    """Return chat messages for one question under one condition.

    GENERIC scaffold only. The actual condition logic is project-specific.

    TODO(clocked): implement conditions:
      - no_hint            : plain MCQ prompt
      - hint@<option>      : MCQ + hint text from data/hints/ config,
                             templated toward <option>
      - paraphrase_<k>     : paraphrased variant k of the question
      - self_report_probe  : follow-up asking what influenced the answer
    """
    raise NotImplementedError("TODO(clocked): condition logic is clocked work")


# ---------------------------------------------------------------------------
# Sampling loop (generic, complete)
# ---------------------------------------------------------------------------

def sample_key(question_id: str, condition: str, sample_idx: int) -> str:
    return f"{question_id}::{condition}::{sample_idx}"


def load_done_keys(out_path: Path) -> set[str]:
    """Resumability: skip (question, condition, sample) triples already on disk."""
    done = set()
    if out_path.exists():
        with open(out_path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done.add(sample_key(rec["question_id"], rec["condition"], rec["sample_idx"]))
                except (json.JSONDecodeError, KeyError):
                    continue  # partial line from a crash; will be re-run
    return done


async def run_one(client, model, messages, temperature, max_tokens, seed):
    t0 = time.time()
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
    )
    return {
        "raw_text": resp.choices[0].message.content,
        "finish_reason": resp.choices[0].finish_reason,
        "latency_s": round(time.time() - t0, 2),
    }


async def run_grid(args):
    questions = load_questions(args.questions)
    out_path = Path(args.out) / f"{args.condition}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = load_done_keys(out_path)
    print(f"[run_grid] {len(questions)} questions x {args.n_samples} samples, "
          f"{len(done)} already done, condition={args.condition}")

    client = AsyncOpenAI(base_url=args.endpoint, api_key="EMPTY")
    condition_cfg = {}
    if args.condition_config:
        with open(args.condition_config) as f:
            condition_cfg = json.load(f)

    sem = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()

    async def worker(q, sidx):
        key = sample_key(q["id"], args.condition, sidx)
        if key in done:
            return
        # deterministic per-sample seed derived from the triple
        seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
        messages = build_prompt(q, args.condition, condition_cfg)
        async with sem:
            try:
                result = await run_one(client, args.model, messages,
                                       args.temperature, args.max_tokens, seed)
                error = None
            except Exception as e:  # logged, never silently dropped
                result, error = None, repr(e)
        record = {
            "question_id": q["id"],
            "condition": args.condition,
            "sample_idx": sidx,
            "seed": seed,
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "messages": messages,
            "ground_truth": q["answer"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "result": result,
            "error": error,
        }
        async with write_lock:
            with open(out_path, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    tasks = [worker(q, sidx) for q in questions for sidx in range(args.n_samples)]
    await asyncio.gather(*tasks)
    print(f"[run_grid] done -> {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--questions", required=True)
    p.add_argument("--condition", required=True)
    p.add_argument("--condition-config", default=None,
                   help="JSON config for the condition, e.g. a hint spec from data/hints/")
    p.add_argument("--n-samples", type=int, default=20)
    p.add_argument("--model", required=True)
    p.add_argument("--endpoint", default="http://localhost:8000/v1")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--out", default="results/")
    args = p.parse_args()
    asyncio.run(run_grid(args))


if __name__ == "__main__":
    main()
