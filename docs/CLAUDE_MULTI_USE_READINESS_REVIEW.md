# Pharos multi-use readiness implementation — review brief

## What changed

Pharos now treats the OpenAlex object, its saved evidence, and the user's intended use as distinct things:

- a **view** explores one OpenAlex object;
- a **snapshot** records aggregate evidence for a dated scope and period;
- a **review** compares that evidence with one or more uses;
- a **report** communicates the use-specific result and limitations; and
- a **data package** carries the evidence, identifiers, scope, and provenance.

The former use-first chooser has been removed. The main entry point now calculates and shows readiness for every applicable use before asking the user to choose anything. A focused evidence view is available only after the user opens a result.

## User-facing behaviour

1. Opening **Readiness by use** immediately evaluates every applicable use, including publication reconciliation, institutional reporting, bibliometric analysis, funding evidence, open-access evidence, and interoperability with another system.
2. Each use receives a provisional categorical result: **Ready**, **Ready with limitations**, **Validation needed**, or **Not supported by this snapshot**.
3. Each card states how many essential checks are resolved and prints the default numeric thresholds used.
4. A focused evidence view exposes observations first. Definitions, validation guidance, notes, and requirement overrides remain collapsed until requested.
5. The user can change a threshold or materiality with a reason and rationale.
6. The overview and detailed review can be downloaded as versioned JSON.

There is deliberately no composite quality score. A high percentage in one field cannot compensate for missing essential evidence elsewhere.

## Readiness rules

- Essential configured requirement below its threshold: **Not supported by this snapshot**.
- Essential item requiring case-level, policy, local-system, or destination-system evidence: **Validation needed**.
- Essential requirements met, but a relevant item remains unresolved: **Ready with limitations**.
- All essential and relevant configured requirements met: **Ready**.

These are deterministic provisional results. The current numeric defaults are product hypotheses, not universal standards:

- discovery: abstracts 70%, primary subject 80%;
- publication reconciliation: DOI 80%, primary source 90%;
- institutional reporting: primary subject 80%;
- bibliometric analysis: primary subject 80%; and
- interoperability assessment: DOI 80%.

Case-level researcher identity and funding claims are capped at **Validation needed** until external evidence is recorded.

## Interoperability

Interoperability is part of each evidence row rather than a footer. The implementation distinguishes OpenAlex's role from the authoritative join and remaining validation. Named joins include CRIS and repository records, HR and organisation data, award or finance systems, ORCID, ROR, DOI or Crossref records, publisher or repository text, and policy definitions.

Pharos can validate its own versioned exports. It does not claim to certify destination-system mappings, imports, deduplication, or round trips without a documented test.

## Benchmarks

The data model can identify benchmarkable measures, but no national or global comparator is fabricated. Every current benchmark is explicitly `not_calculated`. A future comparator must match period, Work types, population definition, and relevant field or geography. Benchmarks provide context and do not determine compliance.

## Schemas and documentation

- `pharos-review-guide-v3`
- `pharos-review-record-v3`
- `pharos-readiness-matrix-v1`
- Earlier v1 and v2 schema files remain available.
- `docs/MULTI_USE_READINESS_PLAN.md` records the product model and delivery sequence.
- `docs/REVIEW_GUIDE.md` documents the implemented workflow and trust boundary.

## Verification performed

- Python unit suite: 78 tests passing.
- JavaScript syntax check passing.
- All published JSON schema documents parse successfully and current version constants are tested.
- Browser walkthrough against the saved University of Oxford 2012–2025 snapshot.
- Confirmed that readiness is shown before the user chooses a use.
- Confirmed that the obsolete use-selection screen is absent.
- Confirmed differentiated classifications and visible default thresholds.
- Confirmed that the focused evidence view has compact, progressively disclosed controls.

## Known limitations and deliberate deferrals

- The default thresholds require domain review and empirical validation before being presented as normative defaults.
- No peer, UK, or global benchmark has yet been calculated.
- A benchmark service will need a defensible comparator-population design and provenance before implementation.
- The matrix is compact relative to separate checklists, but comparisons with many selected uses still require horizontal scrolling.
- User judgements remain in page memory until downloaded; they are not silently added to the saved OpenAlex snapshot.
- The combined matrix export has a published structural schema, but it does not yet include completed human judgements from several detailed reviews in one file.

## Questions for Claude's review

1. Are the four readiness categories mutually intelligible, and is the precedence rule defensible?
2. Which provisional thresholds should be removed, changed, or conditioned by Work type, period, or decision consequence?
3. Are any essential requirements misclassified as merely relevant, or vice versa?
4. Does each use name the correct authoritative external systems and joins?
5. Which measures can support a genuinely like-for-like benchmark, and what comparator populations would be defensible?
6. Does the matrix communicate “evidence for a use” without implying a general OpenAlex quality score?
7. Should completed judgements across several uses be merged into a single signed or auditable review package?
