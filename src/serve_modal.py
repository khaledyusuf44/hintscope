"""serve_modal.py — vLLM OpenAI-compatible server for Qwen3.5-9B on Modal (unclocked infra).

Deploy:  modal deploy src/serve_modal.py
Endpoint: printed on deploy; pass "<url>/v1" as --endpoint to run_grid.py.

Notes:
- vLLM nightly is required for the qwen3_5 architecture (per model card).
- NO --reasoning-parser: we want the raw <think>...</think> block kept inline
  in message.content so every raw completion is saved verbatim (project rule).
- GPU: A10G 24GB — largest tier the account can use without a payment method
  (L40S is gated). bf16 weights ~19.3GB leave ~3.5GB KV at 0.95 util, so
  max-model-len is capped at 16384 and max-num-seqs at 8. Tight but sufficient
  for the gate. If Khalid adds a payment method, switch gpu to "L40S" and
  raise max-model-len/max-num-seqs for the fat resampling chunks.
"""

import subprocess

import modal

MODEL = "Qwen/Qwen3.5-9B"
PORT = 8000

app = modal.App("hintscope-vllm")

# CUDA 13 base image: the vllm nightly wheel links libcudart.so.13, which
# debian_slim lacks (cold start died with ImportError there).
image = (
    modal.Image.from_registry("nvidia/cuda:13.0.1-devel-ubuntu24.04", add_python="3.12")
    .pip_install("uv")
    .run_commands(
        "uv pip install --system --torch-backend=cu130 vllm "
        "--extra-index-url https://wheels.vllm.ai/nightly",
        "uv pip install --system 'huggingface_hub[hf_transfer]'",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_USE_V1": "1"})
)

hf_cache = modal.Volume.from_name("hintscope-hf-cache", create_if_missing=True)


@app.function(
    image=image,
    gpu="L40S",
    timeout=60 * 60 * 24,
    scaledown_window=15 * 60,
    volumes={"/root/.cache/huggingface": hf_cache},
)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=PORT, startup_timeout=30 * 60)
def serve():
    cmd = (
        f"vllm serve {MODEL} --host 0.0.0.0 --port {PORT} "
        "--max-model-len 32768 --gpu-memory-utilization 0.92 --max-num-seqs 32"
    )
    subprocess.Popen(cmd, shell=True)
