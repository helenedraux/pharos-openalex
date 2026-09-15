# Purpose-led review guides

Pharos helps a user decide whether OpenAlex's representation is suitable for the user's own task. It does not make that decision. The review-guide feature therefore turns a completed, dated report into a deterministic inspection checklist rather than a verdict.

## Current workflow

1. Build or reopen a saved report.
2. Choose **Guide my review** and select an intended use.
3. Follow each checklist item to the relevant report evidence.
4. Record a human status: not checked, checked, concern, unresolved, or not applicable.
5. Optionally add a note and download a separate `pharos-review-record-v1` JSON file.

Publication-list/repository reconciliation is available for institution reports. Researcher identity checking is available for researcher reports. A general inspection guide is available for all report types.

The browser keeps an in-progress review only in page memory. It is not added to the saved report, server cache, canonical report export, or OpenAlex data. Users must download the review record if they want to retain it.

## Evidence and trust boundary

The server builds `pharos-review-guide-v1` from the completed report already held in the current session. It makes no OpenAlex request. Checklist content comes from a controlled catalogue in `src/pharos/review_guide.py`, and every item carries semantic evidence references and a validated interface destination.

The guide does not change entity selection, scope, counts, denominators, warnings, identity recommendations, funding attribution, provenance, or report exports. User notes remain user judgements. Following a link to a live drill-down retains the report's saved-versus-live warning.

## Optional local-model experiment

Pharos can request editable draft wording from an operator-configured OpenAI-compatible chat-completions endpoint on `127.0.0.1`, `localhost`, or `::1`. Set `PHAROS_SLM_ENDPOINT` to the full endpoint URL (for example `http://127.0.0.1:8080/v1/chat/completions`) and `PHAROS_SLM_MODEL` to the served model name before starting Pharos. Non-loopback endpoints are rejected so review context is not silently sent off-machine. With no configuration, the deterministic review remains fully functional and the model control explains that it is unavailable.

The server constructs the input from the selected controlled checklist item, its saved-report observation, evidence references, interview answers, and up to 1,000 characters of optional user context. It does not send the full report. Returned prose is length-bounded and rejected when it contains common suitability-verdict language. The interface labels the result with model and inference location, keeps it editable, and requires the user to copy it into a note and choose a status independently. Downloaded review records mark notes that began as model drafts and retain model provenance; model input and output are never added to the canonical report.

No model should calculate measures, choose entities, determine suitability, resolve identities, attribute funding, or modify the canonical report. Disabling model assistance must leave the current guide and complete report fully functional.
