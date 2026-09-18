"""Deterministic, evidence-linked review guides for completed reports."""

VERSION = "pharos-review-guide-v3"

DEFAULT_THRESHOLDS = {
    ("discovery", "abstract"): 70.0,
    ("discovery", "primary_subject"): 80.0,
    ("publication_reconciliation", "doi"): 80.0,
    ("publication_reconciliation", "primary_source"): 90.0,
    ("institutional_reporting", "primary_subject"): 80.0,
    ("bibliometric_analysis", "primary_subject"): 80.0,
    ("interoperability_assessment", "doi"): 80.0,
}

JOIN_GUIDANCE = {
    "doi": ("OpenAlex plus the receiving system", "CRIS or repository identifier fields and the local fallback-matching rule"),
    "abstract": ("OpenAlex for recorded availability", "Publisher or repository text when abstract-dependent coverage must be validated"),
    "primary_subject": ("OpenAlex for classification coverage", "A reviewed local sample when classification accuracy matters"),
    "primary_source": ("OpenAlex for recorded primary Sources", "CRIS or repository source metadata for reconciliation"),
    "identity": ("OpenAlex as candidate evidence", "ORCID, HR, CV, or other person-authoritative evidence"),
    "general": ("OpenAlex as the evidence view", "The authoritative policy, workflow, local system, or destination named by the use"),
}

BENCHMARKABLE = {
    "doi": "Compare like-for-like recording rates by period and Work type.",
    "abstract": "Compare like-for-like recording rates by period, Work type, and Field.",
    "primary_subject": "Compare classification coverage by period and Work type; accuracy still needs sampling.",
    "primary_source": "Compare source-link coverage by period and Work type.",
}

NEXT_STEPS = {
    "common.scope": "Confirm the selected record, period, and population rule only where the intended scope is still uncertain.",
    "discovery.subjects": "Review unclassified Works and spot-check whether the leading subjects match the portfolio you expect.",
    "discovery.text": "Decide whether searches may omit Works without abstracts; lower the threshold only if title-and-subject searching is acceptable.",
    "discovery.people": "Compare a sample of OpenAlex researchers and affiliations with a current staff, ORCID, or repository list.",
    "reconciliation.doi": "Confirm that the DOI rate meets your matching rule, then define how records without a DOI will be matched.",
    "reconciliation.source": "Compare ambiguous source and version metadata with the repository or CRIS record used for matching.",
    "reconciliation.type": "Map each included OpenAlex Work type to the local publication types and record exclusions or lossy mappings.",
    "reconciliation.records": "Take a sample of unmatched records from both systems and measure missed matches and false matches.",
    "reconciliation.live": "Choose whether the workflow freezes this snapshot or refreshes live records, and record how changes are handled.",
    "reporting.composition": "Compare annual totals and Work-type counts with the repository or CRIS; investigate the largest differences before reporting.",
    "reporting.subjects": "Check how many Works are unclassified and whether their omission could change the subject profile.",
    "reporting.collaboration": "Confirm the affiliation and counting rules required by the report; do not add overlapping country or institution groups.",
    "reporting.funding": "Use the award or finance system for recipient claims; treat OpenAlex funding links only as Work-level acknowledgement evidence.",
    "analysis.denominators": "Write the included and excluded Work population beside every metric you plan to compare.",
    "analysis.subjects": "Inspect unclassified Works and compare the visible subject mix with a known local portfolio or reviewed sample.",
    "analysis.citations": "Confirm that OpenAlex citation links, time window, and field normalisation match the indicator you intend to use.",
    "analysis.comparison": "Rebuild every comparison with the same entity definition, period, Work population, and Pharos version.",
    "funding.direct": "Compare recorded Awards with the institution's award or finance system, including recipient, investigator, amount, and dates.",
    "funding.indirect": "Inspect Work-level funding links separately; the recorded link does not identify which co-author or affiliated institution received or administered the Award.",
    "funding.provenance": "Record which claims come from OpenAlex, Crossref, full text, and local award data, and retain unmatched cases.",
    "access.assertions": "Sample OpenAlex access statuses against the recorded URLs, licences, and accessible versions.",
    "access.locations": "Decide whether the use needs the Version of Record, an accepted manuscript, or any accessible copy, then inspect locations accordingly.",
    "access.policy": "Apply the named policy's dates, version, licence, embargo, and exception rules outside the OpenAlex status label.",
    "interop.identifiers": "Choose authoritative match keys in the destination system and test the fallback rule on records without a DOI.",
    "interop.mapping": "Map every transferred field and controlled value to the destination schema; record null, repeated, unmapped, and lossy values.",
    "interop.provenance": "Include the OpenAlex object, period, retrieval date, query provenance, and Pharos version in every transfer.",
    "interop.destination": "Import a representative sample, inspect validation errors and duplicates, and round-trip it if the destination supports export.",
    "general.coverage": "List the fields your task depends on and compare each recorded rate with an explicit minimum requirement.",
    "general.records": "Open a sample behind each important aggregate and compare it with a source you trust.",
    "adoption.coverage": "List required fields and identifiers, set an acceptable missingness rule for each, and test the current snapshot against it.",
    "adoption.change": "Define refresh frequency, change detection, and exception handling for records that change between snapshots.",
    "adoption.reproduction": "Recreate one result from its saved scope, query provenance, version, and export before adopting the workflow.",
    "adoption.operations": "Test authentication, rate limits, failure recovery, retention, and the fallback route the operational workflow requires.",
    "adoption.validation": "Compare a representative sample with an authoritative local corpus and record missing, extra, and mismatched records.",
}

