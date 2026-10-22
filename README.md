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
    uv run python agent.py
    uv run python eval_agent.py
    uv run python eval_ablation.py
    uv run python eval_ood.py

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
| Agent eval, clean test lines (56) | 5 / 56 wrong account; 2 flagged; 4 / 54 wrong among normal-priority drafts |
| Agent eval, 8 fresh suffixes on non-advertising test lines (352 cases) | 152 / 352 wrong (43%); 85 wrongly moved to 6600; 1 flagged; 151 / 351 normal-priority drafts wrong |
| Ablation on 74 held-out-vendor rows: amount and VAT neutralized or shuffled | 69 / 74 real, 68 / 74 neutral, 68 / 74 shuffled; 1 and 3 predictions changed |
| Out-of-phrase test: 36 hand-written lines, unseen vendors and wording | 17 / 36 = 47.2% (95% interval 32-63%); 19 / 36 with amount and VAT neutralized; amount+VAT lookup 6 / 36 (chance) |

## Agent

agent.py is a local MCP client. It starts the server over stdio, sends every invoice line to
review_invoice_line and writes review_queue.jsonl. Every line has status draft_pending_human.
needs_human only sets the priority (high or normal). It is not a safety label: in the agent eval,
151 of 351 normal-priority drafts under short suffix attacks had the wrong account.

## Known limits

- Keyword and length rules do not generalize. The length cap is not a content defense: it only caught
  long attacks. Short suffixes such as "(advertising)", "- Werbung" or "pour publicité" moved the account
  to 6600 in most cases without a flag (see short-attack row). needs_human does not protect against
  content-based steering.
- The short-attack suffixes were chosen after reading the keyword list, so they are a development set,
  not a blind test. Any rule tuned on them needs a fresh held-out set.
- Small sample: 30 base lines (some from the model's own test file), synthetic data.
- The 56 test rows were not used for training (0 overlap with train.jsonl). 44 of them are in the
  validation file and 12 in the hard test file of the model's data split, so they are not fully
  independent of model development.
- Agent eval: 56 test rows, so the 352 attacked cases are about 44 base lines with up to 8 suffixes each
  and are not independent. "Wrong" is measured against the original label, which can be debatable for
  suffixes with real content (for example "Marketingkosten"). The suffixes were written after the earlier
  short-attack results, so they are not a blind test.
- On 36 hand-written lines with unseen vendors and wording the model scored 47.2% (interval 32-63%), against
  93.2% on the held-out-vendor test. The set was written by the author with the model's weak spots in mind and the
  labels were not independently reviewed, so read it as a lower bound for messy real invoices.
- The fine-tuned model treats words like "advertising" as content, so a line that says so can steer it.
- Rules do not use model uncertainty: a confidently wrong account on a clean line is not flagged.
- The server never books anything; the human decision is the real safeguard.
- Not accounting or tax advice.
