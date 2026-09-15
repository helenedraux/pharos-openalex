import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
from pharos.backends.openalex_api import APIError, OpenAlex
from pharos.corpus import selector, specification, digest
from pharos.exports import export, save_json
from pharos.profile import calculate
from pharos.resources import RATE_CARD, estimate, validate_rates
from pharos.storage import Store, now


def parser():
    p = argparse.ArgumentParser(description="See how OpenAlex sees your research. Local institution profile prototype.")
    p.add_argument("institution", help="Exact ROR or OpenAlex institution ID; names are never silently matched")
    p.add_argument("--start-year", type=int, required=True)
    p.add_argument("--end-year", type=int, required=True)
    p.add_argument("--out", type=Path, required=True, help="New output directory, or the existing checkpoint with --resume")
    p.add_argument("--resume", action="store_true", help="Resume or rebuild from the existing frozen checkpoint")
    p.add_argument("--estimate-only", action="store_true", help="Resolve and estimate without downloading the corpus")
    p.add_argument("--anonymous", action="store_true", help="Explicitly use keyless preview access")
    p.add_argument("--max-records", type=int, default=100000, help="Local corpus bound (default: 100000)")
    p.add_argument("--max-cost-usd", type=float, default=0.1, help="Maximum estimated API cost across this run and resumes (default: 0.10)")
    p.add_argument("--rate-card", type=Path, help="Dated JSON rate card; see docs/rate-card.json")
    return p


def run(args, api_factory=OpenAlex):
    import math
    selected = selector(args.institution)
    # Validate years before touching the filesystem or network.
    specification(selected, "https://openalex.org/I1", args.start_year, args.end_year)
    if args.max_records < 1 or not math.isfinite(args.max_cost_usd) or args.max_cost_usd < 0:
        raise ValueError("Resource bounds must be finite and nonnegative; max-records must be positive.")
    if args.out.is_symlink(): raise ValueError("Output directory must not be a symlink.")
    if args.resume:
        if not (args.out / "checkpoint.sqlite3").is_file(): raise ValueError("No checkpoint exists at this target.")
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        if any(args.out.iterdir()): raise ValueError("Output directory is not empty. Use --resume for a matching checkpoint or choose a new target.")
    lock = (args.out / ".lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise ValueError("This output directory is already in use by another Pharos process.") from None
    store = Store(args.out / "checkpoint.sqlite3")
    try:
        previous = store.get("spec")
        if previous:
            requested = specification(selected, previous["resolved_openalex_id"], args.start_year, args.end_year)
            if requested != previous: raise ValueError("Resume parameters differ from the saved corpus. Use the original arguments or a new output directory.")
        key = None if args.anonymous else os.environ.get("OPENALEX_API_KEY")
        if not key and not args.anonymous and not store.get("complete"):
            raise ValueError("Set OPENALEX_API_KEY locally, or explicitly select --anonymous for a small preview. Do not put keys in command arguments.")
        rates = validate_rates(json.loads(args.rate_card.read_text()) if args.rate_card else store.get("rates", RATE_CARD))
        store.set("rates", rates)
        if not store.get("started_at"): store.set("started_at", now())
        def audit(event):
            if event["event"] == "attempt" and event["endpoint"] == "works":
                calls = sum(json.loads(r[0]).get("endpoint") == "works" for r in store.db.execute("SELECT event FROM events"))
                if (calls + 1) * rates["list_call_usd"] > args.max_cost_usd + 1e-12:
                    raise APIError("Configured request-cost limit reached. Checkpoint saved; resume with an explicit revised limit.")
            store.audit(event)
        api = api_factory(key=key, audit=audit)
        if not previous:
            identity = api.resolve(selected)
            spec = specification(selected, identity["id"], args.start_year, args.end_year)
            with store.db:
                store._set("spec", spec)
                store._set("identity", identity)
                store._set("hash", digest(spec))
                store._set("cursor", "*")
                store._set("query", api.query(spec))
        else:
            spec, identity = previous, store.get("identity")
        save_json(args.out / "corpus.yaml", spec)
        print(f"Institution: {identity.get('display_name')} ({identity['id']})", flush=True)
        print(f"Period: {spec['period']['from']} to {spec['period']['to']}; direct assignment; all types; core corpus; retractions retained; whole counts.", flush=True)
        estimate_value = store.get("estimate")
        if estimate_value is None:
            estimate_value = estimate(api.count(spec), rates, bool(key))
            store.set("estimate", estimate_value)
        save_json(args.out / "resource-estimate.json", estimate_value)
        print(f"Estimate: {estimate_value['estimated_records']:,} works, {estimate_value['estimated_calls']} calls, ${estimate_value['estimated_api_cost_usd']:.6f}; rates as of {estimate_value['rate_card']['as_of']}. Not a remaining-balance guarantee.", flush=True)
        if args.estimate_only:
            save_json(args.out / "retrieval-receipt.yaml", store.receipt("estimated"))
            return 0
        if estimate_value["estimated_records"] > args.max_records or store.count() > args.max_records:
            raise APIError("Estimated or cached corpus exceeds --max-records. Review the estimate and explicitly raise the limit if appropriate.")
        if not store.get("complete") and estimate_value["estimated_api_cost_usd"] > args.max_cost_usd:
            raise APIError("Estimated retrieval exceeds --max-cost-usd. Review the estimate and explicitly revise the limit if appropriate.")
        while not store.get("complete"):
            cursor = store.get("cursor", "*")
            result = api.page(spec, cursor)
            new_ids = {r.get("id") for r in result["results"]}
            existing = {r[0] for r in store.db.execute("SELECT id FROM works WHERE id IN (" + ",".join("?" for _ in new_ids) + ")", tuple(new_ids))} if new_ids else set()
            if store.count() + len(new_ids - existing) > args.max_records:
                raise APIError("Actual corpus exceeds --max-records. Last committed page is preserved; resume with a revised bound.")
            store.page(result, cursor)
            save_json(args.out / "retrieval-receipt.yaml", store.receipt("retrieving"))
            print(f"Retrieved {store.count():,} unique works.", flush=True)
        observations = store.observations()
        receipt = store.receipt("complete")
        backend = {"type": "openalex_api", "retrieved_at": store.get("last_page_at"), "source_snapshot_date": None,
                   "receipt": receipt, "raw_records": "checkpoint.sqlite3", "query": api.query(spec)}
        # Frozen raw records are hashed independently of SQLite's physical layout.
        backend["source_assertions_hash"] = digest([json.loads(r[0]) for r in store.db.execute("SELECT raw FROM works ORDER BY id")])
        profile = calculate(observations, spec, identity, backend)
        profile["warnings"].extend(receipt["warnings"])
        export(args.out, profile, observations, receipt)
        print(f"Profile and provenance saved to {args.out.resolve()}", flush=True)
        return 0
    except (APIError, ValueError, OSError, KeyboardInterrupt) as exc:
        # Only controlled errors are persisted; filesystem exception text can contain private paths.
        message = str(exc) if isinstance(exc, (APIError, ValueError)) else "Operation interrupted or local filesystem unavailable. Resume from checkpoint."
        save_json(args.out / "retrieval-receipt.yaml", store.receipt("interrupted", message))
        raise
    finally:
        store.close()
        lock.close()


def main():
    try:
        return run(parser().parse_args())
    except (APIError, ValueError) as exc:
        print(f"Pharos: {exc}", file=sys.stderr)
        return 2
    except (OSError, KeyboardInterrupt):
        print("Pharos: local operation interrupted or unavailable; inspect the saved receipt and resume.", file=sys.stderr)
        return 2

if __name__ == "__main__": sys.exit(main())