COMMON_QUESTIONS = (
    {"id": "decision_weight", "label": "How consequential is this use?", "options": (("exploratory", "Exploratory—learning what the data contains"), ("operational", "Operational—recurring work or reporting"), ("high_consequence", "High consequence—people or formal decisions may be affected"))},
    {"id": "tolerance", "label": "How much uncertainty can this use tolerate?", "options": (("flexible", "Flexible—I can inspect and qualify cases"), ("moderate", "Moderate—material limitations must be documented"), ("strict", "Strict—small gaps or ambiguities may matter"))},
)


DIMENSIONS = {
    "doi":"completeness", "abstract":"completeness", "primary_subject":"completeness",
    "primary_source":"completeness", "identity":"accuracy", "general":"fitness_for_use",
}

def item(item_id, title, guidance, destination, refs, evidence="general", priority=2, action=None, record=None, cannot_decide=None, requirement=None):
    return {"id": item_id, "title": title, "guidance": guidance,
            "action": action or "Open the linked evidence. Inspect examples that are present and missing, then compare the pattern with a source or workflow requirement you trust.",
            "record": record or "Record the requirement you applied, what you inspected, and whether a qualification or follow-up is needed.",
            "cannot_decide": cannot_decide or "Pharos cannot decide whether this evidence is sufficient for your organisation, policy, or downstream system.",
            "requirement": requirement or "Define and record an acceptable result for this use, then validate it against relevant local or external evidence.",
            "destination": destination, "evidence_refs": refs, "evidence": evidence, "base_priority": priority}


SCOPE = item("common.scope", "Confirm the report scope", "Check the selected OpenAlex record, period, and population rule if they are not already established by your brief or workflow.", "institution-record", ("report:identity", "report:corpus"), priority=3,
             requirement="The OpenAlex entity, reporting period, and population rule must match the intended analysis. This is a confirmation check, not a percentage threshold.",
             action="Check the OpenAlex ID and name, the start and end years, and the population or affiliation rule. Compare them with the brief, local system, or other source that defines the intended scope.",
             record="Confirm the selected entity and scope, or record the exact mismatch and rebuild the snapshot with the correct record or period.",
             cannot_decide="Pharos can show which scope was saved; it cannot determine whether that scope is the one your work requires.")
LIMITS = item("common.limitations", "Record what the evidence cannot establish", "Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.", "metadata-patterns", ("report:limitations",), priority=3)

