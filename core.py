import re
from functools import lru_cache

MODEL_PATH = "../swiss-bookkeeping-ai/fused_8bit"
CHART = {
    "5830": "Travel expenses (staff)",
    "6200": "Vehicle expenses",
    "6500": "Office supplies and administration",
    "6510": "Telephone and internet",
    "6570": "IT and software",
    "6600": "Advertising",
}
ALLOWED_VAT = (0.0, 2.6, 3.8, 8.1)
REVIEW_ABOVE_CHF = 1000.0
MAX_TEXT_LEN = 200
SUSPICIOUS = ("ignore", "instruction", "system prompt", "previous", "disregard", "override")
SYSTEM = ("You are a Swiss SME bookkeeper. Reply with ONLY the 4-digit account number "
          "from the chart.\n\nChart:\n" + "\n".join(f"{k} {v}" for k, v in sorted(CHART.items())))


@lru_cache(maxsize=1)
def _model():
    from mlx_lm import load
    return load(MODEL_PATH)


def suggest_account(text, amount_chf, vat_rate):
    from mlx_lm import generate
    model, tok = _model()
    user = f"Invoice line: {text} | CHF {amount_chf:.2f} | VAT {vat_rate:g}%"
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    out = generate(model, tok, prompt=prompt, max_tokens=8)
    m = re.search(r"\d{4}", out)
    return m.group(0) if m else None


def lookup_account(account):
    key = str(account).strip()
    if key in CHART:
        return {"account": key, "name": CHART[key]}
    return {"error": "unknown account", "valid_accounts": sorted(CHART)}


def check_vat(vat_rate):
    ok = round(float(vat_rate), 1) in ALLOWED_VAT
    return {"vat_rate": vat_rate, "status": "OK" if ok else "FLAG", "allowed": list(ALLOWED_VAT)}


def review_line(text, amount_chf, vat_rate):
    reasons = []
    low = text.lower()
    if len(text) > MAX_TEXT_LEN:
        reasons.append("text unusually long")
    if any(word in low for word in SUSPICIOUS):
        reasons.append("text contains instruction-like wording")
    account = suggest_account(text, amount_chf, vat_rate)
    if account not in CHART:
        reasons.append("model returned no valid account")
        account = None
    if check_vat(vat_rate)["status"] == "FLAG":
        reasons.append("VAT rate not in allowed list")
    if amount_chf > REVIEW_ABOVE_CHF:
        reasons.append("amount above review threshold")
    return {"account": account, "account_name": CHART.get(account),
            "needs_human": bool(reasons), "reasons": reasons}
