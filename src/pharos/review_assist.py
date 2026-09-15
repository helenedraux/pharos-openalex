"""Bounded model assistance for review wording; never a review decision."""
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


SYSTEM_PROMPT = """You draft short, cautious review notes for Pharos. Use only the supplied
saved-report evidence and checklist instructions. Do not decide suitability, assign a
status, infer missing facts, recommend pass/fail, or claim the user completed a check.
State what the evidence establishes, then what a human still needs to inspect. Return
plain text only, at most 120 words."""


class ReviewAssistError(Exception):
    pass


def _configuration(endpoint=None, model=None):
    endpoint = endpoint if endpoint is not None else os.environ.get("PHAROS_SLM_ENDPOINT", "")
    model = model if model is not None else os.environ.get("PHAROS_SLM_MODEL", "")
    if not endpoint or not model:
        raise ReviewAssistError("Model assistance is not configured on this Pharos server.")
    parsed = urlsplit(endpoint)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
        raise ReviewAssistError("PHAROS_SLM_ENDPOINT must be an http(s) endpoint without embedded credentials.")
    if parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ReviewAssistError("PHAROS_SLM_ENDPOINT must use a loopback host so review context stays on this machine.")
    return endpoint.rstrip("/"), model


def assistance_status(endpoint=None, model=None):
    try:
        _, selected_model = _configuration(endpoint, model)
        return {"available": True, "model": selected_model, "location": "local server"}
    except ReviewAssistError:
        return {"available": False, "model": None, "location": "local server"}


def build_packet(guide, item, user_context=""):
    if not isinstance(user_context, str) or len(user_context) > 1000:
        raise ValueError("Review context must be text of at most 1,000 characters.")
    return {
        "purpose": {"id": guide["purpose"]["id"], "label": guide["purpose"]["label"]},
        "answers": guide["answers"],
        "check": {
            key: item.get(key) for key in
            ("id", "title", "guidance", "action", "record", "observation", "evidence_refs")
        },
        "optional_user_context": user_context.strip(),
    }


def _validate_text(value):
    if not isinstance(value, str):
        raise ReviewAssistError("The model did not return a text draft.")
    value = " ".join(value.split()).strip()
    if not value or len(value) > 2000:
        raise ReviewAssistError("The model returned an empty or overlong draft.")
    prohibited = ("suitable for", "not suitable", "fit for purpose", "pass", "fail")
    if any(phrase in value.casefold() for phrase in prohibited):
        raise ReviewAssistError("The model draft crossed the suitability-verdict boundary and was not displayed.")
    return value


def generate_review_draft(guide, item, user_context="", endpoint=None, model=None, opener=urlopen):
    endpoint, model = _configuration(endpoint, model)
    packet = build_packet(guide, item, user_context)
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 220,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False, separators=(",", ":"))},
        ],
    }
    request = Request(endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with opener(request, timeout=30) as response:
            result = json.loads(response.read(256 * 1024))
        text = result["choices"][0]["message"]["content"]
    except ReviewAssistError:
        raise
    except Exception as exc:
        raise ReviewAssistError("The configured model could not produce a draft. The deterministic review remains available.") from exc
    return {
        "kind": "model_generated_draft",
        "text": _validate_text(text),
        "model": model,
        "location": "local server",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checklist_item_id": item["id"],
        "evidence_refs": item["evidence_refs"],
        "input": packet,
        "warning": "Draft wording only. Edit it and choose the review status yourself; this is not a suitability verdict.",
    }