PURPOSES = {
    "discovery": {"label": "Find research or researchers", "description": "Check whether OpenAlex is sufficiently recognisable and searchable for discovery.", "report_types": {"institution", "researcher", "source", "publisher"}, "question": {"id": "discovery_basis", "label": "How do you expect people to search?", "options": (("topics", "Subjects or topics"), ("text", "Titles, abstracts or keywords"), ("people", "Researchers or affiliations"))}, "items": (SCOPE,
        item("discovery.subjects", "Check subject classification", "Inspect unclassified Works and whether the Field and Topic mix is recognisable.", "subjects-types", ("measure:coverage.primary_subject", "group:subjects"), "primary_subject", requirement="Enough classified Works for the intended subject search, with missing areas disclosed and recognisable examples inspected."),
        item("discovery.text", "Check abstract availability", "Abstract availability affects text and semantic discovery. Inspect missingness before assuming searches are comprehensive.", "metadata-patterns", ("measure:coverage.abstract",), "abstract", requirement="Enough searchable text for the intended discovery method, with users warned that missing abstracts make results incomplete."),
        item("discovery.people", "Inspect affiliation and identity evidence", "Check whether relevant researchers and affiliations are represented coherently; OpenAlex Author identities are algorithmic.", "researchers", ("identity:authors", "identity:affiliations"), "identity", requirement="Recognisable people and affiliations in a reviewed sample; identity remains a case-level judgement."), LIMITS)},
    "publication_reconciliation": {"label": "Reconcile a publication list or repository", "description": "Compare OpenAlex records with a local publication list or repository.", "report_types": {"institution"}, "question": {"id": "match_basis", "label": "What will you primarily use to match records?", "options": (("doi", "DOI or other identifiers"), ("title", "Titles and dates"), ("mixed", "A mixture of identifiers and metadata"))}, "items": (SCOPE,
        item("reconciliation.doi", "Inspect Works without a DOI", "A missing DOI assertion can make matching harder; it does not mean the Work has no identifier outside OpenAlex.", "metadata-patterns", ("measure:coverage.doi",), "doi", 1, requirement="The locally agreed identifier requirement, conditioned on years and Work types; validate fallback matching where DOI is absent."),
        item("reconciliation.source", "Inspect missing or unexpected primary Sources", "Source gaps and version choices can explain records that do not reconcile cleanly.", "venues", ("measure:coverage.primary_source", "group:sources"), "primary_source", requirement="Source and version metadata sufficient to resolve ambiguous matches in the local reconciliation workflow."),
        item("reconciliation.type", "Compare publication types", "Confirm that OpenAlex Work types correspond to material included in the local system.", "subjects-types", ("group:types",), requirement="A documented, reviewed mapping between OpenAlex Work types and the local system, including lossy or unmapped values."),
        item("reconciliation.records", "Sample unmatched-looking Works", "Compare identifiers, titles, dates, and primary Sources for suspicious years or categories.", "output", ("group:annual", "records:works"), requirement="A defined local validation sample with recorded false-match and missed-match results acceptable to the workflow owner."),
        item("reconciliation.live", "Record saved-versus-live differences", "Live record lists may have changed since the saved aggregate; do not treat them as a corrected snapshot count.", "output", ("report:retrieved_at", "boundary:saved-live"), requirement="A documented snapshot date, refresh rule, and procedure for handling changes during reconciliation."), LIMITS)},
    "institutional_reporting": {"label": "Prepare institutional reporting", "description": "Inspect whether the corpus and metadata can support a defined reporting workflow.", "report_types": {"institution"}, "question": {"id": "report_focus", "label": "What is the main reporting focus?", "options": (("output", "Output volume and composition"), ("collaboration", "Collaboration"), ("funding", "Funding"), ("subjects", "Subject profile"))}, "items": (SCOPE,
        item("reporting.composition", "Check annual output and Work types", "Compare trends and composition with locally recognisable patterns before using totals.", "output", ("group:annual", "group:types"), priority=1),
        item("reporting.subjects", "Check classification coverage", "Subject summaries use classified Works; inspect the excluded denominator and category definitions.", "subjects-types", ("measure:coverage.primary_subject", "group:subjects"), "primary_subject"),
        item("reporting.collaboration", "Review collaboration scope", "Institution and country groups overlap and are not parts of a whole.", "collaboration", ("group:institutions", "group:countries")),
        item("reporting.funding", "Keep funding traces separate", "Work-level acknowledgements do not prove that the institution received or led an Award. If funding evidence matters beyond a summary, use the separate Investigate funding evidence guide.", "funding", ("funding:work-links", "funding:awards")), LIMITS)},
    "bibliometric_analysis": {"label": "Assess data for bibliometric analysis", "description": "Inspect scope, metadata, and citation limitations before analysis.", "report_types": {"institution", "researcher", "funder", "source", "publisher"}, "question": {"id": "analysis_focus", "label": "Which analysis matters most?", "options": (("descriptive", "Descriptive output patterns"), ("citation", "Citation indicators"), ("subjects", "Field or topic analysis"), ("comparison", "Comparison with another entity or snapshot"))}, "items": (SCOPE,
        item("analysis.denominators", "Write down which Works each result includes", "Percentages and totals can describe different sets of Works. Subject results exclude unclassified Works, while institution and country groups can count the same Work more than once.", "metadata-patterns", ("report:population", "measure:coverage"), priority=1,
             action="For every result you plan to use, identify its total population and any Works it excludes. Do not add institution or country groups together: a Work may appear in several groups.",
             record="Record the denominator and exclusions beside each result. Mark a concern if two results use populations that cannot be compared directly."),
        item("analysis.subjects", "Check whether missing classifications could change the story", "Field and Topic summaries only include Works for which OpenAlex records a primary Topic.", "subjects-types", ("measure:coverage.primary_subject", "group:subjects"), "primary_subject",
             action="Check how many Works have no primary Topic, then compare the leading Fields and Topics with what you know about this research portfolio. Look for areas you expected to see but do not.",
             record="Note the number excluded from subject results and whether the visible subject mix looks plausible. If it does not, record which area needs a sample or local comparison."),
        item("analysis.citations", "Inspect citation indicator scope", "Citation links and normalised flags are OpenAlex assertions, not rankings or research quality.", "citations", ("measure:citations",)),
        item("analysis.comparison", "Establish comparability before comparing", "Use identical entity definitions, periods, report versions, and populations.", "institution-record", ("report:identity", "report:corpus", "report:implementation_version")), LIMITS)},
    "researcher_identity": {"label": "Check a researcher’s identity", "description": "Review whether one OpenAlex Author profile represents the intended person.", "report_types": {"researcher"}, "question": {"id": "identity_reason", "label": "What prompted the identity check?", "options": (("confirm", "Confirm a profile before reuse"), ("mixed", "The profile may combine people"), ("duplicate", "Another profile may represent the same person"), ("works", "Particular Works look unexpected"))}, "items": (
        item("identity.selection", "Confirm the selected Author profile", "Check the Author ID, displayed name, and ORCID assertion against a source you trust.", "researcher-identity-panel", ("report:identity",), "identity", 1),
        item("identity.names", "Review printed-name and ORCID evidence", "Look for incompatible names and multiple work-level ORCID assertions.", "researcher-identity-panel", ("identity:name-variants", "identity:orcids"), "identity", 1),
        item("identity.affiliations", "Review affiliation history", "Check whether institutions and years form a recognisable history. Missing affiliations remain unknown.", "researcher-affiliations-panel", ("identity:affiliations",), "identity"),
        item("identity.coauthors", "Inspect recurring co-authors", "Recognisable collaborators and discontinuities can inform review, but linked profiles may be imperfect.", "researcher-identity-panel", ("identity:coauthors",), "identity"),
        item("identity.resolution", "Review merge and split signals separately", "Candidates and deterministic signals are prompts for inspection, not automatic identity decisions.", "researcher-resolution-panel", ("identity:merge-candidates", "identity:split-signals", "records:works"), "identity", 1), LIMITS)},
    "funding_evidence": {"label": "Investigate funding evidence", "description": "Separate direct Award assertions from indirect Work-level acknowledgements.", "report_types": {"institution", "researcher", "funder"}, "question": {"id": "funding_question", "label": "What are you trying to establish?", "options": (("awards", "Which Awards are recorded"), ("outputs", "Which outputs acknowledge funding"), ("recipient", "Whether an entity received or led funding"))}, "items": (SCOPE,
        item("funding.direct", "Inspect direct Award records", "Check which fields explicitly name a recipient, investigator, amount or date; absent fields remain unknown.", "funding", ("funding:awards",), priority=1),
        item("funding.indirect", "Inspect Work-level acknowledgements separately", "The funding link associates the Work with a funder or Award but does not assign recipient, investigator, or administering roles to its authors or affiliations.", "funding", ("funding:work-links", "records:works"), priority=1),
        item("funding.provenance", "Record provenance and incompleteness", "Funding evidence cannot establish a complete administrative portfolio.", "funding", ("funding:provenance", "report:limitations")), LIMITS)},
    "open_access_evidence": {"label": "Inspect open-access evidence", "description": "Inspect OpenAlex access and location assertions without treating them as a policy-compliance decision.", "report_types": {"institution"}, "question": {"id": "access_question", "label": "What do you need to understand?", "options": (("availability", "Recorded free-to-read availability"), ("versions", "Repository and publication versions"), ("policy", "Evidence for a separate policy review"))}, "items": (SCOPE,
        item("access.assertions", "Inspect access-status assertions", "Check recorded access statuses and unknowns. These are changing OpenAlex assertions, not a compliance result or statement of reuse rights.", "outputs-access", ("measure:open_access",), priority=1),
        item("access.locations", "Inspect Sources and versions", "Primary locations and other recorded versions answer different questions about where a Work can be accessed.", "venues", ("group:sources", "records:versions")),
        item("access.policy", "Apply the relevant policy separately", "Record the policy, dates, version requirements, licences, and exceptions outside Pharos before making a compliance judgement.", "outputs-access", ("report:limitations",)), LIMITS)},
    "source_publisher_scope": {"label": "Examine journal or publisher coverage", "description": "Inspect primary-location and publisher-lineage scope before using source aggregates.", "report_types": {"source", "publisher"}, "question": {"id": "source_question", "label": "What matters most?", "options": (("inventory", "Title or source inventory"), ("output", "Output patterns"), ("access", "Open-access assertions"), ("publisher", "Publisher relationships"))}, "items": (SCOPE,
        item("source.primary", "Confirm primary-location scope", "Source reports use the Work's primary location; alternative versions are outside this source population.", "overview", ("report:corpus", "group:sources"), priority=1),
        item("source.longtail", "Account for leading groups and the long tail", "Ranked Sources or publishers are leading returned groups, not an exhaustive inventory.", "venues", ("group:sources", "group:publishers")),
        item("source.access", "Inspect open-access assertions", "OpenAlex access status is a changing assertion and does not establish reuse rights.", "outputs-access", ("measure:open_access",)), LIMITS)},
    "interoperability_assessment": {"label": "Prepare data for another system", "description": "Assess whether the evidence can be mapped, transferred, and validated in a repository, CRIS or data pipeline.", "report_types": {"institution", "researcher", "source", "funder", "publisher"}, "question": {"id": "destination_type", "label": "Where does the data need to work?", "options": (("repository", "Institutional repository"), ("cris", "CRIS or research information system"), ("analysis", "Analysis pipeline or data warehouse"), ("unknown", "Destination not chosen yet"))}, "items": (SCOPE,
        item("interop.identifiers", "Define identifiers used for matching", "Inspect identifier presence and document which identifiers are authoritative, optional or unavailable in the receiving system.", "metadata-patterns", ("measure:coverage.doi", "report:identity"), "doi", 1, requirement="A documented identifier and fallback-matching rule that the receiving system can apply without silently merging distinct records."),
        item("interop.mapping", "Map fields and controlled values", "Map Pharos fields, OpenAlex concepts, and null values to the destination schema; record transformations and information loss.", "institution-record", ("report:provenance", "report:corpus"), priority=1, requirement="A reviewed field-and-vocabulary mapping with explicit handling for null, repeated, unmapped, and lossy values."),
        item("interop.provenance", "Preserve scope and provenance", "Keep entity, period, retrieval time, implementation version, and upstream provenance with transferred data.", "institution-record", ("report:identity", "report:retrieved_at", "report:implementation_version", "report:provenance"), requirement="Enough machine-readable provenance to identify the source, scope, version, and retrieval date of every transfer."),
        item("interop.destination", "Run a destination-system test", "Import a representative sample, inspect errors and duplicates, then verify how records are stored and exported.", "output", ("records:works",), priority=1, requirement="A recorded test import and, where supported, round trip using representative records and agreed acceptance criteria.", cannot_decide="Pharos cannot predict or certify the receiving system's validation, deduplication, transformation, or export behaviour."), LIMITS)},
    "general_assessment": {"label": "Another intended use", "description": "Start with a general evidence inspection when no specialist guide matches.", "report_types": {"institution", "researcher", "source", "funder", "publisher"}, "question": {"id": "evidence_focus", "label": "Which evidence matters most?", "options": (("identifiers", "Identifiers and record matching"), ("subjects", "Subjects and classifications"), ("people", "People and affiliations"), ("funding", "Funding"), ("unknown", "I am not sure yet"))}, "items": (SCOPE,
        item("general.coverage", "Review relevant missing metadata", "Decide which missing fields could affect the intended task.", "metadata-patterns", ("measure:coverage",), priority=1),
        item("general.records", "Inspect supporting records", "Open records behind important aggregates before relying on them.", "output", ("records:works",)), LIMITS)},
    "adoption_due_diligence": {"label": "Evaluate OpenAlex before adopting it for ongoing use", "description": "Document evidence and unresolved operational risks before relying on OpenAlex in a continuing workflow.", "report_types": {"institution"}, "question": {"id": "adoption_role", "label": "What role would OpenAlex have?", "options": (("reference", "Reference or discovery source"), ("supplement", "Supplement to a local system"), ("primary", "Primary operational data source"))}, "items": (SCOPE,
        item("adoption.coverage", "Define required fields and acceptable gaps", "Record which identifiers and metadata the workflow requires; inspect their counts and denominators without treating them as a readiness score.", "metadata-patterns", ("measure:coverage",), priority=1),
        item("adoption.change", "Plan for changing upstream data", "Saved reports are dated snapshots while live OpenAlex results can change. Define refresh, comparison, and exception-handling procedures.", "output", ("report:retrieved_at", "boundary:saved-live"), priority=1),
        item("adoption.reproduction", "Test reproducibility and provenance", "Confirm that report version, entity, scope, queries, and exports provide enough context to reproduce the intended workflow.", "institution-record", ("report:implementation_version", "report:corpus", "report:provenance")),
        item("adoption.operations", "Assess operational dependencies", "Document authentication, rate budgets, availability, retention, and the independent local route needed by the proposed workflow.", "institution-record", ("report:limitations",)),
        item("adoption.validation", "Compare against authoritative local evidence", "Use a defined sample or local corpus to measure mismatches; this Pharos report alone cannot approve adoption.", "output", ("records:works",)), LIMITS)},
}


