#!/usr/bin/env bash
# One-time project setup (all unclocked). Run from the project root.
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
git init -q 2>/dev/null || true
git add -A
git commit -q -m "hintscope: initial project skeleton" || true
echo "Setup done. Next: serve the model with vLLM on the rented GPU,"
echo "then build data/questions/pool.jsonl from an established MCQ benchmark."
