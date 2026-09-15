"""Bounded HTTPS transport and the OpenAlex-to-canonical observation adapter."""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pharos.contracts import Observation

SELECT = "id,doi,ids,publication_date,publication_year,type,primary_topic,open_access,authorships,abstract_inverted_index,is_retracted,primary_location,related_works,funders,awards,is_xpac"

class APIError(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise APIError("Unexpected redirect refused; credentials were not forwarded.")

class OpenAlex:
    def __init__(self, key=None, audit=None, key_provider=None):
        self._key = key
        self._key_provider = key_provider
        self.audit = audit or (lambda event: None)
        self.opener = urllib.request.build_opener(NoRedirect)

    @property
    def key(self):
        return self._key_provider() if self._key_provider else self._key

    def get(self, path, params=None):
        url = "https://api.openalex.org/" + path + "?" + urllib.parse.urlencode(params or {})
        headers = {"User-Agent": "Pharos/0.1 (local research portrait)", "Accept": "application/json"}
        key = self.key
        if key:
            headers["Authorization"] = "Bearer " + key
        for attempt in range(3):
            self.audit({"event": "attempt", "endpoint": path.split("/")[0]})
            try:
                with self.opener.open(urllib.request.Request(url, headers=headers), timeout=45) as response:
                    raw = response.read(32 * 1024 * 1024 + 1)
                if len(raw) > 32 * 1024 * 1024:
                    raise APIError("API response exceeded the 32 MiB page limit.")
                # Defense against accidental upstream credential echoes, including in source text.
                if key:
                    raw = raw.replace(key.encode(), b"[REDACTED]")
                value = json.loads(raw)
                cost = (value.get("meta") or {}).get("cost_usd")
                if not isinstance(cost, (float, int)) or isinstance(cost, bool) or cost < 0:
                    cost = None
                self.audit({"event": "response", "bytes": len(raw), "reported_cost_usd": cost})
                return value
            except urllib.error.HTTPError as exc:
                status = exc.code
                exc.close()
                if status == 429:
                    raise APIError("OpenAlex rate limit or daily budget reached. Checkpoint saved; resume later.") from None
                if status in (401, 403):
                    raise APIError("OpenAlex authentication failed. Check OPENALEX_API_KEY locally.") from None
                if status >= 500 and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(f"OpenAlex returned HTTP {status}; request details suppressed.") from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError("OpenAlex network request failed. Checkpoint saved; resume later.") from None
            except (ValueError, TypeError):
                raise APIError("OpenAlex returned malformed JSON.") from None
        raise APIError("OpenAlex request failed.")

    def resolve(self, selected):
        entity = self.get("institutions/" + urllib.parse.quote(selected["id"], safe="/:"))
        identifier = entity.get("id", "")
        if not re.fullmatch(r"https://openalex.org/I[1-9][0-9]*", identifier):
            raise APIError("Institution resolution returned no valid OpenAlex ID.")
        expected = selected["id"]
        if selected["id_namespace"] == "ror" and entity.get("ror") != expected:
            raise APIError("ROR mapping disagrees with the requested identity; no corpus was selected.")
        if selected["id_namespace"] == "openalex" and identifier.split("/")[-1] != expected:
            raise APIError("Institution ID was redirected or merged; inspect the current identity before proceeding.")
        return entity

    @staticmethod
    def query(spec):
        return {"filter": f"authorships.institutions.id:{spec['resolved_openalex_id']},from_publication_date:{spec['period']['from']},to_publication_date:{spec['period']['to']}", "corpus": spec["openalex_corpus"]}

    def count(self, spec):
        result = self.get("works", dict(self.query(spec), per_page=1, select="id"))
        count = result.get("meta", {}).get("count")
        if not isinstance(count, int) or count < 0:
            raise APIError("OpenAlex count is missing or invalid.")
        return count

    def page(self, spec, cursor):
        result = self.get("works", dict(self.query(spec), per_page=100, select=SELECT, cursor=cursor))
        if not isinstance(result.get("results"), list) or "next_cursor" not in result.get("meta", {}):
            raise APIError("OpenAlex page is missing results or its continuation cursor.")
        return result


def observe(raw):
    """Preserve IDs and raw categories; no negative inference for absent OA assertions."""
    if not re.fullmatch(r"https://openalex.org/W[1-9][0-9]*", raw.get("id", "")):
        raise APIError("Invalid work ID in source page.")
    field = (raw.get("primary_topic") or {}).get("field") or {}
    oa = raw.get("open_access") or {}
    authors = raw.get("authorships") or []
    institutions, countries = {}, set()
    resolved = 0
    observable = False
    for author in authors:
        items = author.get("institutions") or []
        valid = [i for i in items if i.get("id")]
        resolved += bool(valid)
        observable |= bool(valid or author.get("raw_affiliation_strings") or author.get("affiliations"))
        countries.update(author.get("countries") or [])
        for inst in valid:
            institutions[inst["id"]] = inst.get("display_name") or inst["id"]
            if inst.get("country_code"):
                countries.add(inst["country_code"])
    source = (raw.get("primary_location") or {}).get("source") or {}
    boolean = lambda x: x if isinstance(x, bool) else None
    return Observation(raw["id"], raw.get("doi"), (raw.get("ids") or {}).get("pmid"),
        raw.get("publication_date") or "", raw.get("publication_year") or 0, raw.get("type"),
        field.get("id"), field.get("display_name"), boolean(oa.get("is_oa")), oa.get("oa_status"),
        boolean(oa.get("any_repository_has_fulltext")), len(authors), resolved, observable,
        tuple(sorted(institutions.items())), tuple(sorted(countries)), bool(raw.get("abstract_inverted_index")),
        bool(raw.get("funders") or raw.get("awards")), boolean(raw.get("is_retracted")),
        source.get("id"), source.get("display_name"), source.get("type"),
        len(authors) >= 100)
