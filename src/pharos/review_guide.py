"""Deterministic, evidence-linked review guides for completed reports."""

VERSION = "pharos-review-guide-v1"

COMMON_QUESTIONS = (
    {"id": "decision_weight", "label": "How consequential is this use?", "options": (("exploratory", "Exploratory—learning what the data contains"), ("operational", "Operational—recurring work or reporting"), ("high_consequence", "High consequence—people or formal decisions may be affected"))},
    {"id": "tolerance", "label": "How much uncertainty can this use tolerate?", "options": (("flexible", "Flexible—I can inspect and qualify cases"), ("moderate", "Moderate—material limitations must be documented"), ("strict", "Strict—small gaps or ambiguities may matter"))},
)


def item(item_id, title, guidance, destination, refs, evidence="general", priority=2, action=None, record=None):
    return {"id": item_id, "title": title, "guidance": guidance,
            "action": action or "Open the linked evidence and compare what Pharos shows with the requirements of your intended use.",
            "record": record or "Note whether the evidence is usable as shown, needs a qualification, or requires follow-up.",
            "destination": destination, "evidence_refs": refs, "evidence": evidence, "base_priority": priority}


SCOPE = item("common.scope", "Confirm identity, population and scope", "Check that the exact OpenAlex record, dates and corpus definition match what you intend to study.", "institution-record", ("report:identity", "report:corpus"), priority=1)
LIMITS = item("common.limitations", "Record what the evidence cannot establish", "Document limitations requiring local knowledge or another authoritative source. Missing metadata is not evidence of real-world absence.", "metadata-patterns", ("report:limitations",), priority=3)

