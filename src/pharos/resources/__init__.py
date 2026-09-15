import math
from datetime import date

RATE_CARD = {"as_of": "2026-09-07", "list_call_usd": 0.0001, "free_daily_budget_usd": 1.0,
             "anonymous_daily_budget_usd": 0.1, "payment_card_required": False,
             "source": "https://help.openalex.org/access/example-costs/"}


def validate_rates(rates):
    date.fromisoformat(rates["as_of"])
    for key in ("list_call_usd", "free_daily_budget_usd", "anonymous_daily_budget_usd"):
        if isinstance(rates[key], bool) or not isinstance(rates[key], (int, float)) or not math.isfinite(rates[key]) or rates[key] < 0:
            raise ValueError("Rate card must contain finite nonnegative amounts.")
    return rates


def estimate(count, rates, authenticated):
    calls = math.ceil(count / 100) + 1  # Includes final cursor exhaustion probe.
    cost = round((calls + 1) * rates["list_call_usd"], 8)  # Plus count query.
    budget = rates["free_daily_budget_usd"] if authenticated else rates["anonymous_daily_budget_usd"]
    return {"operation": "retrieve_profile_corpus", "backend": "openalex_api", "estimated_records": count,
        "estimated_retrieval_calls": calls, "estimated_calls": calls + 2,
        "calls_basis": "One free identity lookup, one count query, pages of 100, one terminal probe; retries extra.",
        "estimated_api_cost_usd": cost, "free_daily_budget_sufficient": cost <= budget,
        "payment_card_required": rates["payment_card_required"], "rate_card": rates,
        "estimated_download_mb": None, "download_estimate_basis": "Unknown until a full page is received; abstracts and authorship sizes vary.",
        "estimate_basis": "OpenAlex meta.count and dated configurable rate card",
        "warnings": ["Estimate is not a guarantee or a remaining account balance. API data may change during retrieval.",
                     "Profiling uses memory proportional to the retrieved corpus; --max-records bounds local work."],
        "call_tolerance": "One terminal page plus retries; count drift is reported without hiding discrepancies."}
