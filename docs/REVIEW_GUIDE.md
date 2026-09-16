# Use-specific readiness reviews

Pharos separates the OpenAlex object being viewed from the decision a user needs to make. A saved snapshot supplies dated evidence; a review compares that evidence with one or more intended uses; a report communicates the resulting readiness, limitations, and methodology; and a data package carries the underlying identifiers, scope, and provenance.

## Current workflow

1. Build or reopen a saved snapshot.
2. Choose **Review**, then select one or more intended uses.
3. Compare the deduplicated evidence-by-use matrix. Each use receives a provisional readiness result: **Ready**, **Ready with limitations**, **Validation needed**, or **Not supported by this snapshot**.
4. Inspect the observed value, configured requirement, OpenAlex's role, required external join, benchmark status, and evidence source for each row.
5. Open a focused review when a human needs to record evidence, change a provisional status, or override a threshold or materiality.
6. Download either a combined `pharos-readiness-matrix-v1` comparison or a detailed `pharos-review-record-v3` record.

The browser keeps an in-progress detailed review only in page memory. It is not added to the saved snapshot, server cache, canonical report export, or OpenAlex data. Users must download the review record if they want to retain their judgements.

## Readiness model

Readiness is use-specific. Pharos does not average unrelated measures into one quality score.

- **Ready** means every essential configured requirement is met.
- **Ready with limitations** means essential requirements are met, but relevant evidence is incomplete or below its configured requirement.
- **Validation needed** means an essential requirement needs local, record-level, policy, or destination-system evidence.
- **Not supported by this snapshot** means an essential configured requirement is not met.

The initial thresholds are deterministic defaults in `src/pharos/review_guide.py`. They are provisional product assumptions, not universal claims about data quality. A user can change a threshold or materiality only with a recorded reason and rationale. Case-level and claim-level questions, including researcher identity and funding evidence, cannot pass automatically from aggregate OpenAlex evidence.

## Interoperability and benchmarks

Interoperability is shown inside every applicable evidence row. The guide states OpenAlex's role, whether it is sufficient on its own, the source that should be joined, the join key, and the validation still required. Typical joins include a CRIS or repository, HR and organisation records, award or finance systems, ORCID, ROR, DOI or Crossref records, publication full text, and funder policy definitions.

Automatic checks cover Pharos's own versioned exports. Destination-specific field mapping, vocabulary mapping, test import, deduplication, and round-trip verification remain explicit validation tasks. Pharos cannot certify another system it has not tested.

Benchmarks provide context rather than a pass/fail rule. A measure is labelled benchmarkable only when a comparator can use the same period, work types, population definition, and relevant field or geography. Until a matching comparator is calculated, the interface says that no benchmark is available. Recorded acknowledgement prevalence, open-access availability, ORCID presence, and similar measures are not described as proof of real-world compliance or completeness.

## Evidence and trust boundary

The server builds `pharos-review-guide-v3` from the completed snapshot already held in the current session. It makes no OpenAlex request. Checklist content comes from a controlled catalogue, and every item carries semantic evidence references, a validated interface destination, a measurement definition, the saved observation, a use-specific requirement, materiality, interoperability guidance, benchmark status, and an explicit decision boundary. Earlier schemas remain published for existing downloads.

The review does not change entity selection, scope, counts, denominators, warnings, identity recommendations, funding attribution, provenance, or canonical report exports. User notes and overrides remain user judgements. Following a link to a live drill-down retains the report's saved-versus-live warning.

## Optional local-model experiment

Pharos can request editable draft wording from an operator-configured OpenAI-compatible chat-completions endpoint on `127.0.0.1`, `localhost`, or `::1`. Set `PHAROS_SLM_ENDPOINT` to the full endpoint URL and `PHAROS_SLM_MODEL` to the served model name before starting Pharos. Non-loopback endpoints are rejected so review context is not silently sent off-machine. With no configuration, the deterministic review remains fully functional.

The server sends only the selected controlled checklist item, its saved observation, evidence references, interview answers, and up to 1,000 characters of optional user context. Returned prose is length-bounded and rejected when it contains common suitability-verdict language. The interface labels the result with model and inference location, keeps it editable, and requires the user to copy it into a note and choose a status independently. Model input and output are never added to the canonical report.

No model should calculate measures, choose entities, determine readiness, resolve identities, attribute funding, or modify the canonical report.
