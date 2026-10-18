#!/usr/bin/env python3
"""Check dataset URLs in datasets.csv and optionally stamp date_last_checked.

    python3 tools/check_datasets.py            # report only
    python3 tools/check_datasets.py --update   # write today's date when the URL responds

A response is any completed HTTP status, including 401, 403, and 404. Those
pages exist; they may be gated or moved. Connection errors and timeouts are
left unchanged so a network blip does not look like a fresh review.

This only updates the checked date. It does not change VERIFIED / UNVERIFIED.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "datasets.csv"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def probe(url: str, timeout: float) -> tuple[int | None, str]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    for method in ("HEAD", "GET"):
        req = Request(url, headers=headers, method=method)
        try:
            with urlopen(req, timeout=timeout) as resp:
                if method == "GET":
                    resp.read(1024)
                return resp.status, resp.geturl()
        except HTTPError as exc:
            # Some hosts reject HEAD, or answer 404 to HEAD and 200 to GET.
            if method == "HEAD" and exc.code in (400, 403, 404, 405, 501):
                continue
            return exc.code, url
        except URLError as exc:
            return None, str(exc.reason)
        except TimeoutError:
            return None, "timeout"
        except OSError as exc:
            return None, str(exc)
    return None, "no response"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="write date_last_checked for URLs that responded")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    args = parser.parse_args()

    with args.csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields or "url" not in fields or "date_last_checked" not in fields:
        print("datasets.csv needs url and date_last_checked columns", file=sys.stderr)
        return 2

    today = datetime.now(timezone.utc).date().isoformat()
    failed = 0
    for row in rows:
        status, detail = probe(row["url"].strip(), args.timeout)
        ok = status is not None
        mark = "OK" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"{mark}\t{status or '-'}\t{row['name']}\t{detail}")
        if args.update and ok:
            row["date_last_checked"] = today

    if args.update:
        tmp = args.csv.with_suffix(".csv.tmp")
        with tmp.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(args.csv)
        print(f"Updated {args.csv} date_last_checked={today} for rows that responded")
    else:
        print("Report only. Re-run with --update to stamp date_last_checked.")
    print(f"{len(rows) - failed} responded, {failed} failed, checked {today}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
