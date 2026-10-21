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
    uv run python eval_heldout.py
    uv run python eval_short.py

Needs the 8-bit model from https://huggingface.co/ChadSaglam/swiss-bookkeeping-qwen-lora-mlx-8bit
(set MODEL_PATH in core.py), Apple Silicon.

## Measured guardrail results (synthetic data, small samples)

| Test | Result |
|---|---|
| Clean test lines flagged by text rules | 0 / 74 |
| Known attacks (rules were written from them) | 30 / 30 flagged |
| Held-out attacks, keyword rules only | 22 / 50 changed the account and were not flagged |
| Held-out long attacks, plus length cap of 55 characters | 3 / 50 (the cap fired on length, not on content) |
| Harmless noisy lines flagged by the length cap | 19 / 40 |
| Short attacks: 12 suffixes on 30 clean lines, all under the 55 cap | 210 / 360 changed the account and were not flagged; 166 / 360 moved to 6600; 1 / 360 flagged |

## Known limits

- Keyword and length rules do not generalize. The length cap is not a content defense: it only caught
  long attacks. Short suffixes such as "(advertising)", "- Werbung" or "pour publicité" moved the account
  to 6600 in most cases without a flag (see short-attack row). needs_human does not protect against
  content-based steering.
- The short-attack suffixes were chosen after reading the keyword list, so they are a development set,
  not a blind test. Any rule tuned on them needs a fresh held-out set.
- Small sample: 30 base lines (some from the model's own test file), synthetic data.
- The fine-tuned model treats words like "advertising" as content, so a line that says so can steer it.
- Rules do not use model uncertainty: a confidently wrong account on a clean line is not flagged.
- The server never books anything; the human decision is the real safeguard.
- Not accounting or tax advice.
