import asyncio, csv, json, sys
from pathlib import Path
from fastmcp import Client

SRC = sys.argv[1] if len(sys.argv) > 1 else "invoice_lines_demo.csv"
OUT = "review_queue.jsonl"
NEEDED = {"review_invoice_line", "lookup_account", "check_vat"}


def payload(res):
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        return data
    sc = getattr(res, "structured_content", None)
    if isinstance(sc, dict):
        return sc
    return json.loads(res.content[0].text)


async def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    queue = []
    async with Client(Path(__file__).parent / "mcp_server.py") as c:
        names = {t.name for t in await c.list_tools()}
        missing = NEEDED - names
        if missing:
            sys.exit(f"server is missing tools: {missing}")
        for i, r in enumerate(rows, 1):
            out = payload(await c.call_tool("review_invoice_line", {
                "text": r["text"], "amount_chf": float(r["amount_chf"]),
                "vat_rate": float(r["vat_rate"])}))
            queue.append({
                "line_id": i, "text": r["text"], "amount_chf": float(r["amount_chf"]),
                "vat_rate": float(r["vat_rate"]),
                "suggested_account": out["account"], "account_name": out["account_name"],
                "priority": "high" if out["needs_human"] else "normal",
                "reasons": out["reasons"], "status": "draft_pending_human"})
    queue.sort(key=lambda q: (q["priority"] != "high", q["line_id"]))
    with open(OUT, "w", encoding="utf-8") as f:
        for q in queue:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    hi = sum(q["priority"] == "high" for q in queue)
    print(f"{len(queue)} lines -> {OUT} | high priority {hi} | normal {len(queue) - hi}")
    print("All lines are drafts pending human review. Priority is not a safety label.\n")
    for q in queue:
        print(f"[{q['priority']:<6}] #{q['line_id']} {q['text']!r} -> {q['suggested_account']} {q['reasons']}")


asyncio.run(main())