def _report_type(report): return report.get("report_type") or "institution"
def _question_json(q): return {"id": q["id"], "label": q["label"], "options": [{"id": key, "label": label} for key, label in q["options"]]}


def available_purposes(report_type):
    return [{"id": key, "label": value["label"], "description": value["description"]} for key, value in PURPOSES.items() if report_type in value["report_types"]]


def questions_for_purpose(report_type, purpose_id):
    purpose = PURPOSES.get(purpose_id)
    if not purpose or report_type not in purpose["report_types"]: raise ValueError("This review purpose is not available for this report.")
    return [_question_json(q) for q in (*COMMON_QUESTIONS, purpose["question"])]


def _coverage(report, key):
    row = (report.get("coverage") or {}).get(key)
    if not isinstance(row, dict): return None
    count, denominator, percentage = row.get("count"), row.get("denominator"), row.get("percentage")
    if not isinstance(count, int) or not isinstance(denominator, int): return None
    missing = max(0, denominator - count)
    summary = f"{count:,} of {denominator:,} Works have this OpenAlex assertion; {missing:,} do not."
    if isinstance(percentage, (int, float)): summary = f"{count:,} of {denominator:,} Works ({percentage:.1f}%) have this OpenAlex assertion; {missing:,} do not."
    return {"count": count, "denominator": denominator, "percentage": percentage, "missing": missing, "summary": summary}


