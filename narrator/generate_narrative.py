"""
Part 3: GenAI insight narrator (Situation - Complication - Resolution).

    python narrator/generate_narrative.py

* With GEMINI_API_KEY set  -> asks Gemini (free Google AI Studio key) for the narrative.
* With NO key (or if the API call fails) -> uses a deterministic offline template.
Either way the five required figures are checked and the result is saved to
narrator/sample_output.txt.

Input: narrator/findings.json (written by analysis/clean_and_eda.py, never by hand).
"""
import calendar
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINDINGS_PATH = HERE / "findings.json"
SAMPLE_PATH = HERE / "sample_output.txt"

# Model names change often (gemini-2.5-flash is scheduled to shut down on 16 Oct 2026), so we try a
# short list in order. To force one model:  $env:GEMINI_MODEL="model-name"
MODELS = ([os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL")
          else ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-3.1-flash-lite"])
MODEL_USED = None            # filled in with whichever model actually answered
TIMEOUT_MS = 30_000          # the SDK takes milliseconds: 30,000 ms = 30 s (the brief's minimum is 10 s)
MAX_OUTPUT_TOKENS = 4096     # explicit and generous: newer models spend part of this budget on hidden "thinking"


# ------------------------------------------------------------------ helpers
def month_label(ym: str) -> str:
    """'2026-03' -> 'March 2026'"""
    year, month = ym.split("-")
    return f"{calendar.month_name[int(month)]} {year}"


def inr(x: float) -> str:
    return f"{x:,.2f}"


def get_api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def load_findings(path: Path = FINDINGS_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ prompts (built from findings)
SYSTEM_INSTRUCTION = (
    "You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
    "Write a business narrative with exactly three labeled sections: Situation, Complication, Resolution. "
    "Rules: (1) Every number you use must come from the FINDINGS the user supplies and must appear with "
    "the same value; never invent, estimate or round differently. (2) Write for non-technical readers: "
    "no code, no jargon. (3) Keep the whole narrative to roughly 250 words. (4) Use INR for money. "
    "(5) Resolution must give concrete, actionable steps for ops and finance."
)


def build_user_prompt(findings: dict) -> str:
    """Interpolates every number from `findings`; nothing is hardcoded here."""
    rr = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]
    return (
        "FINDINGS (verified; use these numbers exactly):\n"
        f"- Raw total revenue (before cleaning): INR {inr(findings['raw_total_revenue_inr'])}\n"
        f"- Cleaned total revenue (duplicates removed): INR {inr(findings['cleaned_total_revenue_inr'])}\n"
        f"- Difference caused by 5 double-submitted duplicate orders: INR {inr(findings['duplicate_reconciliation_delta_inr'])}\n"
        f"- Return rate by payment method: COD {rr['COD']}%, Card {rr['CARD']}%, UPI {rr['UPI']}%\n"
        f"- Highest-risk segment: {seg['payment_method']} orders in Tier-{seg['city_tier']} cities, "
        f"return rate {seg['return_rate_pct']}%\n"
        f"- True peak revenue month (after excluding 2 bulk-order outliers): {month_label(peak['month'])}, "
        f"INR {inr(peak['revenue_inr'])}\n"
        f"- {month_label(infl['month'])} only looked like the best month at INR {inr(infl['apparent_revenue_inr'])}; "
        f"corrected it is INR {inr(infl['corrected_revenue_inr'])}\n\n"
        "Write the Situation / Complication / Resolution narrative now."
    )


# ------------------------------------------------------------------ online path (Gemini)
def generate_scr_narrative(findings: dict) -> dict:
    """Ask Gemini for the SCR narrative. Never raises: always returns a dict.

    success -> {"status": "success", "narrative": str, "tokens": int}
    failure -> {"status": "error",   "narrative": None, "message": str}
    """
    global MODEL_USED
    try:
        key = get_api_key()
        if not key:
            raise RuntimeError("No GEMINI_API_KEY set")
        from google import genai                     # imported here so the offline path needs no package
        from google.genai import types

        client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
        errors = []
        for model in MODELS:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=build_user_prompt(findings),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,   # role + structure + no-invented-numbers rule
                        # temperature 0.0: this is a factual finance report, so we want the most
                        # deterministic, repeatable wording, not creative variation.
                        temperature=0.0,
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                    ),
                )
                text = response.text
                if not text:
                    raise RuntimeError("empty response")
                usage = getattr(response, "usage_metadata", None)
                tokens = getattr(usage, "total_token_count", None) or 0
                MODEL_USED = model
                return {"status": "success", "narrative": text.strip(), "tokens": tokens}
            except Exception as model_err:           # this model failed: remember why, try the next one
                errors.append(f"{model}: {model_err}")
        raise RuntimeError("All models failed -> " + " | ".join(errors))
    except Exception as err:                          # caller never sees a raw exception
        return {"status": "error", "narrative": None, "message": str(err)}


