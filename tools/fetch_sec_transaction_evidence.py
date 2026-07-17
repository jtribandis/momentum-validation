#!/usr/bin/env python3
"""Primary-source SEC evidence retrieval per DEV_TERMINAL_EVIDENCE_PILOT_V1.

Controls implemented:
- SEC-compliant User-Agent must be supplied via env SEC_EDGAR_USER_AGENT;
  the tool refuses to run without it and never writes its value to artifacts.
- Conservative pacing (>= 0.6 s between requests) and bounded retries.
- Saves original response bytes exactly as received (no transcription).
- Saves response headers to a sibling *_headers.txt file (UA never echoed).
- Records url, timestamp, status, content-type, byte count, SHA-256.
- Refuses to label an HTTP error page (or SEC block page) as a filing.
- Refuses to overwrite a previously saved source.
- Optional repeat retrieval: fetches the URL a second time and verifies byte
  identity; a mismatch is recorded as a provenance exception.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PACING_SECONDS = 0.6
MAX_RETRIES = 3
BLOCK_MARKERS = (
    b"Undeclared Automated Tool",
    b"Request Rate Threshold Exceeded",
)

_last_request_ts = 0.0


def _ua() -> str:
    ua = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
    if not ua:
        sys.exit("REFUSING TO RUN: SEC_EDGAR_USER_AGENT is not set in the environment.")
    return ua


def _pace() -> None:
    global _last_request_ts
    wait = PACING_SECONDS - (time.monotonic() - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.monotonic()


def _get(url: str) -> tuple[int, dict, bytes]:
    ua = _ua()
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        _pace()
        req = urllib.request.Request(url, headers={
            "User-Agent": ua,
            "Accept-Encoding": "identity",
            "Host": urllib.request.urlparse(url).netloc,
        })
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.code in (429, 503) and attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
                last_err = e
                continue
            return e.code, dict(e.headers or {}), body
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
    raise RuntimeError(f"retrieval failed after {MAX_RETRIES} attempts: {url} ({last_err})")


def _is_error_page(status: int, body: bytes) -> str | None:
    if status != 200:
        return f"HTTP {status}"
    for marker in BLOCK_MARKERS:
        if marker in body[:8192]:
            return f"SEC block page marker: {marker.decode()}"
    return None


def _sanitize_headers(headers: dict) -> str:
    drop = {"set-cookie", "authorization", "cookie"}
    lines = [f"{k}: {v}" for k, v in headers.items() if k.lower() not in drop]
    return "\n".join(lines) + "\n"


def fetch_source(url: str, dest: Path, verify_repeat: bool = True) -> dict:
    """Fetch url to dest; return a source record dict (UA value never included)."""
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError(f"refusing to overwrite existing source: {dest}")
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    status, headers, body = _get(url)
    err = _is_error_page(status, body)
    if err:
        raise RuntimeError(f"refusing to save error page as filing ({err}): {url}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    headers_path = dest.with_name(dest.stem + "_headers.txt")
    headers_path.write_text(
        f"source_url: {url}\nretrieval_date_utc: {retrieved}\nhttp_status: {status}\n---\n"
        + _sanitize_headers(headers)
    )
    sha = hashlib.sha256(body).hexdigest()

    repeat_ok = "N"
    repeat_exception = None
    if verify_repeat:
        status2, _, body2 = _get(url)
        if status2 == 200 and hashlib.sha256(body2).hexdigest() == sha:
            repeat_ok = "Y"
        else:
            repeat_exception = (
                f"PROVENANCE_EXCEPTION: repeat retrieval mismatch for {url} "
                f"(status2={status2}, sha2={hashlib.sha256(body2).hexdigest()})"
            )

    record = {
        "source_url": url,
        "retrieval_date_utc": retrieved,
        "http_status": status,
        "content_type": headers.get("Content-Type", "NOT_FOUND"),
        "local_filename": dest.name,
        "byte_count": len(body),
        "byte_sha256": sha,
        "repeat_retrieval_verified_YN": repeat_ok,
    }
    if repeat_exception:
        record["provenance_exception"] = repeat_exception
    return record


def fetch_json(url: str) -> dict:
    """Fetch SEC JSON metadata (submissions/index) without saving as evidence."""
    status, _, body = _get(url)
    err = _is_error_page(status, body)
    if err:
        raise RuntimeError(f"metadata fetch failed ({err}): {url}")
    return json.loads(body)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: fetch_sec_transaction_evidence.py <url> <dest_path> [--no-repeat]")
    rec = fetch_source(sys.argv[1], Path(sys.argv[2]),
                       verify_repeat="--no-repeat" not in sys.argv)
    print(json.dumps(rec, indent=2))
