import json, random, re, sys
import core

rows = [json.loads(l) for l in open("../swiss-bookkeeping-ai/data_hard/test.jsonl", encoding="utf-8")]
data = []
for ex in rows:
    msgs = {m["role"]: m["content"] for m in ex["messages"]}
    if "assistant" not in msgs:
        sys.exit("no assistant message in test.jsonl, cannot read the expected account")
    m = re.match(r"Invoice line: (.*) \| CHF ([\d.]+) \| VAT ([\d.]+)%", msgs["user"])
    exp = re.search(r"\d{4}", msgs["assistant"]).group(0)
    data.append((m.group(1), float(m.group(2)), float(m.group(3)), exp))

pairs = [(a, v) for _, a, v, _ in data]
shuf = pairs[:]
random.Random(0).shuffle(shuf)
conds = {"real amount and VAT": pairs,
         "neutral (100.00, 8.1)": [(100.0, 8.1)] * len(data),
         "shuffled across rows": shuf}

preds = {}
for name, pv in conds.items():
    preds[name] = [core.suggest_account(t, a, v) for (t, _, _, _), (a, v) in zip(data, pv)]
    ok = sum(p == d[3] for p, d in zip(preds[name], data))
    print(f"{name:<24} {ok}/{len(data)} = {ok / len(data):.1%}")

base = preds["real amount and VAT"]
for name in list(conds)[1:]:
    ch = sum(p != b for p, b in zip(preds[name], base))
    print(f"{name:<24} predictions changed vs real: {ch}/{len(data)}")
