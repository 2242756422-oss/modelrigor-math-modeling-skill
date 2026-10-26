#!/usr/bin/env python3
"""Record real argv execution and endpoint integrity, not a security sandbox.

Common Python script/local-module entries are resolved, not substring-matched.
Other commands are recorded with LIMITED scope, not auto-certified computation.
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from core import resolve, sha256
from provenance import execution_entry, run_provenance_limitations, audit_entry_review


def _snapshot(root, names):
    items = []
    for name in names:
        path = Path(name) if Path(name).is_absolute() else root/name
        items.append({'path': str(path.absolute()), 'resolved_path': str(path.resolve()),
                      'sha256': sha256(path) if path.is_file() else None})
    return items


def record_run(root, command, code, inputs, outputs, receipt, entry_review=None):
    root = Path(root).resolve(); receipt = resolve(root, str(receipt)).resolve()
    code, inputs, outputs = list(code), list(inputs), list(outputs)
    if not isinstance(command, list) or not command or not code or not outputs or any(not isinstance(x, str) for x in command):
        raise ValueError('argv command, code and outputs are required')
    for name in code + inputs:
        if not resolve(root, name).is_file():
            raise ValueError("missing execution input: " + name)
    entry = execution_entry(root, command, code, os.environ)
    if entry['status'] == 'MISMATCH':
        raise ValueError(entry['reason'])
    # Package initializers may execute before __main__; bind without importing.
    for initializer in entry['module_initializers']:
        if Path(initializer) not in {resolve(root, x).resolve() for x in code}:
            code.append(initializer)
    entry = execution_entry(root, command, code, os.environ)
    source_paths = {resolve(root, x).resolve() for x in code+inputs}
    output_paths = {resolve(root, x).resolve() for x in outputs}
    log = receipt.with_suffix('.log')
    if source_paths & output_paths or receipt in source_paths | output_paths or log in source_paths | output_paths or receipt == log:
        raise ValueError('code/input, outputs and receipt/log must be distinct artifacts; use separate preprocessing output')
    before_sources = {'code': _snapshot(root, code), 'inputs': _snapshot(root, inputs)}
    if entry_review is not None:
        code_bindings=[x['resolved_path']+'@'+x['sha256'] for x in before_sources['code']]
        review_issues=audit_entry_review(root,entry_review,command,code_bindings)
        if review_issues: raise ValueError('; '.join(review_issues))
    # Require fresh outputs; never silently bind an old result to a new run.
    before = {name: (sha256(resolve(root, name)), resolve(root, name).stat().st_mtime_ns)
              for name in outputs if resolve(root, name).is_file()}
    start = datetime.now(timezone.utc).isoformat(); clock = time.perf_counter()
    executable = shutil.which(command[0]) if not Path(command[0]).is_absolute() else command[0]
    process_error = None
    try:
        proc = subprocess.run(command, cwd=root, capture_output=True, text=True)
        process_exit_code = proc.returncode; stdout, stderr = proc.stdout, proc.stderr
    except OSError as error:
        process_exit_code = None  # No child exit occurred; never fabricate 127.
        process_error = str(error); stdout, stderr = '', process_error
    after_sources = {'code': _snapshot(root, code), 'inputs': _snapshot(root, inputs)}
    changed = [pre['path'] for key in before_sources
               for pre, post in zip(before_sources[key], after_sources[key]) if pre != post]
    receipt.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(stdout+'\nSTDERR\n'+stderr, encoding='utf-8')
    def bindings(items):
        return [x['resolved_path']+'@'+x['sha256'] for x in items]
    stale = [name for name in outputs if not resolve(root, name).is_file()
             or (name in before and before[name] == (sha256(resolve(root, name)), resolve(root, name).stat().st_mtime_ns))]
    data = {"schema_version": "5.1.2", "kind": "EXECUTION_RECEIPT", "command": command, "cwd": str(root), "started_at": start,
            "finished_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.perf_counter()-clock,
            "runtime": {"python": sys.version, "recorder_python": sys.version, "platform": platform.platform(),
                        "executable": str(Path(executable).resolve()) if executable else None,
                        "environment": {k: os.environ[k] for k in ('PYTHONPATH', 'PYTHONSAFEPATH', 'PYTHONDONTWRITEBYTECODE') if k in os.environ}},
            "exit_code": process_exit_code, "process_exit_code": process_exit_code, "process_error": process_error,
            "execution_binding": entry,
            "integrity": {"status": "FAIL" if changed else "PASS", "before": before_sources, "after": after_sources, "changed": changed},
            "provenance_status": "FAIL" if changed or stale else "PASS" if entry['status'] == 'VERIFIED_ENTRY' else "LIMITED",
            "fresh_output_errors": stale,
            "code": bindings(before_sources['code']), "inputs": bindings(before_sources['inputs']),
            "outputs": [str(resolve(root, x).resolve())+'@'+sha256(resolve(root, x)) for x in outputs if resolve(root, x).is_file()],
            "log": str(log)+'@'+sha256(log)}
    data['validation_limitations'] = run_provenance_limitations(data)
    if entry_review is not None: data['entry_review']=entry_review
    receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return data


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root", type=Path, required=True)
    for name in ("code", "input", "output"):
        ap.add_argument("--"+name, action="append", default=[])
    ap.add_argument("--receipt", required=True)
    ap.add_argument('--entry-review',type=Path,help='Existing REVIEWED_ARGUMENT JSON for complex entry; binds exact argv and code hashes, not auto certification')
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a=ap.parse_args(); command=a.command[1:] if a.command[:1]==["--"] else a.command
    try:
        review=json.loads(a.entry_review.read_text()) if a.entry_review else None
        data=record_run(a.root, command, a.code, a.input, a.output, a.receipt, entry_review=review)
    except (ValueError, OSError) as error: ap.error(str(error))
    print("EXECUTION RECORDED", data["process_exit_code"], "PROVENANCE", data['provenance_status'])
    return 0 if data["process_exit_code"] == 0 and (data['provenance_status']=='PASS' or data['provenance_status']=='LIMITED' and review is not None) else 1


if __name__ == "__main__":
    raise SystemExit(main())