PURPOSES = {
    "discovery": {"label": "Find research or researchers", "description": "Check whether OpenAlex is sufficiently recognisable and searchable for discovery.", "report_types": {"institution", "researcher", "source", "publisher"}, "question": {"id": "discovery_basis", "label": "How do you expect people to search?", "options": (("topics", "Subjects or topics"), ("text", "Titles, abstracts or keywords"), ("people", "Researchers or affiliations"))}, "items": (SCOPE,
        item("discovery.subjects", "Check subject classification", "Inspect unclassified Works and whether the Field and Topic mix is recognisable.", "subjects-types", ("measure:coverage.primary_subject", "group:subjects"), "primary_subject"),
        item("discovery.text", "Check abstract availability", "Abstract availability affects text and semantic discovery. Inspect missingness before assuming searches are comprehensive.", "metadata-patterns", ("measure:coverage.abstract",), "abstract"),
        item("discovery.people", "Inspect affiliation and identity evidence", "Check whether relevant researchers and affiliations are represented coherently; OpenAlex Author identities are algorithmic.", "researchers", ("identity:authors", "identity:affiliations"), "identity"), LIMITS)},
    "publication_reconciliation": {"label": "Reconcile a publication list or repository", "description": "Compare OpenAlex records with a local publication list or repository.", "report_types": {"institution"}, "question": {"id": "match_basis", "label": "What will you primarily use to match records?", "options": (("doi", "DOI or other identifiers"), ("title", "Titles and dates"), ("mixed", "A mixture of identifiers and metadata"))}, "items": (SCOPE,
        item("reconciliation.doi", "Inspect Works without a DOI", "A missing DOI assertion can make matching harder; it does not mean the Work has no identifier outside OpenAlex.", "metadata-patterns", ("measure:coverage.doi",), "doi", 1),
        item("reconciliation.source", "Inspect missing or unexpected primary Sources", "Source gaps and version choices can explain records that do not reconcile cleanly.", "venues", ("measure:coverage.primary_source", "group:sources"), "primary_source"),
        item("reconciliation.type", "Compare publication types", "Confirm that OpenAlex Work types correspond to material included in the local system.", "subjects-types", ("group:types",)),
        item("reconciliation.records", "Sample unmatched-looking Works", "Compare identifiers, titles, dates and primary Sources for suspicious years or categories.", "output", ("group:annual", "records:works")),
        item("reconciliation.live", "Record saved-versus-live differences", "Live record lists may have changed since the saved aggregate; do not treat them as a corrected snapshot count.", "output", ("report:retrieved_at", "boundary:saved-live")), LIMITS)},
    "institutional_reporting": {"label": "Prepare institutional reporting", "description": "Inspect whether the corpus and metadata can support a defined reporting workflow.", "report_types": {"institution"}, "question": {"id": "report_focus", "label": "What is the main reporting focus?", "options": (("output", "Output volume and composition"), ("collaboration", "Collaboration"), ("funding", "Funding"), ("subjects", "Subject profile"))}, "items": (SCOPE,
        item("reporting.composition", "Check annual output and Work types", "Compare trends and composition with locally recognisable patterns before using totals.", "output", ("group:annual", "group:types"), priority=1),
        item("reporting.subjects", "Check classification coverage", "Subject summaries use classified Works; inspect the excluded denominator and category definitions.", "subjects-types", ("measure:coverage.primary_subject", "group:subjects"), "primary_subject"),
        item("reporting.collaboration", "Review collaboration scope", "Institution and country groups overlap and are not parts of a whole.", "collaboration", ("group:institutions", "group:countries")),
        item("reporting.funding", "Keep funding traces separate", "Work-level acknowledgements do not prove that the institution received or led an Award. If funding evidence matters beyond a summary, use the separate Investigate funding evidence guide.", "funding", ("funding:work-links", "funding:awards")), LIMITS)},
    "bibliometric_analysis": {"label": "Assess data for bibliometric analysis", "description": "Inspect scope, metadata and citation limitations before analysis.", "report_types": {"institution", "researcher", "funder", "source", "publisher"}, "question": {"id": "analysis_focus", "label": "Which analysis matters most?", "options": (("descriptive", "Descriptive output patterns"), ("citation", "Citation indicators"), ("subjects", "Field or topic analysis"), ("comparison", "Comparison with another entity or snapshot"))}, "items": (SCOPE,
        item("analysis.denominators", "Write down which Works each result includes", "Percentages and totals can describe different sets of Works. Subject results exclude unclassified Works, while institution and country groups can count the same Work more than once.", "metadata-patterns", ("report:population", "measure:coverage"), priority=1,
             action="For every result you plan to use, identify its total population and any Works it excludes. Do not add institution or country groups together: a Work may appear in several groups.",
             record="Record the denominator and exclusions beside each result. Mark a concern if two results use populations that cannot be compared directly."),
        item("analysis.subjects", "Check whether missing classifications could change the story", "Field and Topic summaries only include Works for which OpenAlex records a primary Topic.", "subjects-types", ("measure:coverage.primary_subject", "group:subjects"), "primary_subject",
             action="Check how many Works have no primary Topic, then compare the leading Fields and Topics with what you know about this research portfolio. Look for areas you expected to see but do not.",
             record="Note the number excluded from subject results and whether the visible subject mix looks plausible. If it does not, record which area needs a sample or local comparison."),
        item("analysis.citations", "Inspect citation indicator scope", "Citation links and normalised flags are OpenAlex assertions, not rankings or research quality.", "citations", ("measure:citations",)),
        item("analysis.comparison", "Establish comparability before comparing", "Use identical entity definitions, periods, report versions and populations.", "institution-record", ("report:identity", "report:corpus", "report:implementation_version")), LIMITS)},
    "researcher_identity": {"label": "Check a researcher’s identity", "description": "Review whether one OpenAlex Author profile represents the intended person.", "report_types": {"researcher"}, "question": {"id": "identity_reason", "label": "What prompted the identity check?", "options": (("confirm", "Confirm a profile before reuse"), ("mixed", "The profile may combine people"), ("duplicate", "Another profile may represent the same person"), ("works", "Particular Works look unexpected"))}, "items": (
        item("identity.selection", "Confirm the selected Author profile", "Check the Author ID, displayed name and ORCID assertion against a source you trust.", "researcher-identity-panel", ("report:identity",), "identity", 1),
        item("identity.names", "Review printed-name and ORCID evidence", "Look for incompatible names and multiple work-level ORCID assertions.", "researcher-identity-panel", ("identity:name-variants", "identity:orcids"), "identity", 1),
        item("identity.affiliations", "Review affiliation history", "Check whether institutions and years form a recognisable history. Missing affiliations remain unknown.", "researcher-affiliations-panel", ("identity:affiliations",), "identity"),
        item("identity.coauthors", "Inspect recurring co-authors", "Recognisable collaborators and discontinuities can inform review, but linked profiles may be imperfect.", "researcher-identity-panel", ("identity:coauthors",), "identity"),
        item("identity.resolution", "Review merge and split signals separately", "Candidates and deterministic signals are prompts for inspection, not automatic identity decisions.", "researcher-resolution-panel", ("identity:merge-candidates", "identity:split-signals", "records:works"), "identity", 1), LIMITS)},
    "funding_evidence": {"label": "Investigate funding evidence", "description": "Separate direct Award assertions from indirect Work-level acknowledgements.", "report_types": {"institution", "researcher", "funder"}, "question": {"id": "funding_question", "label": "What are you trying to establish?", "options": (("awards", "Which Awards are recorded"), ("outputs", "Which outputs acknowledge funding"), ("recipient", "Whether an entity received or led funding"))}, "items": (SCOPE,
        item("funding.direct", "Inspect direct Award records", "Check which fields explicitly name a recipient, investigator, amount or date; absent fields remain unknown.", "funding", ("funding:awards",), priority=1),
        item("funding.indirect", "Inspect Work-level acknowledgements separately", "A funding link on a co-authored Work does not establish who received or administered the Award.", "funding", ("funding:work-links", "records:works"), priority=1),
        item("funding.provenance", "Record provenance and incompleteness", "Funding evidence cannot establish a complete administrative portfolio.", "funding", ("funding:provenance", "report:limitations")), LIMITS)},
    "open_access_evidence": {"label": "Inspect open-access evidence", "description": "Inspect OpenAlex access and location assertions without treating them as a policy-compliance decision.", "report_types": {"institution"}, "question": {"id": "access_question", "label": "What do you need to understand?", "options": (("availability", "Recorded free-to-read availability"), ("versions", "Repository and publication versions"), ("policy", "Evidence for a separate policy review"))}, "items": (SCOPE,
        item("access.assertions", "Inspect access-status assertions", "Check recorded access statuses and unknowns. These are changing OpenAlex assertions, not a compliance result or statement of reuse rights.", "outputs-access", ("measure:open_access",), priority=1),
        item("access.locations", "Inspect Sources and versions", "Primary locations and other recorded versions answer different questions about where a Work can be accessed.", "venues", ("group:sources", "records:versions")),
        item("access.policy", "Apply the relevant policy separately", "Record the policy, dates, version requirements, licences and exceptions outside Pharos before making a compliance judgement.", "outputs-access", ("report:limitations",)), LIMITS)},
    "source_publisher_scope": {"label": "Examine journal or publisher coverage", "description": "Inspect primary-location and publisher-lineage scope before using source aggregates.", "report_types": {"source", "publisher"}, "question": {"id": "source_question", "label": "What matters most?", "options": (("inventory", "Title or source inventory"), ("output", "Output patterns"), ("access", "Open-access assertions"), ("publisher", "Publisher relationships"))}, "items": (SCOPE,
        item("source.primary", "Confirm primary-location scope", "Source reports use the Work's primary location; alternative versions are outside this source population.", "overview", ("report:corpus", "group:sources"), priority=1),
        item("source.longtail", "Account for leading groups and the long tail", "Ranked Sources or publishers are leading returned groups, not an exhaustive inventory.", "venues", ("group:sources", "group:publishers")),
        item("source.access", "Inspect open-access assertions", "OpenAlex access status is a changing assertion and does not establish reuse rights.", "outputs-access", ("measure:open_access",)), LIMITS)},
    "general_assessment": {"label": "Another intended use", "description": "Start with a general evidence inspection when no specialist guide matches.", "report_types": {"institution", "researcher", "source", "funder", "publisher"}, "question": {"id": "evidence_focus", "label": "Which evidence matters most?", "options": (("identifiers", "Identifiers and record matching"), ("subjects", "Subjects and classifications"), ("people", "People and affiliations"), ("funding", "Funding"), ("unknown", "I am not sure yet"))}, "items": (SCOPE,
        item("general.coverage", "Review relevant missing metadata", "Decide which missing fields could affect the intended task.", "metadata-patterns", ("measure:coverage",), priority=1),
        item("general.records", "Inspect supporting records", "Open records behind important aggregates before relying on them.", "output", ("records:works",)), LIMITS)},
    "adoption_due_diligence": {"label": "Evaluate OpenAlex before adopting it for ongoing use", "description": "Document evidence and unresolved operational risks before relying on OpenAlex in a continuing workflow.", "report_types": {"institution"}, "question": {"id": "adoption_role", "label": "What role would OpenAlex have?", "options": (("reference", "Reference or discovery source"), ("supplement", "Supplement to a local system"), ("primary", "Primary operational data source"))}, "items": (SCOPE,
        item("adoption.coverage", "Define required fields and acceptable gaps", "Record which identifiers and metadata the workflow requires; inspect their counts and denominators without treating them as a readiness score.", "metadata-patterns", ("measure:coverage",), priority=1),
        item("adoption.change", "Plan for changing upstream data", "Saved reports are dated snapshots while live OpenAlex results can change. Define refresh, comparison and exception-handling procedures.", "output", ("report:retrieved_at", "boundary:saved-live"), priority=1),
        item("adoption.reproduction", "Test reproducibility and provenance", "Confirm that report version, entity, scope, queries and exports provide enough context to reproduce the intended workflow.", "institution-record", ("report:implementation_version", "report:corpus", "report:provenance")),
        item("adoption.operations", "Assess operational dependencies", "Document authentication, rate budgets, availability, retention and the independent local route needed by the proposed workflow.", "institution-record", ("report:limitations",)),
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
        observation=_coverage(report,entry["evidence"]) if entry["evidence"] in (report.get("coverage") or {}) else _identity_observation(report) if entry["evidence"]=="identity" and report_type=="researcher" else None
        rows.append({k:v for k,v in entry.items() if k not in ("evidence","base_priority")}|{"priority":_priority(entry,observation,answers),"observation":observation})
    rows.sort(key=lambda row:row["priority"])
    return {"schema_version":VERSION,"generator":"deterministic","purpose":{"id":purpose_id,"label":purpose["label"]},"answers":answers,"report":{"type":report_type,"identity_id":identity.get("id"),"identity_name":identity.get("display_name"),"retrieved_at":report.get("retrieved_at"),"implementation_version":report.get("implementation_version"),"period":corpus.get("period") or report.get("period")},"introduction":f"{len(rows)} checks, sequenced for {purpose['label'].lower()}.","items":rows,"allowed_statuses":["not_checked","checked","concern","unresolved","not_applicable"],"limitations":["This guide does not decide whether OpenAlex is fit for your purpose.","The sequence organises inspection; it is not a quality or severity score.","High coverage describes OpenAlex's recorded data, not whether it is sufficient for your use.","Checklist status and notes are user judgements, not OpenAlex assertions or Pharos findings.","Live drill-downs may differ from the dated saved report."]}
