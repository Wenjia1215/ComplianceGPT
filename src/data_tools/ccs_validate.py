#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ccs_validate.py
A harsh & strict JSON / JSONL validator.

Features:
- UTF-8 only (no BOM). Fails on decode errors.
- Forbids NaN/Infinity/-Infinity (true RFC 8259 compliance).
- Detects duplicate keys (at any nesting level).
- JSONL: each non-empty line must be exactly one valid JSON value (default: object).
- Optional: require top-level object for both JSON and JSONL (--require-object).
- Optional: require final newline at end of file (--newline-eof).
- Flags errors with precise locations where possible.
- Outputs a CSV summary: path,type,rows,errors,warnings and verbose details to stderr.
- Returns exit code 1 if any file has errors (strict).

Usage:
  python strict_json_check.py <path or file> [<more paths>]
Options:
  --json                 Treat all inputs as JSON (ignore extension).
  --jsonl                Treat all inputs as JSONL (ignore extension).
  --require-object       Require top-level to be a JSON object (for both JSON and JSONL lines).
  --allow-blank-lines    Allow blank lines in JSONL (ignored, not counted as rows).
  --newline-eof          Require files to end with a trailing newline.
  --fail-on-warning      Exit non-zero if any warnings are produced.
  --summary-csv <path>   Also write the CSV summary to a file (stdout still prints it).
  --quiet                Do not print per-error details to stderr (still prints CSV to stdout).
Notes:
- File type detection defaults by extension: *.json -> JSON, *.jsonl -> JSONL.
- Directory inputs are scanned recursively for *.json and *.jsonl.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

# ------------------------- Duplicate-key detection -------------------------

class DuplicateKeyError(ValueError):
    pass