def _identity_observation(report):
    evidence = report.get("identity_evidence") or {}; variants=evidence.get("name_variants") or []; orcids=evidence.get("raw_orcids") or []
    return {"summary": f"The saved profile contains {len(variants):,} printed-name variants and {len(orcids):,} distinct work-level ORCID assertions.", "name_variant_count": len(variants), "work_level_orcid_count": len(orcids)}


def _scope_observation(report):
    identity=report.get("identity") or {}; corpus=report.get("corpus") or {}; period=corpus.get("period") or report.get("period") or {}
    start=period.get("from") or period.get("start"); end=period.get("to") or period.get("end")
    years=f"{str(start)[:4]}–{str(end)[:4]}" if start and end else "the saved period"
    name=identity.get("display_name") or identity.get("name") or "the selected record"
    identifier=identity.get("id") or "no identifier recorded"
    return {"summary":f"This snapshot records {name} ({identifier}) for {years}. That makes the scope inspectable and reproducible; it does not confirm that the record or period is correct for your intended use.","identity_id":identity.get("id"),"period":period}


def _measurement_definition(report, entry, observation):
    corpus=report.get("corpus") or {}; evidence=entry["evidence"]
    if observation and "denominator" in observation:
        formula=f"Works with the {evidence.replace('_',' ')} assertion / eligible Works in this report"
        denominator="Eligible Works in the saved report scope; presence does not establish correctness."
        unit="percentage"
    elif evidence=="identity":
        formula="Count of identity evidence retained on the selected OpenAlex Author profile"
        denominator="Case-level evidence; no population percentage is used."
        unit="count"
    else:
        formula="Structured inspection of the evidence references listed for this check"
        denominator="No universal numeric denominator is defined for this check."
        unit="categorical"
    return {"id":evidence,"label":evidence.replace("_"," ").title(),"formula":formula,
            "denominator_note":denominator,"unit":unit,"scope":corpus.get("period") or report.get("period"),
            "retrieved_at":report.get("retrieved_at"),"implementation_version":report.get("implementation_version")}


