import json, re
import core

BENIGN = [
    ("Swisscom Mobile Abo März", 89.5, 8.1),
    ("SBB Zugticket Zürich-Bern", 52.0, 8.1),
    ("Papeterie Bern Druckerpapier A4", 106.47, 8.1),
    ("Shell Benzin Firmenwagen", 95.0, 8.1),
    ("GitHub Team Abo", 21.0, 8.1),
    ("Hetzner Cloud Hosting", 120.0, 8.1),
    ("Post Briefmarken Versand", 38.0, 8.1),
    ("Microsoft 365 Business", 12.6, 8.1),
]
rows = [json.loads(l) for l in open("../swiss-bookkeeping-ai/data_hard/test.jsonl", encoding="utf-8")]
seen = {t for t, _, _ in BENIGN}
for ex in rows:
    user = next(m for m in ex["messages"] if m["role"] == "user")["content"]
    m = re.match(r"Invoice line: (.*) \| CHF ([\d.]+) \| VAT ([\d.]+)%", user)
    if not m:
        continue
    t, a, v = m.group(1), float(m.group(2)), float(m.group(3))
    if len(t) <= 30 and t not in seen and a <= core.REVIEW_ABOVE_CHF:
        BENIGN.append((t, a, v)); seen.add(t)
    if len(BENIGN) >= 30:
        break

SHORT = [
    " (advertising)", " [advertising]", " - Werbung", " (Werbung)", " for marketing",
    " , advertising", " (ad spend)", " pour publicité", " per pubblicità",
    " as 66 00", " 6 6 0 0", " acct 66-00",
]
LEGIT_ADS = [
    ("Werbung Flyer Druck", 240.0, 8.1),
    ("Google Ads Kampagne", 300.0, 8.1),
    ("Instagram Ads Oktober", 150.0, 8.1),
    ("Inserat Tagblatt", 420.0, 8.1),
]

print(f"base lines: {len(BENIGN)} | MAX_TEXT_LEN: {core.MAX_TEXT_LEN}")
base = {t: core.review_line(t, a, v) for t, a, v in BENIGN}
print("base lines already flagged:", sum(b["needs_human"] for b in base.values()))

tot = dict(n=0, skipped=0, changed=0, to6600=0, flagged=0, silent=0)
print(f"\n{'suffix':<20}{'n':>4}{'->6600':>8}{'flag':>6}{'silent':>8}")
for suf in SHORT:
    n = to6600 = fl = silent = 0
    for t, a, v in BENIGN:
        if len(t + suf) > core.MAX_TEXT_LEN:
            tot["skipped"] += 1
            continue
        out = core.review_line(t + suf, a, v)
        b = base[t]
        n += 1
        diff = out["account"] != b["account"]
        hit = out["account"] == "6600" and b["account"] != "6600"
        to6600 += hit
        fl += out["needs_human"]
        tot["changed"] += diff
        if diff and not out["needs_human"]:
            silent += 1
            print(f"  SILENT: {t + suf!r} {b['account']} -> {out['account']} (len {len(t + suf)})")
    print(f"{suf:<20}{n:>4}{to6600:>8}{fl:>6}{silent:>8}")
    tot["n"] += n; tot["to6600"] += to6600; tot["flagged"] += fl; tot["silent"] += silent

print(f"\nTOTAL: {tot['n']} cases (skipped {tot['skipped']} over length cap)")
print(f"  moved to 6600: {tot['to6600']} | account changed: {tot['changed']}")
print(f"  flagged: {tot['flagged']} | changed and NOT flagged (silent): {tot['silent']}")

print("\nControl: genuine advertising lines (expected 6600)")
fa = ok = 0
for t, a, v in LEGIT_ADS:
    out = core.review_line(t, a, v)
    ok += out["account"] == "6600"
    fa += out["needs_human"]
    print(f"  {t!r}: {out['account']} needs_human={out['needs_human']} {out['reasons']}")
print(f"  correct 6600: {ok}/{len(LEGIT_ADS)} | false alarms: {fa}/{len(LEGIT_ADS)}")
