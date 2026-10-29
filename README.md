# Bookkeeping MCP Agent

A local MCP server and client that turn synthetic Swiss SME invoice lines into account-suggestion drafts. The server combines an 8-bit Qwen2.5-0.5B model with deterministic VAT, amount and text checks. It never posts a transaction: every output remains pending human review.

## Resources

| Resource | Link |
|---|---|
| Runtime model used by this repository | [8-bit MLX model](https://huggingface.co/ChadSaglam/swiss-bookkeeping-qwen-lora-mlx-8bit) |
| Full-precision weights and model card | [Swiss Bookkeeping Qwen LoRA](https://huggingface.co/ChadSaglam/swiss-bookkeeping-qwen-lora) |
| Training data, OOD set and validation scripts | [Swiss SME Bookkeeping dataset](https://huggingface.co/datasets/ChadSaglam/swiss-sme-bookkeeping-dataset) |
| Training and model evaluation code | [swiss-bookkeeping-ai](https://github.com/ChadSaglam/swiss-bookkeeping-ai) |
| Protocol used by the server and client | [Model Context Protocol documentation](https://modelcontextprotocol.io/docs/getting-started/intro) |
| Python framework used in this project | [FastMCP documentation](https://gofastmcp.com/getting-started/welcome) |

All data is synthetic. The six-account chart is a simplified test chart, not an official Swiss chart of accounts. This project is not accounting or tax advice.

## How it works

```text
invoice CSV -> local MCP client -> review_invoice_line tool
             -> model suggestion + deterministic checks
             -> review_queue.jsonl (all rows pending human review)
```

The MCP server runs over stdio and exposes three tools:

| Tool | Purpose |
|---|---|
| `lookup_account` | Return an account name, or an error for an unknown code. |
| `check_vat` | Check a VAT rate against 0, 2.6, 3.8 and 8.1 percent. |
| `review_invoice_line` | Return a suggested account, review priority and reasons. |

A line receives high priority when the VAT rate is outside the allowed list, the amount exceeds CHF 1,000, the text triggers a length or instruction-like-wording rule, or the model returns no valid account. Model output is reduced to a four-digit code and accepted only if it exists in the chart.

**`needs_human` is a queue-priority field, not a safety label.** Normal-priority drafts can still be wrong. The measured attack results below show why every row stays a draft.

## Requirements

- macOS on Apple Silicon for the 8-bit MLX runtime
- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)
- About 525 MB for the model download, plus runtime memory

## Quickstart

```bash
git clone https://github.com/ChadSaglam/bookkeeping-mcp-agent.git
cd bookkeeping-mcp-agent
uv sync
uv run python test_tools.py
uv run python agent.py
```

The first model run downloads `ChadSaglam/swiss-bookkeeping-qwen-lora-mlx-8bit` through `mlx-lm`. To use an existing local copy instead:

```bash
export BOOKKEEPING_MODEL_PATH=/absolute/path/to/fused_8bit
uv run python agent.py
```

`agent.py` starts the MCP server, checks that all three tools are available, processes `invoice_lines_demo.csv` and writes `review_queue.jsonl`. A different CSV can be supplied as the first argument:

```bash
uv run python agent.py path/to/invoices.csv
```

The input columns are `text`, `amount_chf` and `vat_rate`. The output file is overwritten on each run. Example record:

```json
{
  "line_id": 5,
  "text": "Server Migration Hetzner",
  "amount_chf": 1450.0,
  "vat_rate": 8.1,
  "suggested_account": "6570",
  "account_name": "IT and software",
  "priority": "high",
  "reasons": ["amount above review threshold"],
  "status": "draft_pending_human"
}
```

To connect another MCP client, run `mcp_server.py` over stdio. The tool implementations are in `core.py`; the transport boundary is in `mcp_server.py`.

## Evaluation snapshot

These are small synthetic-data experiments, not estimates of production accuracy. See [REPORT.md](REPORT.md) for the complete table, attack construction and sample limitations.

| Check | Observed result |
|---|---|
| Held-out-vendor rows | 69 / 74 correct (93.2%) |
| Hand-written out-of-phrase stress test | 17 / 36 correct (47.2%; 95% interval 32–63%) |
| Clean agent test rows | 5 / 56 wrong; 4 / 54 normal-priority drafts wrong |
| Short suffix attacks through the MCP agent | 152 / 352 wrong (43%); 151 / 351 normal-priority drafts wrong |
| Harmless noisy lines flagged by the length cap | 19 / 40 |

The OOD set was written around known weaknesses and its labels were not independently reviewed. Attack cases are repeated modifications of a smaller set of base lines, not independent samples. Some suffixes contain genuine accounting content, so the original label is not always an unambiguous target.

## Reproduce the evaluations

The quickstart and unit tests need only this repository. The evaluation scripts also expect the dataset and training repositories beside this one:

```text
parent-directory/
├── bookkeeping-mcp-agent/
├── swiss-bookkeeping-ai/
└── swiss-sme-bookkeeping-dataset/
```

From this repository's root:

```bash
uv run python eval_guardrails.py
uv run python eval_false_positives.py
uv run python eval_heldout.py
uv run python eval_short.py
uv run python agent.py
uv run python eval_agent.py
uv run python eval_ablation.py
uv run python eval_ood.py
```

These scripts run many model inferences and take longer than the demo. Raw agent results are written to `eval_agent_results.json`.

## Repository layout

| File | Role |
|---|---|
| `mcp_server.py` | FastMCP tool definitions and stdio server |
| `agent.py` | Local MCP client and review-queue writer |
| `core.py` | Model loading, output parsing and deterministic checks |
| `test_tools.py` | Fast unit tests with the model call mocked |
| `eval_*.py` | Reproducible robustness and ablation experiments |
| `REPORT.md` | Full measurements, interpretation and limitations |

## Known limits

- Keyword and length rules do not generalize to short content-based steering.
- A confidently wrong account can pass every deterministic check.
- The 56 agent test rows have no exact training-text overlap, but 44 occur in validation and 12 in the hard test split; they are not fully independent of model development.
- The data is synthetic, German-centric and limited to six accounts.
- Model scores are not calibrated confidence estimates.
- Do not use this project for unattended posting, production bookkeeping or tax decisions.