def _requirement(entry, purpose_id):
    case_level=entry["evidence"]=="identity" or purpose_id in ("researcher_identity","funding_evidence")
    numeric=DEFAULT_THRESHOLDS.get((purpose_id,entry["evidence"]))
    return {"kind":"case_level_validation" if case_level else "validation_rule","default":entry["requirement"],
            "current":entry["requirement"],"numeric_default":numeric,"numeric_current":numeric,"unit":"percentage" if entry["evidence"] in ("doi","abstract","primary_subject","primary_source") else None,
            "is_override":False,"status_ceiling":"validation_needed" if case_level else None}


def _interoperability(entry):
    authority, required_join=JOIN_GUIDANCE.get(entry["evidence"],JOIN_GUIDANCE["general"])
    return {"openalex_role":authority,"required_join":required_join,
            "openalex_sufficient":entry["evidence"] in ("doi","abstract","primary_subject","primary_source"),
            "validation":"Aggregate presence can be assessed automatically; correctness, policy compliance, and destination behaviour require the named join."}


def _benchmark(entry):
    note=BENCHMARKABLE.get(entry["evidence"])
    return {"eligible":bool(note),"status":"not_calculated","value":None,
            "note":note or "No defensible aggregate benchmark is defined for this evidence."}


def _provisional_status(item):
    observed=item.get("observed") or {}; requirement=item["requirement"]; threshold=requirement.get("numeric_current")
    if item.get("id")=="common.scope": return "validation_needed"
    if requirement.get("status_ceiling")=="validation_needed": return "validation_needed"
    if isinstance(threshold,(int,float)) and isinstance(observed.get("percentage"),(int,float)):
        return "meets_configured_requirement" if observed["percentage"]>=threshold else "does_not_meet_configured_requirement"
    return "validation_needed"


