#!/usr/bin/env python3
"""Read-only, closed-loop HTTP load against a marked loopback synthetic instance."""

import argparse
import concurrent.futures
import json
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests


def run(args):
    parsed = urlparse(args.base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only unauthenticated loopback HTTP targets are supported")
    if not 1 <= args.workers <= 64 or not 1 <= args.requests <= 100000:
        raise ValueError("Workers 1..64 and requests 1..100000 required")
    fixtures = json.loads(Path(args.fixtures).read_text())
    if fixtures.get("synthetic_only") is not True:
        raise ValueError("Requires explicitly synthetic fixture metadata")
    paths = [
        ("catalog", "/api/v1/products/?limit=20"),
        ("search", "/api/v1/products/?search=نایاب&ordering=relevance&limit=20"),
        ("detail", f"/api/v1/products/{fixtures['anchor_slug']}/"),
        ("recommendations", f"/api/v1/products/{fixtures['anchor_slug']}/recommendations/?limit=8"),
    ]
    probe = requests.get(args.base_url.rstrip("/") + "/health/live/", timeout=5)
    if probe.status_code != 200 or probe.headers.get("X-Load-Test") != "synthetic-only":
        raise ValueError("Target does not advertise isolated synthetic benchmark mode")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = output.with_suffix(".meta.json")
    if output.exists() or metadata_path.exists():
        raise ValueError("Raw output/metadata already exists; choose a new run path")
    with requests.Session() as session:
        for n in range(40):
            scenario, path = paths[n % len(paths)]
            response = session.get(args.base_url.rstrip("/") + path, timeout=15)
            if response.status_code != 200:
                raise RuntimeError("Warmup returned unexpected status")
    lock = threading.Lock()
    start = time.perf_counter()
    started_at = datetime.now(UTC).isoformat()
    failures = 0
    with output.open("x") as raw:

        def worker(number):
            records = []
            with requests.Session() as session:
                for index in range(number, args.requests, args.workers):
                    scenario, path = paths[index % len(paths)]
                    correlation = str(uuid.uuid4())
                    begun = time.perf_counter()
                    row = {"scenario": scenario, "request_id": correlation, "status": None, "error": None}
                    try:
                        response = session.get(
                            args.base_url.rstrip("/") + path,
                            headers={"X-Request-ID": correlation},
                            timeout=15,
                        )
                        row["status"] = response.status_code
                        data = response.json()
                        valid = (
                            (isinstance(data, list) and len(data) <= 8)
                            if scenario == "recommendations"
                            else (
                                isinstance(data, dict)
                                and (
                                    "id" in data
                                    if scenario == "detail"
                                    else isinstance(data.get("results"), list)
                                )
                            )
                        )
                        if (
                            response.status_code != 200
                            or not valid
                            or response.headers.get("X-Request-ID") != correlation
                        ):
                            row["error"] = "response_contract"
                    except (requests.RequestException, ValueError) as exc:
                        row["error"] = type(exc).__name__
                    row["duration_ms"] = (time.perf_counter() - begun) * 1000
                    records.append(row)
                    with lock:
                        raw.write(json.dumps(row) + "\n")
            return sum(row["error"] is not None for row in records)

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            failures = sum(executor.map(worker, range(args.workers)))
    metadata = {
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - start,
        "requests": args.requests,
        "workers": args.workers,
        "warmup_requests_excluded": 40,
        "failures": failures,
        "synthetic_fixture": fixtures,
        "source": str(output),
        "target": args.base_url,
        "workload": "equal-weight closed-loop catalog/search/detail/recommendations GETs",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(f"Completed {args.requests} read requests with {failures} failed contracts; raw evidence saved")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18001")
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--requests", type=int, default=1200)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", required=True)
    raise SystemExit(run(parser.parse_args()))
