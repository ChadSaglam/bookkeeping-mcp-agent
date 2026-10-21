import json, re
import core

rows = [json.loads(l) for l in open("../swiss-bookkeeping-ai/data_hard/test.jsonl", encoding="utf-8")]
flagged = []
for ex in rows:
    user = next(m for m in ex["messages"] if m["role"] == "user")["content"]
    text = re.sub(r"^Invoice line: | \| CHF.*$", "", user)
    if core.text_risks(text):
        flagged.append(text)
print(f"{len(flagged)} of {len(rows)} clean test lines flagged by the text rules")
for t in flagged:
    print(" ", t)
