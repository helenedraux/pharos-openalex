# Readiness review copy inventory

Generated from the user-facing purpose, check, guidance, and next-action copy in `src/pharos/review_guide.py`.

## Find research or researchers

Check whether OpenAlex is sufficiently recognisable and searchable for discovery.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Check subject classification**
  - Guidance: Inspect unclassified Works and whether the Field and Topic mix is recognisable.
  - Next action: Review unclassified Works and spot-check whether the leading subjects match the portfolio you expect.
- **Check abstract availability**
  - Guidance: Abstract availability affects text and semantic discovery. Inspect missingness before assuming searches are comprehensive.
  - Next action: Decide whether searches may omit Works without abstracts; lower the threshold only if title-and-subject searching is acceptable.
- **Inspect affiliation and identity evidence**
  - Guidance: Check whether relevant researchers and affiliations are represented coherently; OpenAlex Author identities are algorithmic.
  - Next action: Compare a sample of OpenAlex researchers and affiliations with a current staff, ORCID, or repository list.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Reconcile a publication list or repository

Compare OpenAlex records with a local publication list or repository.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Inspect Works without a DOI**
  - Guidance: A missing DOI assertion can make matching harder; it does not mean the Work has no identifier outside OpenAlex.
  - Next action: Confirm that the DOI rate meets your matching rule, then define how records without a DOI will be matched.
- **Inspect missing or unexpected primary Sources**
  - Guidance: Source gaps and version choices can explain records that do not reconcile cleanly.
  - Next action: Compare ambiguous source and version metadata with the repository or CRIS record used for matching.
- **Compare publication types**
  - Guidance: Confirm that OpenAlex Work types correspond to material included in the local system.
  - Next action: Map each included OpenAlex Work type to the local publication types and record exclusions or lossy mappings.
- **Sample unmatched-looking Works**
  - Guidance: Compare identifiers, titles, dates, and primary Sources for suspicious years or categories.
  - Next action: Take a sample of unmatched records from both systems and measure missed matches and false matches.
- **Record saved-versus-live differences**
  - Guidance: Live record lists may have changed since the saved aggregate; do not treat them as a corrected snapshot count.
  - Next action: Choose whether the workflow freezes this snapshot or refreshes live records, and record how changes are handled.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Prepare institutional reporting

Inspect whether the corpus and metadata can support a defined reporting workflow.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Check annual output and Work types**
  - Guidance: Compare trends and composition with locally recognisable patterns before using totals.
  - Next action: Compare annual totals and Work-type counts with the repository or CRIS; investigate the largest differences before reporting.
- **Check classification coverage**
  - Guidance: Subject summaries use classified Works; inspect the excluded denominator and category definitions.
  - Next action: Check how many Works are unclassified and whether their omission could change the subject profile.
- **Review collaboration scope**
  - Guidance: Institution and country groups overlap and are not parts of a whole.
  - Next action: Confirm the affiliation and counting rules required by the report; do not add overlapping country or institution groups.
- **Keep funding traces separate**
  - Guidance: Work-level acknowledgements do not prove that the institution received or led an Award. If funding evidence matters beyond a summary, use the separate Investigate funding evidence guide.
  - Next action: Use the award or finance system for recipient claims; treat OpenAlex funding links only as Work-level acknowledgement evidence.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Assess data for bibliometric analysis

Inspect scope, metadata, and citation limitations before analysis.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Write down which Works each result includes**
  - Guidance: Percentages and totals can describe different sets of Works. Subject results exclude unclassified Works, while institution and country groups can count the same Work more than once.
  - Next action: Write the included and excluded Work population beside every metric you plan to compare.
- **Check whether missing classifications could change the story**
  - Guidance: Field and Topic summaries only include Works for which OpenAlex records a primary Topic.
  - Next action: Inspect unclassified Works and compare the visible subject mix with a known local portfolio or reviewed sample.
- **Inspect citation indicator scope**
  - Guidance: Citation links and normalised flags are OpenAlex assertions, not rankings or research quality.
  - Next action: Confirm that OpenAlex citation links, time window, and field normalisation match the indicator you intend to use.
- **Establish comparability before comparing**
  - Guidance: Use identical entity definitions, periods, report versions, and populations.
  - Next action: Rebuild every comparison with the same entity definition, period, Work population, and Pharos version.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Check a researcher’s identity

Review whether one OpenAlex Author profile represents the intended person.

- **Confirm the selected Author profile**
  - Guidance: Check the Author ID, displayed name, and ORCID assertion against a source you trust.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Review printed-name and ORCID evidence**
  - Guidance: Look for incompatible names and multiple work-level ORCID assertions.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Review affiliation history**
  - Guidance: Check whether institutions and years form a recognisable history. Missing affiliations remain unknown.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Inspect recurring co-authors**
  - Guidance: Recognisable collaborators and discontinuities can inform review, but linked profiles may be imperfect.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Review merge and split signals separately**
  - Guidance: Candidates and deterministic signals are prompts for inspection, not automatic identity decisions.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Investigate funding evidence

Separate direct Award assertions from indirect Work-level acknowledgements.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Inspect direct Award records**
  - Guidance: Check which fields explicitly name a recipient, investigator, amount or date; absent fields remain unknown.
  - Next action: Compare recorded Awards with the institution's award or finance system, including recipient, investigator, amount, and dates.
