import csv, math
from collections import Counter, defaultdict
from pathlib import Path
import core

D = Path("../swiss-sme-bookkeeping-dataset")
ood = list(csv.DictReader(open(D / "ood_test.csv", encoding="utf-8")))
orig = list(csv.DictReader(open(D / "swiss_sme_bookkeeping_synthetic.csv", encoding="utf-8")))


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def run(real):
    return [core.suggest_account(r["text"], float(r["amount_chf"]) if real else 100.0,
                                 float(r["vat_rate"]) if real else 8.1) for r in ood]


n = len(ood)
res = {}
for name, real in (("real amount and VAT", True), ("neutral (100.00, 8.1)", False)):
    preds = run(real)
    k = sum(p == r["account"] for p, r in zip(preds, ood))
    lo, hi = wilson(k, n)
    res[name] = preds
    print(f"model, {name}: {k}/{n} = {k / n:.1%} (95% interval {lo:.0%}-{hi:.0%})")

bins = [0, 25, 50, 100, 200, 400, 800, 950, 1e9]
key = lambda r: (r["vat_rate"], next(i for i, b in enumerate(bins[1:]) if float(r["amount_chf"]) <= b))
tab = defaultdict(Counter)
for r in orig:
    if r["split"] == "train":
        tab[key(r)][r["account"]] += 1
glob = Counter(r["account"] for r in orig if r["split"] == "train").most_common(1)[0][0]
kb = sum((tab[key(r)].most_common(1)[0][0] if key(r) in tab else glob) == r["account"] for r in ood)
print(f"amount+VAT lookup baseline: {kb}/{n} = {kb / n:.1%} (chance about 16.7%)")

print("\nper account (real condition):")
for acct in sorted({r["account"] for r in ood}):
    idx = [i for i, r in enumerate(ood) if r["account"] == acct]
    print(f"  {acct}: {sum(res['real amount and VAT'][i] == acct for i in idx)}/{len(idx)}")
print("\nmisses (real condition):")
for p, r in zip(res["real amount and VAT"], ood):
    if p != r["account"]:
        print(f"  {r['text']!r} CHF {r['amount_chf']} VAT {r['vat_rate']}: expected {r['account']} got {p}")