def _no_duplicate_object_pairs(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    obj: Dict[str, Any] = {}
    for k, v in pairs:
        if k in obj:
            raise DuplicateKeyError(f"Duplicate key: {k!r}")
        obj[k] = v
    return obj

def _reject_constants(val: str) -> Any:
    # Called when encountering NaN/Infinity/-Infinity
    raise ValueError(f"Non-JSON numeric constant encountered: {val}")

STRICT_JSON_KW = dict(
    object_pairs_hook=_no_duplicate_object_pairs,
    parse_float=float,           # normal
    parse_int=int,
    parse_constant=_reject_constants,  # disallow NaN, Infinity, -Infinity
)

# ------------------------- Helpers -------------------------

@dataclass
class FileReport:
    path: str
    ftype: str                     # 'json' or 'jsonl'
    rows: int = 0                  # for jsonl = number of JSON lines; for json = 1 if valid
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def has_error(self) -> bool:
        return len(self.errors) > 0

    def has_warning(self) -> bool:
        return len(self.warnings) > 0

def discover_files(paths: Iterable[str], forced_type: str | None) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for name in files:
                    full = os.path.join(root, name)
                    if forced_type == 'json' or forced_type == 'jsonl':
                        out.append((full, forced_type))
                    else:
                        if name.lower().endswith('.json'):
                            out.append((full, 'json'))
                        elif name.lower().endswith('.jsonl'):
                            out.append((full, 'jsonl'))
        else:
            if forced_type in ('json', 'jsonl'):
                out.append((p, forced_type))
            else:
                lower = p.lower()
                if lower.endswith('.json'):
                    out.append((p, 'json'))
                elif lower.endswith('.jsonl'):
                    out.append((p, 'jsonl'))
                else:
                    # Unknown without forced type: skip silently
                    pass
    return out

def read_bytes(path: str) -> Tuple[bytes, List[str]]:
    warnings: List[str] = []
    with open(path, 'rb') as f:
        data = f.read()
    # BOM check
    if data.startswith(b'\xef\xbb\xbf'):
        warnings.append("UTF-8 BOM detected (discouraged).")
    return data, warnings

def decode_utf8_strict(data: bytes) -> str:
    return data.decode('utf-8', errors='strict')

def check_newline_eof(text: str) -> bool:
    return text.endswith('\n')

def json_top_is_object(val: Any) -> bool:
    return isinstance(val, dict)

# ------------------------- Validators -------------------------

def validate_json(path: str, text: str, require_object: bool) -> FileReport:
    rep = FileReport(path=path, ftype='json')
    # Hard-trim nothing; JSON may have surrounding whitespace, but we want to warn if multiple trailing newlines
    if text.strip() == "":
        rep.add_error("Empty file or only whitespace.")
        return rep

    try:
        # Capture line/col on error via an extra pass with json.loads
        value = json.loads(text, strict=True, **STRICT_JSON_KW)
        rep.rows = 1
        if require_object and not json_top_is_object(value):
            rep.add_error("Top-level value is not an object (use --require-object to enforce objects).")
    except DuplicateKeyError as e:
        rep.add_error(f"Duplicate key error: {e}")
    except json.JSONDecodeError as e:
        rep.add_error(f"JSON syntax error at line {e.lineno}, col {e.colno}: {e.msg}")
    except ValueError as e:
        rep.add_error(f"JSON semantic error: {e}")
    return rep

def validate_jsonl(path: str, text: str, require_object: bool, allow_blank_lines: bool) -> FileReport:
    rep = FileReport(path=path, ftype='jsonl')
    lines = text.splitlines()
    if text and not lines:
        # Shouldn't happen, but guard anyway
        rep.add_error("Internal error splitting lines.")
        return rep

    if len(lines) == 0:
        rep.add_error("Empty file.")
        return rep

    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if line == "":
            if allow_blank_lines:
                continue
            else:
                rep.add_error(f"Blank line not allowed (line {idx}).")
                continue
        try:
            value = json.loads(line, strict=True, **STRICT_JSON_KW)
            rep.rows += 1
            if require_object and not json_top_is_object(value):
                rep.add_error(f"Top-level value is not an object (line {idx}).")
        except DuplicateKeyError as e:
            rep.add_error(f"Duplicate key (line {idx}): {e}")
        except json.JSONDecodeError as e:
            rep.add_error(f"JSONL syntax error at line {idx}, col {e.colno}: {e.msg}")
        except ValueError as e:
            rep.add_error(f"JSONL semantic error at line {idx}: {e}")
    return rep

# ------------------------- Main -------------------------

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Harsh & strict JSON/JSONL validator.")
    gtype = ap.add_mutually_exclusive_group()
    gtype.add_argument("--json", action="store_true", help="Treat all inputs as JSON.")
    gtype.add_argument("--jsonl", action="store_true", help="Treat all inputs as JSONL.")
    ap.add_argument("--require-object", action="store_true", help="Require top-level JSON objects.")
    ap.add_argument("--allow-blank-lines", action="store_true", help="Allow blank lines in JSONL.")
    ap.add_argument("--newline-eof", action="store_true", help="Require newline at end of file.")
    ap.add_argument("--fail-on-warning", action="store_true", help="Exit non-zero if warnings exist.")
    ap.add_argument("--summary-csv", type=str, default=None, help="Write CSV summary to file (stdout still prints CSV).")
    ap.add_argument("--quiet", action="store_true", help="Suppress detailed error messages on stderr.")
    ap.add_argument("paths", nargs="+", help="Files and/or directories (recursively scanned).")

    args = ap.parse_args(argv)

    forced_type = 'json' if args.json else ('jsonl' if args.jsonl else None)
    filelist = discover_files(args.paths, forced_type)

    if not filelist:
        print("path,type,rows,errors,warnings")
        return 0

    outputs: List[FileReport] = []

    for fpath, ftype in sorted(filelist):
        rep = FileReport(path=fpath, ftype=ftype)
        try:
            data, warn_list = read_bytes(fpath)
            for w in warn_list:
                rep.add_warning(w)
            try:
                text = decode_utf8_strict(data)
            except UnicodeDecodeError as e:
                rep.add_error(f"UTF-8 decoding error: {e}")
                outputs.append(rep)
                continue

            if args.newline_eof and not check_newline_eof(text):
                rep.add_error("Missing newline at end of file.")

            # Validate per type
            if ftype == 'json':
                rep = validate_json(fpath, text, args.require_object)
                rep.warnings.extend(warn_list)  # preserve previous warnings
            else:
                rep = validate_jsonl(fpath, text, args.require_object, args.allow_blank_lines)
                rep.warnings.extend(warn_list)

        except OSError as e:
            rep.add_error(f"I/O error: {e}")

        outputs.append(rep)

    # Print detailed errors/warnings to stderr (unless quiet)
    if not args.quiet:
        for rep in outputs:
            if rep.has_error() or rep.has_warning():
                print(f"[{rep.ftype.upper()}] {rep.path}", file=sys.stderr)
                for err in rep.errors:
                    print(f"  ERROR: {err}", file=sys.stderr)
                for wrn in rep.warnings:
                    print(f"  WARN : {wrn}", file=sys.stderr)

    # CSV summary to stdout
    out_csv = io.StringIO()
    writer = csv.writer(out_csv)
    writer.writerow(["path", "type", "rows", "errors", "warnings"])
    for rep in outputs:
        writer.writerow([
            rep.path,
            rep.ftype,
            rep.rows,
            len(rep.errors),
            len(rep.warnings),
        ])
    csv_text = out_csv.getvalue()
    sys.stdout.write(csv_text)

    if args.summary_csv:
        try:
            with open(args.summary_csv, "w", newline="") as f:
                f.write(csv_text)
        except OSError as e:
            print(f"[WARN] Failed to write summary CSV: {e}", file=sys.stderr)

    # Exit code logic
    any_error = any(r.has_error() for r in outputs)
    any_warn = any(r.has_warning() for r in outputs)
    if any_error:
        return 1
    if args.fail_on_warning and any_warn:
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
