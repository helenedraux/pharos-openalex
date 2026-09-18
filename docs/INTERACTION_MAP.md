# Pharos interaction map

## Landing page

The user chooses one entity type, searches for a record, verifies identifying context, and builds a saved report. The order is:

1. Research organisation
2. Individual researcher
3. Funder
4. Journal or source
5. Publisher

Only institution reports expose a year range. Other reports cover the complete OpenAlex-linked history.

Search accepts entity-specific identifiers as well as names. A candidate must be selected before report generation becomes available.

## Institution

The saved-summary view leads with a coverage verdict and metadata-quality flags, then opens a larger report with tabs for overview, gaps, subjects, access, citations, sources and versions, collaboration, funding, researchers, and affiliations.

Some actions are live lookups layered onto a dated saved aggregate. These are visually labelled and excluded from the saved snapshot export. The Funding view combines saved work-level funder coverage with a live lookup of Award records that explicitly name the institution.

## Researcher

The Identity tab is primary. It shows names, ORCIDs, co-authors, affiliation history, and evidence relevant to profile merging or splitting. Other tabs cover identity-resolution proposals, career shape, access and citations, affiliations, and detailed Award records linked to the profile's works.

Award occurrence on a Work does not prove that the selected researcher was an investigator.

## Funder

Evidence overview is the first and default tab. Award records provides two explicitly ranked views: Awards with the largest recorded amounts and Award records linked to the most outputs. These are exploration lists, not statistical samples, and Pharos does not use them to estimate field completeness. Separate tabs cover research themes, institutions, outputs, access, citations, and the OpenAlex Funder record. The Institutions tab reports yearly authorship-affiliation coverage and the most frequent affiliated institution on linked Works; neither is recipient evidence.

Award data varies substantially by provenance. Missing amount, investigator, institution, date, or title is unknown rather than zero.

## Journal or source

Overview is primary, followed by Subjects, Access and citations, and Source record. Scope uses the Work's OpenAlex primary location. A Source can be a journal, repository, conference series, book series, or platform.

## Publisher

Overview is primary, followed by Sources, Subjects, Access and citations, and Publisher record. Scope uses the selected publisher's recorded lineage on the Work's primary source. Sources are leading returned groups rather than a complete title inventory.

## Shared states

- Loading: the current report job exposes concise progress messages.
- Saved snapshot: the completed report is reused when entity, scope, and implementation version match.
- Daily response cache: successful public API responses are keyed by request parameters and UTC date.
- Error: upstream details and local paths are suppressed; retry reuses successful cached queries.
- Export: PDF, Excel, CSV, and JSON are generated from the completed report held by the current local session.
- New report: returns to the landing page without deleting saved reports or API-response cache.

## Known review issue

The Saved Snapshots landing list currently exposes institution reports only, although completed researcher, funder, source, and publisher report files are also cached on disk. This is a discoverability limitation, not data loss.