# ------------------------------------------------------------------ offline path (no key, no network)
def generate_scr_narrative_offline(findings: dict) -> dict:
    """Deterministic template built only from `findings`. Same return shape as the online path."""
    rr = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]
    narrative = (
        "SITUATION\n"
        f"After removing 5 double-submitted orders, Mamaearth's cleaned order revenue stands at "
        f"INR {inr(findings['cleaned_total_revenue_inr'])}, not the INR {inr(findings['raw_total_revenue_inr'])} "
        f"a raw count suggests. The INR {inr(findings['duplicate_reconciliation_delta_inr'])} gap is entirely "
        f"those duplicates. Revenue peaked in {month_label(peak['month'])} at INR {inr(peak['revenue_inr'])}. "
        f"{month_label(infl['month'])} only looked stronger (INR {inr(infl['apparent_revenue_inr'])}) because two "
        f"bulk orders landed in it; without them it was INR {inr(infl['corrected_revenue_inr'])}.\n\n"
        "COMPLICATION\n"
        f"Returns are concentrated, not spread evenly. Cash on delivery orders are returned "
        f"{rr['COD']}% of the time, against {rr['UPI']}% for UPI and {rr['CARD']}% for Card. "
        f"The problem is sharpest for {seg['payment_method']} orders in Tier-{seg['city_tier']} cities, "
        f"where {seg['return_rate_pct']}% of orders come back. Every returned order erodes margin "
        f"after shipping and handling have already been paid.\n\n"
        "RESOLUTION\n"
        f"1) Operations: add confirmation calls or OTP checks before shipping "
        f"{seg['payment_method']} orders to Tier-{seg['city_tier']} cities, and pilot a small prepaid discount "
        f"to move buyers from COD to UPI or Card. "
        f"2) Finance: report revenue on the cleaned base of INR {inr(findings['cleaned_total_revenue_inr'])} "
        f"and track return-adjusted margin by payment method. "
        f"3) Planning: treat {month_label(peak['month'])} as the true seasonal peak and exclude bulk orders "
        f"when forecasting."
    )
    return {"status": "success", "narrative": narrative, "tokens": 0}


# ------------------------------------------------------------------ choose path
def get_narrative(findings: dict):
    """Try Gemini; on a missing key or any error, fall back to the offline template.
    Returns (result_dict, source_label)."""
    if get_api_key():
        result = generate_scr_narrative(findings)
        if result["status"] == "success":
            return result, f"Gemini ({MODEL_USED})"
        print(f"[warn] Gemini call failed ({result['message']}). Falling back to offline template.")
    else:
        print("[info] No GEMINI_API_KEY set. Using the offline template (no network needed).")
    return generate_scr_narrative_offline(findings), "offline template"


# ------------------------------------------------------------------ numeric accuracy check
def check_figures(narrative: str, findings: dict) -> bool:
    """Assert the 5 required figures appear in the narrative (commas ignored). Prints PASS/FAIL each."""
    text = narrative.replace(",", "")
    peak = findings["true_peak_month"]
    required = {
        "cleaned total revenue": f"{findings['cleaned_total_revenue_inr']:.2f}".rstrip("0").rstrip("."),
        "COD return rate": str(findings["return_rate_by_payment"]["COD"]),
        "COD + Tier-2 segment rate": str(findings["highest_risk_segment"]["return_rate_pct"]),
        "duplicate reconciliation delta": f"{findings['duplicate_reconciliation_delta_inr']:.2f}".rstrip("0").rstrip("."),
        "peak month name": calendar.month_name[int(peak["month"].split("-")[1])],
        "peak month revenue": f"{peak['revenue_inr']:.2f}".rstrip("0").rstrip("."),
    }
    ok = True
    print("\nNumeric accuracy check:")
    for label, needle in required.items():
        found = needle in text
        ok &= found
        print(f"  [{'PASS' if found else 'FAIL'}] {label}: '{needle}'")
    print("  ->", "ALL FIGURES PRESENT" if ok else "SOME FIGURES MISSING")
    return ok


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    findings = load_findings()
    result, source = get_narrative(findings)
    print(f"\n=== Narrative (source: {source}) ===\n")
    print(result["narrative"])
    check_figures(result["narrative"], findings)
    SAMPLE_PATH.write_text(f"[source: {source}]\n\n{result['narrative']}\n", encoding="utf-8")
    print(f"\nSaved -> {SAMPLE_PATH}")