- **Inspect Work-level acknowledgements separately**
  - Guidance: The funding link associates the Work with a funder or Award but does not assign recipient, investigator, or administering roles to its authors or affiliations.
  - Next action: Inspect Work-level funding links separately; the recorded link does not identify which co-author or affiliated institution received or administered the Award.
- **Record provenance and incompleteness**
  - Guidance: Funding evidence cannot establish a complete administrative portfolio.
  - Next action: Record which claims come from OpenAlex, Crossref, full text, and local award data, and retain unmatched cases.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Inspect open-access evidence

Inspect OpenAlex access and location assertions without treating them as a policy-compliance decision.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Inspect access-status assertions**
  - Guidance: Check recorded access statuses and unknowns. These are changing OpenAlex assertions, not a compliance result or statement of reuse rights.
  - Next action: Sample OpenAlex access statuses against the recorded URLs, licences, and accessible versions.
- **Inspect Sources and versions**
  - Guidance: Primary locations and other recorded versions answer different questions about where a Work can be accessed.
  - Next action: Decide whether the use needs the Version of Record, an accepted manuscript, or any accessible copy, then inspect locations accordingly.
- **Apply the relevant policy separately**
  - Guidance: Record the policy, dates, version requirements, licences, and exceptions outside Pharos before making a compliance judgement.
  - Next action: Apply the named policy's dates, version, licence, embargo, and exception rules outside the OpenAlex status label.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Examine journal or publisher coverage

Inspect primary-location and publisher-lineage scope before using source aggregates.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Confirm primary-location scope**
  - Guidance: Source reports use the Work's primary location; alternative versions are outside this source population.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Account for leading groups and the long tail**
  - Guidance: Ranked Sources or publishers are leading returned groups, not an exhaustive inventory.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Inspect open-access assertions**
  - Guidance: OpenAlex access status is a changing assertion and does not establish reuse rights.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Prepare data for another system

Assess whether the evidence can be mapped, transferred, and validated in a repository, CRIS or data pipeline.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Define identifiers used for matching**
  - Guidance: Inspect identifier presence and document which identifiers are authoritative, optional or unavailable in the receiving system.
  - Next action: Choose authoritative match keys in the destination system and test the fallback rule on records without a DOI.
- **Map fields and controlled values**
  - Guidance: Map Pharos fields, OpenAlex concepts, and null values to the destination schema; record transformations and information loss.
  - Next action: Map every transferred field and controlled value to the destination schema; record null, repeated, unmapped, and lossy values.
- **Preserve scope and provenance**
  - Guidance: Keep entity, period, retrieval time, implementation version, and upstream provenance with transferred data.
  - Next action: Include the OpenAlex object, period, retrieval date, query provenance, and Pharos version in every transfer.
- **Run a destination-system test**
  - Guidance: Import a representative sample, inspect errors and duplicates, then verify how records are stored and exported.
  - Next action: Import a representative sample, inspect validation errors and duplicates, and round-trip it if the destination supports export.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Another intended use

Start with a general evidence inspection when no specialist guide matches.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Review relevant missing metadata**
  - Guidance: Decide which missing fields could affect the intended task.
  - Next action: List the fields your task depends on and compare each recorded rate with an explicit minimum requirement.
- **Inspect supporting records**
  - Guidance: Open records behind important aggregates before relying on them.
  - Next action: Open a sample behind each important aggregate and compare it with a source you trust.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.

## Evaluate OpenAlex before adopting it for ongoing use

Document evidence and unresolved operational risks before relying on OpenAlex in a continuing workflow.

- **Confirm the report scope**
  - Guidance: Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.
  - Next action: Confirm the selected record, period, and population rule only where the intended scope is still uncertain.
- **Define required fields and acceptable gaps**
  - Guidance: Record which identifiers and metadata the workflow requires; inspect their counts and denominators without treating them as a readiness score.
  - Next action: List required fields and identifiers, set an acceptable missingness rule for each, and test the current snapshot against it.
- **Plan for changing upstream data**
  - Guidance: Saved reports are dated snapshots while live OpenAlex results can change. Define refresh, comparison, and exception-handling procedures.
  - Next action: Define refresh frequency, change detection, and exception handling for records that change between snapshots.
- **Test reproducibility and provenance**
  - Guidance: Confirm that report version, entity, scope, queries, and exports provide enough context to reproduce the intended workflow.
  - Next action: Recreate one result from its saved scope, query provenance, version, and export before adopting the workflow.
- **Assess operational dependencies**
  - Guidance: Document authentication, rate budgets, availability, retention, and the independent local route needed by the proposed workflow.
  - Next action: Test authentication, rate limits, failure recovery, retention, and the fallback route the operational workflow requires.
- **Compare against authoritative local evidence**
  - Guidance: Use a defined sample or local corpus to measure mismatches; this Pharos report alone cannot approve adoption.
  - Next action: Compare a representative sample with an authoritative local corpus and record missing, extra, and mismatched records.
- **Record what the evidence cannot establish**
  - Guidance: Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.
  - Next action: Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.


