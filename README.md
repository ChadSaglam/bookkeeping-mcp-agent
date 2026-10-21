# Bookkeeping MCP Server

A local MCP server (FastMCP, stdio) that exposes a fine-tuned 0.5B bookkeeping model
as tools, with deterministic guardrails. It never books anything: it only suggests an
account and says whether a human must check the line. Synthetic data only.

## Tools

- lookup_account: name of an account in the test chart
- check_vat: OK or FLAG for a VAT rate
- review_invoice_line: suggested account plus needs_human and reasons

## Guardrails

A line goes to a human if the VAT rate is not allowed, the amount is above CHF 1000,
the text is unusually long or contains instruction-like wording, or the model returns
no valid account. The model output is parsed to a 4-digit account in the chart,
so injected text cannot produce arbitrary output.

## Run

    uv sync
    uv run python test_tools.py
    uv run python eval_guardrails.py

Needs the 8-bit model from https://huggingface.co/ChadSaglam/swiss-bookkeeping-qwen-lora-mlx-8bit
(set MODEL_PATH in core.py), Apple Silicon.

## Known limits

Rules do not use model uncertainty: a confidently wrong account on a clean line is not flagged.
Keyword list is English only. Not accounting or tax advice.
