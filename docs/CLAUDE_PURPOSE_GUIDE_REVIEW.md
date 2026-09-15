# Pharos purpose-led review guide: review brief for Claude

## Review request

Please review the new **Guide my review** interaction in Pharos. Focus on whether it helps a real user answer this question:

> Can I trust OpenAlex's representation of this entity for my intended task, and what evidence should I inspect before deciding?

Pharos must support an informed human judgement rather than issue its own verdict. Please assess the implemented interaction, information architecture, language, evidential integrity and readiness to become the deterministic baseline for a later optional SLM/LLM experiment.

Do not assume that adding AI is desirable. Recommend model assistance only where it would provide clear additional user value over deterministic questions, rules, navigation, filtering or improved writing.

## Product boundary

Pharos describes what OpenAlex currently asserts about a selected entity and corpus. It does not establish administrative or objective truth.

The following principles are non-negotiable:

- The user selects and confirms the exact OpenAlex entity.
- Scope, populations, counts, denominators and missingness remain deterministic.
- Missing metadata is not treated as evidence that a real-world property is absent.
- OpenAlex Author profiles are treated as algorithmic and fallible.
- Work-level funding acknowledgements do not prove that an author or institution received or led an Award.
- Saved aggregates and live drill-downs remain visibly distinct.
- User judgements are not presented as OpenAlex assertions or Pharos findings.
- The guide must not decide whether OpenAlex is fit for the user's purpose.
- The complete report and review workflow must remain functional without AI.

## Implemented interaction

### Entry point

After building or reopening a completed report, the report heading contains a **Guide my review** button beside **New report**.

The button opens a modal headed:

> What are you hoping to use OpenAlex for?

The modal states that Pharos will ask three short questions before prioritising the evidence.

### Purpose selection

Institution reports currently offer:

1. **Find research or researchers**  
   Check whether OpenAlex is sufficiently recognisable and searchable for discovery.

2. **Reconcile a publication list or repository**  
   Compare OpenAlex records with a local publication list or repository.

3. **Prepare institutional reporting**  
   Inspect whether the corpus and metadata can support a defined reporting workflow.

4. **Assess data for bibliometric analysis**  
   Inspect scope, metadata and citation limitations before analysis.

5. **Investigate funding evidence**  
   Separate direct Award assertions from indirect Work-level acknowledgements.

6. **Examine journal or publisher coverage**  
   Inspect primary-location and publisher-lineage scope before using source aggregates.

7. **Another intended use**  
   Start with a general evidence inspection when no specialist guide matches.

Purpose availability is restricted by report type. Researcher reports include researcher identity checking; funder, Source and publisher reports receive relevant subsets rather than the complete institution list.

### Short interview

Every purpose asks two common questions:

1. **How consequential is this use?**
   - Exploratory—learning what the data contains
   - Operational—recurring work or reporting
   - High consequence—people or formal decisions may be affected

2. **How much uncertainty can this use tolerate?**
   - Flexible—I can inspect and qualify cases
   - Moderate—material limitations must be documented
   - Strict—small gaps or ambiguities may matter

A third question is specific to the purpose. Examples include:

- What will you primarily use to match records?
- What is the main reporting focus?
- Which analysis matters most?
- What prompted the identity check?
- What are you trying to establish about funding?

The answers are controlled choices. No model interprets free text in the current implementation.

### Review workspace

Pharos creates a deterministic checklist from:

- The selected purpose.
- The three controlled answers.
- A controlled checklist catalogue.
- The completed saved report already held in the current session.

Checklist items are ordered under three labels:

- **Review first**
- **Review next**
- **Document before finishing**

Where the saved report exposes a compatible measure, the checklist displays the actual value and denominator. For example:

> 274,932 of 283,324 Works (97.0%) have this OpenAlex assertion; 8,392 do not.

Each item contains:

- A title.
- Purpose-specific guidance.
- An optional report-specific observation.
- Semantic evidence references.
- An **Inspect evidence** action.
- A user-controlled status.
- An optional note.

Available statuses are:

- Not checked
- Checked
- Concern
- Unresolved
- Not applicable

The guide explicitly says that priorities organise inspection and are not quality scores.

### Evidence navigation

**Inspect evidence** closes the guide and navigates to the relevant existing report section, such as:

- Institution record and scope
- Coverage gaps
- Subjects and Work types
- Sources and versions
- Collaboration
- Funding
- Citation evidence
- Researcher identity evidence
- Merge/split review
- Underlying Works

The user can reopen the guide and retain in-progress statuses and notes while the page remains open.

### Review record

The user may download a separate `pharos-review-record-v1` JSON file containing:

- Report identity and snapshot metadata.
- Purpose and interview answers.
- Checklist item identifiers.
- User statuses and notes.
- Evidence references.
- Limitations.

The review record is separate from the canonical Pharos report and its PDF, Excel, CSV and JSON exports. In-progress notes remain only in page memory unless downloaded. They are not written to the report, server cache or OpenAlex.

## Current prioritisation behaviour

Prioritisation is deterministic. Every checklist item has a controlled base priority. Where a compatible coverage measure is available, weaker coverage can move the item earlier. Strict uncertainty tolerance or high-consequence use also moves relevant checks earlier.

