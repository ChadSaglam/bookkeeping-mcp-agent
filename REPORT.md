# Evaluation report: bookkeeping-mcp-agent

Synthetic data only. Small samples. Not accounting or tax advice.

## Question

A fine-tuned 0.5B model suggests a Swiss SME account for one invoice line. The invoice text is
untrusted. Can simple deterministic rules (keywords, length cap, VAT and amount checks) tell a human
which suggestions need attention, and can an MCP agent use them to build a review queue?

## Setup

- MCP server (FastMCP, stdio) with three tools: lookup_account, check_vat, review_invoice_line.
- review_invoice_line returns a suggested account, needs_human and reasons. It never books anything.
- agent.py is a local MCP client. Every line becomes a draft with status draft_pending_human.
  needs_human only sets the queue priority.

## Results

| Test | Result |
|---|---|
| Clean test lines flagged by text rules | 0 / 74 |
| Known attacks (rules were written from them) | 30 / 30 flagged |
| Held-out long attacks, keyword rules only | 22 / 50 changed the account, not flagged |
| Held-out long attacks, plus length cap 55 | 3 / 50 (the cap fired on length, not content) |
| Short attacks, 12 suffixes on 30 clean lines | 210 / 360 changed the account, not flagged; 166 / 360 moved to 6600 |
| Agent eval, clean test lines | 5 / 56 wrong; 4 / 54 wrong among normal-priority drafts |
| Agent eval, 8 fresh suffixes (352 cases) | 152 / 352 wrong (43%); 85 wrongly moved to 6600; 1 flagged; 151 / 351 normal-priority drafts wrong |
| Ablation on 74 held-out-vendor rows: amount and VAT neutralized or shuffled | 69 / 74 real, 68 / 74 neutral, 68 / 74 shuffled; 1 and 3 predictions changed |
| Out-of-phrase test: 36 hand-written lines, unseen vendors and wording | 17 / 36 = 47.2% (95% interval 32-63%); 19 / 36 with amount and VAT neutralized; amount+VAT lookup 6 / 36 (chance) |

## Findings

1. Keyword rules written from known attacks did not generalize to new attacks.
2. The length cap looked effective only because the long attacks were long. Short suffixes such as
   "(advertising)", "- Werbung" or "pour publicité" passed it and steered the model in most cases.
3. The model treats words like "advertising" as content, not as text to ignore. The effect is
   language independent. Errors go to 6600 but also to 6510, 6570 and 6500.
4. In the agent, needs_human is not a safety label. A normal-priority draft was wrong 7% of the time
   on clean lines and 43% under short suffix attacks.
5. The design therefore treats every suggestion as a draft. The human decision is the safeguard.

## Limits

- The 56 test rows were not used for training (0 overlap with train.jsonl). 44 of them are in the
  validation file and 12 in the hard test file of the model's data split, so they are not fully
  independent of model development.
- Synthetic data. The test set has 56 rows, so the 352 attacked cases are about 44 base lines with
  up to 8 suffixes each. They are not independent.
- "Wrong" is measured against the original label. For suffixes with real content (for example
  "Marketingkosten") the right account can be debatable.
- The short-attack suffixes and the fresh suffixes were written after earlier results, so they are
  development sets, not blind tests. Rules tuned on them need a new held-out set.
- Attack-attributable error is roughly the attacked rate minus the clean rate, but no paired
  per-line baseline was computed.

## Not done

- Multi-view consistency check (rerun on the vendor name only, flag disagreements).
- Model confidence scores.
- Training with attack examples. Note that "Werbung" is a legitimate word in real line items.

## Reproduce

    uv sync
    uv run python eval_guardrails.py
    uv run python eval_heldout.py
    uv run python eval_short.py
    uv run python agent.py
    uv run python eval_agent.py
    uv run python eval_ablation.py
    uv run python eval_ood.py

Raw per-case results: eval_agent_results.json.
