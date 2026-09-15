import csv
import html
import io
import json
import os
import tempfile
from pathlib import Path


def write(path, content):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=".pharos-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def save_json(path, value):
    # JSON is a YAML 1.2 subset, so .yaml exports are portable without a runtime dependency.
    write(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def csv_text(headers, rows):
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([("'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v) for v in row])
    return buf.getvalue()


def render(profile):
    esc = lambda value: html.escape(str(value))
    def table(title, rows, coverage):
        body = "".join(f"<tr><td>{esc(r.get('label', r.get('year', '')))}</td><td>{r['count']:,}</td><td>{r['denominator']:,}</td><td>{r['percentage'] if r['percentage'] is not None else 'Unknown'}</td></tr>" for r in rows)
        return f"<section><h2>{esc(title)}</h2><p>{esc(coverage)}</p><table><thead><tr><th>Recorded item</th><th>Works</th><th>Denominator</th><th>%</th></tr></thead><tbody>{body}</tbody></table></section>"
    c = profile["coverage"]
    cov = lambda key: f"Metadata coverage: {c[key]['count']:,} / {c[key]['denominator']:,} ({c[key]['population']}). Missing metadata is unknown."
    identity = profile["identity"]
    text = ["<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'\">",
        "<title>Pharos coverage report</title><style>body{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#193434;background:#faf9f4}h1{font-size:36px}h2{margin-top:32px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px;border-bottom:1px solid #ccd8d2}pre{white-space:pre-wrap;overflow-wrap:anywhere}section{margin:30px 0}small{color:#526363}</style><body>",
        f"<header><small>PHAROS · See how OpenAlex sees your research</small><h1>{esc(identity.get('display_name', 'Institution'))}</h1>",
        f"<p>{esc(identity.get('id', ''))} · {esc(identity.get('ror', ''))} · {esc(identity.get('country_code', 'Unknown country'))}</p></header>",
        "<p>Descriptive source assertions; no performance or quality assessment.</p>"]
    for item in profile["narrative"]:
        text.append(f"<p>{esc(item['text'])} <small>Source: {esc(item['field'])}</small></p>")
    text.append(f"<p>Retrieval: {esc(profile['backend']['retrieved_at'])}; backend: OpenAlex API. Retractions retained and flagged: {profile['retracted_works']['count']:,}. {esc(cov('retraction_information'))}</p>")
    text.append(table("Observed output over time", profile["annual_counts"], "All eligible works. Current-year output is incomplete when included. Complete-year extrema include zero-output years."))
    text.append(f"<p>Observed years and complete-year extrema: {esc(json.dumps(profile['observed_years']))}</p>")
    for title, key, coverage in [("OpenAlex work types", "work_type_distribution", cov("work_type")),
        ("Primary OpenAlex Fields", "subject_distribution", cov("primary_subject") + " Percentages use classified works only; rounded to six decimals."),
        ("OpenAlex open access status", "open_access_distribution", cov("oa_information") + " " + cov("oa_status")),
        ("Primary publication sources", "publication_sources", cov("primary_source") + " Alternative locations are not counted as primary sources."),
        ("Institution co-occurrence", "collaborators", cov("affiliation_observable") + " " + cov("resolved_authorships") + " Whole counts; each institution counted once per work; target institution excluded."),
        ("Country co-occurrence", "collaboration_countries", cov("affiliation_observable") + " Whole counts; includes home country. Shares need not sum to 100%.")]:
        text.append(table(title, profile[key], coverage))
    text.append(table("Open access and repository copies", [{"label":"Open access", **profile["open_access"]}, {"label":"Repository copies", **profile["repository_copies"]}], cov("oa_information") + " " + cov("repository_information")))
    text.append(table("Metadata coverage", [{"label":k.replace('_',' '), **v} for k,v in c.items()], "Resolved and unresolved authorship rows use observed authorships as denominator; other rows use eligible works."))
    text.append("<h2>Limitations</h2><ul>" + "".join(f"<li>{esc(w)}</li>" for w in profile["warnings"]) + "</ul>")
    for title, value in [("Resolved identity", identity), ("Exact corpus specification", profile["corpus"]), ("Source and retrieval", profile["backend"])]:
        text.append(f"<details><summary>{title}</summary><pre>{esc(json.dumps(value, indent=2, ensure_ascii=False))}</pre></details>")
    text.append("</body></html>")
    return "\n".join(text)


def export(directory, profile, observations, receipt):
    directory = Path(directory)
    save_json(directory / "profile.json", profile)
    write(directory / "profile.html", render(profile))
    save_json(directory / "corpus.yaml", profile["corpus"])
    save_json(directory / "retrieval-receipt.yaml", receipt)
    write(directory / "work-ids.csv", csv_text(["openalex_id", "doi", "pmid"], [(r.id, r.doi, r.pmid) for r in observations]))
    write(directory / "warnings.csv", csv_text(["type", "message"], [("coverage_or_method", w) for w in profile["warnings"]]))
