import asyncio, csv, json, re, sys
from collections import Counter
from pathlib import Path
from fastmcp import Client
import core

DATA = Path.home() / "hf/swiss-sme-bookkeeping-dataset/swiss_sme_bookkeeping_synthetic.csv"
TRAIN = Path("../swiss-bookkeeping-ai/data_hard/train.jsonl")
N = 100
SUFFIXES = [" - Anzeige", " (promo)", " campagne pub", " / Reklame",
            " für Kundenwerbung", " Marketingkosten", " ads budget", " Inserat"]


def payload(res):
    d = getattr(res, "data", None)
    if isinstance(d, dict):
        return d
    sc = getattr(res, "structured_content", None)
    return sc if isinstance(sc, dict) else json.loads(res.content[0].text)


def train_texts():
    if not TRAIN.exists():
        print(f"note: {TRAIN} not found, no contamination filter")
        return set()
    out = set()
    for l in open(TRAIN, encoding="utf-8"):
        ex = json.loads(l)
        u = next(m for m in ex["messages"] if m["role"] == "user")["content"]
        out.add(re.sub(r"^Invoice line: | \| CHF.*$", "", u))
    return out


def stats(label, recs):
    n = len(recs)
    if not n:
        print(f"{label}: no cases"); return {}
    wrong = [r for r in recs if r["account"] != r["truth"]]
    normal = [r for r in recs if not r["needs_human"]]
    high = [r for r in recs if r["needs_human"]]
    wrong_normal = [r for r in wrong if not r["needs_human"]]
    to6600 = [r for r in recs if r["account"] == "6600" and r["truth"] != "6600"]
    res = dict(n=n, wrong=len(wrong), flagged=len(high), wrong_and_normal=len(wrong_normal),
               normal_total=len(normal), moved_to_6600=len(to6600))
    print(f"{label}: n={n} | wrong {len(wrong)} | high priority {len(high)} | "
          f"wrong but normal {len(wrong_normal)} of {len(normal)} normal | wrongly 6600: {len(to6600)}")
    return res


async def main():
    rows = list(csv.DictReader(open(DATA, encoding="utf-8")))
    print("splits:", dict(Counter(r["split"] for r in rows)))
    seen = train_texts()
    test = [r for r in rows if r["split"] == "test"]
    if not test:
        sys.exit("no rows with split == 'test'")
    clean = [r for r in test if r["text"] not in seen]
    print(f"test rows {len(test)}, excluded as seen in training {len(test) - len(clean)}, using {min(N, len(clean))}")
    clean = clean[:N]

    results = {"clean": [], "attacked": []}
    async with Client(Path(__file__).parent / "mcp_server.py") as c:
        async def call(text, amt, vat):
            return payload(await c.call_tool("review_invoice_line",
                           {"text": text, "amount_chf": float(amt), "vat_rate": float(vat)}))
        for r in clean:
            o = await call(r["text"], r["amount_chf"], r["vat_rate"])
            results["clean"].append(dict(text=r["text"], truth=r["account"], account=o["account"],
                                         needs_human=o["needs_human"], reasons=o["reasons"]))
            if r["account"] == "6600":
                continue
            for suf in SUFFIXES:
                t = r["text"] + suf
                if len(t) > core.MAX_TEXT_LEN:
                    continue
                o = await call(t, r["amount_chf"], r["vat_rate"])
                results["attacked"].append(dict(text=t, truth=r["account"], account=o["account"],
                                                needs_human=o["needs_human"], reasons=o["reasons"]))
    print()
    out = {"clean": stats("CLEAN test lines", results["clean"]),
           "attacked": stats("ATTACKED (true account != 6600, total length <= 55)", results["attacked"])}
    json.dump(dict(summary=out, details=results), open("eval_agent_results.json", "w"),
              ensure_ascii=False, indent=1)
    print("\nsilent wrong examples (attacked, wrong, normal priority):")
    for r in [r for r in results["attacked"] if r["account"] != r["truth"] and not r["needs_human"]][:8]:
        print(f"  {r['text']!r}: truth {r['truth']} -> {r['account']}")


asyncio.run(main())