This currently organises the review; it does not calculate or display a readiness score, pass/fail result, recommendation or fitness verdict.

Please examine whether this prioritisation is methodologically defensible. In particular, consider whether generic percentage thresholds are appropriate at all, or whether priorities should instead follow explicit purpose requirements without treating coverage percentages as comparable across metadata fields.

## Worked example

For a saved University of Oxford institution report, selecting **Reconcile a publication list or repository** currently produces seven checks:

1. Confirm identity, population and scope.
2. Inspect Works without a DOI.
3. Inspect missing or unexpected primary Sources.
4. Compare publication types.
5. Sample unmatched-looking Works.
6. Record saved-versus-live differences.
7. Record what the evidence cannot establish.

The DOI and primary-Source items display their actual saved counts, denominators, percentages and missing counts.

## Relevant implementation files

- `src/pharos/review_guide.py` — controlled purposes, questions, checklist catalogue, observations and priorities.
- `src/pharos/server.py` — session-scoped read-only review-guide endpoint.
- `src/pharos/web/app.js` — purpose selection, interview, review workspace, evidence navigation and JSON download.
- `src/pharos/web/style.css` — modal, purpose cards, interview and checklist presentation.
- `schemas/pharos-review-guide-v1.schema.json` — deterministic guide contract.
- `schemas/pharos-review-record-v1.schema.json` — user review-record contract.
- `tests/test_review_guide.py` — catalogue, allowlist, evidence, priority and schema tests.
- `docs/REVIEW_GUIDE.md` — current feature documentation and future model boundary.
- `docs/AI_AND_ONLINE_BRIEF.md` — wider product, AI and hosting context.

The complete automated suite currently passes. The interaction has also been exercised in the browser using saved institution data.

## Questions for review

Please provide concrete findings and replacement wording or behaviour where possible.

### User value and task fit

1. Are the purposes recognisable in the language real researchers, librarians, research managers, bibliometricians and data stewards would use?
2. Are important user purposes missing, duplicated or incorrectly combined?
3. Do the three questions materially change what a user needs to inspect, or merely add friction?
4. Would users understand the distinction between “checking OpenAlex for a purpose” and receiving a suitability verdict?
5. Does the guide help users reach evidence efficiently, or does it reproduce the existing report navigation in another form?

### Prioritisation and epistemic risk

6. Is “Review first / Review next / Document before finishing” appropriate language?
7. Could ordering create an unintended impression of severity, quality scoring or methodological endorsement?
8. Should coverage percentages affect priority? If so, should thresholds vary by purpose and measure?
9. What evidence is required before Pharos may say that a check matters for a particular intended use?
10. Where does the copy risk turning missing OpenAlex metadata into a claim about the underlying entity or research?

### Interaction design

11. Is a modal suitable for a potentially extended review, or should the guide become a persistent side panel, report tab or dedicated workspace?
12. Can users easily return from report evidence to the exact checklist item they were reviewing?
13. Should progress survive a refresh or session restart? If so, what is the safest no-account design?
14. Should users be able to revise interview answers without losing judgements?
15. Is a JSON-only review record sufficient, or is a readable HTML/PDF/Word export needed?
16. Does showing semantic evidence IDs help transparency, or create unnecessary technical noise?
17. What accessibility issues do you anticipate with the modal, purpose cards, radio groups, priority labels, notes and evidence navigation?

### Human judgement and record design

18. Are the five statuses sufficient and mutually comprehensible?
19. Should “Checked” be separated from the outcome of the check—for example, observation completed versus acceptable/concern/unresolved?
20. How should the export distinguish user statements, deterministic Pharos observations and any future model-drafted wording?
21. What minimum context is needed for another person to understand or reproduce the review record?

### Appropriate SLM/LLM role

22. Which parts, if any, genuinely benefit from a model?
23. Would free-text intent interpretation improve the experience enough to justify privacy, latency and hallucination risks?
24. Could a browser-local SLM reliably map free text onto controlled purpose and checklist IDs?
25. Could a model adapt explanations without subtly changing protected methodological meanings?
26. What output schema and refusal behaviour should be required?
27. What adversarial tests must pass before model assistance is exposed to users?

## Explicit exclusions for any future model

A model must not:

- Select or change the entity or corpus.
- Calculate counts, denominators, missingness or indicators.
- Rank research performance.
- Decide whether OpenAlex is fit for use.
- Make author merge or split decisions.
- Infer unsupported personal or organisational identity links.
- Attribute an Award to an author or institution without direct evidence.
- Convert missing metadata into real-world absence.
- silently alter deterministic warnings or priorities.
- Generate evidence references that were not supplied and validated.
- Write into the canonical report.

## Requested response format

Please return:

1. **Overall assessment** — whether this is a meaningful product improvement.
2. **Critical misunderstandings or epistemic risks**.
3. **Missing or poorly framed user purposes**.
4. **Interview questions to add, remove or rewrite**.
5. **Review-workspace and navigation improvements**.
6. **Review-record and provenance improvements**.
7. **Accessibility and privacy concerns**.
8. **Where an SLM/LLM adds genuine value, if anywhere**.
9. **A recommended next implementation milestone**, separating changes needed before user testing from later experiments.

For every substantive finding, identify the relevant current wording or behaviour and propose a concrete replacement.