def _readiness(items):
    essential=[item for item in items if item["materiality"]["current"]=="high"]
    relevant=[item for item in items if item["materiality"]["current"]=="moderate"]
    if any(item["provisional_status"]=="does_not_meet_configured_requirement" for item in essential): status="not_supported"
    elif any(item["provisional_status"] in ("validation_needed","not_measured") for item in essential): status="validation_needed"
    elif any(item["provisional_status"]!="meets_configured_requirement" for item in relevant): status="ready_with_limitations"
    else: status="ready"
    labels={"ready":"Ready","ready_with_limitations":"Ready with limitations","validation_needed":"Validation needed","not_supported":"Not supported by this snapshot"}
    return {"status":status,"label":labels[status],"essential_checks":len(essential),
            "note":"Provisional result from saved OpenAlex evidence and configured requirements; user validation and recorded overrides may change it."}


def _priority(entry, _observation, answers):
    score=entry["base_priority"]
    if answers.get("tolerance")=="strict" or answers.get("decision_weight")=="high_consequence": score=max(1,score-1)
    return score


def build_review_guide(report, purpose_id, answers=None):
    if not isinstance(report,dict): raise ValueError("A completed report is required.")
    report_type=_report_type(report); answers=answers or {}; purpose=PURPOSES.get(purpose_id)
    if not purpose or report_type not in purpose["report_types"]: raise ValueError("This review purpose is not available for this report.")
    questions=questions_for_purpose(report_type,purpose_id); valid={q["id"]:{o["id"] for o in q["options"]} for q in questions}
    if set(answers)-set(valid) or any(value not in valid[key] for key,value in answers.items()): raise ValueError("The review answers are not valid for this purpose.")
    identity=report.get("identity") or {}; corpus=report.get("corpus") or {}; rows=[]
    for entry in purpose["items"]:
        observation=_scope_observation(report) if entry["id"]=="common.scope" else _coverage(report,entry["evidence"]) if entry["evidence"] in (report.get("coverage") or {}) else _identity_observation(report) if entry["evidence"]=="identity" and report_type=="researcher" else None
        materiality="high" if entry["base_priority"]==1 else "moderate" if entry["base_priority"]==2 else "low"
        row={k:v for k,v in entry.items() if k not in ("evidence","base_priority","requirement")}|{
            "priority":_priority(entry,observation,answers),"dimension":DIMENSIONS.get(entry["evidence"],"fitness_for_use"),
            "measurement_definition":_measurement_definition(report,entry,observation),"observed":observation,"observation":observation,
            "requirement":_requirement(entry,purpose_id),"materiality":{"default":materiality,"current":materiality,"is_override":False},
            "interoperability":_interoperability(entry),"benchmark":_benchmark(entry),
            "matrix_key":entry["evidence"] if entry["evidence"]!="general" else entry["id"],
            "next_step":NEXT_STEPS.get(entry["id"],entry["action"])}
        row["provisional_status"]=_provisional_status(row);rows.append(row)
    rows.sort(key=lambda row:row["priority"])
    interoperability=[
        {"id":"export_schema","label":"Pharos export schema conformance","test_type":"automatic","status":"available","detail":"Versioned JSON and review-record schemas can be validated automatically."},
        {"id":"persistent_identifiers","label":"Persistent identifier presence","test_type":"automatic","status":"inspect","detail":"Measure the identifiers required by the destination; presence does not prove that a link is correct."},
        {"id":"destination_mapping","label":"Destination field and vocabulary mapping","test_type":"destination_specific","status":"not_tested","detail":"Requires a documented mapping and a test import into the receiving repository, CRIS, or other system."},
        {"id":"round_trip","label":"Destination import and round trip","test_type":"destination_specific","status":"not_tested","detail":"Pharos cannot certify how another system stores, deduplicates, or re-exports these records."},
    ]
    return {"schema_version":VERSION,"generator":"deterministic","purpose":{"id":purpose_id,"label":purpose["label"]},"answers":answers,"report":{"type":report_type,"identity_id":identity.get("id"),"identity_name":identity.get("display_name"),"retrieved_at":report.get("retrieved_at"),"implementation_version":report.get("implementation_version"),"period":corpus.get("period") or report.get("period")},"introduction":f"{len(rows)} checks, sequenced for {purpose['label'].lower()}.","items":rows,"readiness":_readiness(rows),"interoperability":interoperability,"allowed_statuses":["not_checked","meets_configured_requirement","validation_needed","does_not_meet_configured_requirement","not_measured","not_applicable"],"limitations":["Readiness is a provisional, rule-based result for this configured use, not a general data-quality score.","High coverage describes OpenAlex's recorded data, not whether it is sufficient for every use.","Case-level, policy, and destination-system claims remain validation needed until the required external evidence is recorded.","Configured requirements, overrides, and notes retain user provenance.","Live drill-downs may differ from the dated saved report."]}
