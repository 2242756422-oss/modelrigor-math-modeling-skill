"""Evidence checks, not certificates of scientific truth. Standard library only.

Run receipts bind execution products. An auditor never executes an untrusted
command from a receipt. General proofs and scientific judgments remain reviewed
arguments, not machine-proven theorems or nominally independent PASS files.
"""
from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


def execution_entry(root: Path, command: list[str], code: list[str], environment: dict | None = None):
    """Identify common Python argv entries without executing/importing code.

    Bind an entry, not a dynamic call graph. Shell/inline/installed-module
    resolution needs substantive evidence, never automatic approval.
    """
    root = Path(root).resolve()
    answer = {"status": "UNVERIFIED", "kind": "UNSUPPORTED_COMMAND", "entrypoint": None,
              "scope": "ARGV_ENTRY_ONLY; declared dependencies are not proof of imports",
              "module_initializers": [], "reason": "not a supported Python source invocation"}
    if not isinstance(command, list) or not command or any(not isinstance(x, str) for x in command):
        return answer
    if not re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", Path(command[0]).name):
        return answer
    args = command[1:]; i = 0; no_local_path = False; ignore_environment = False
    while i < len(args):
        arg = args[i]
        if arg == '--':
            i += 1; break
        if arg in ('-W', '-X', '--check-hash-based-pycs'):
            i += 2; continue
        if arg.startswith(('-W', '-X')) and len(arg) > 2:
            i += 1; continue
        if re.fullmatch(r'-[bBdEIOPqRsSuv]+', arg):
            no_local_path |= 'I' in arg or 'P' in arg
            ignore_environment |= 'I' in arg or 'E' in arg
            i += 1; continue
        break
    if i >= len(args) or args[i] in ('-c', '-', '-i'):
        answer['reason'] = 'inline/stdin/interactive Python has no automatically bound source entry'
        return answer
    arg = args[i]
    if arg == '-m':
        if no_local_path or (not ignore_environment and (environment or {}).get('PYTHONSAFEPATH')):
            answer['reason'] = 'module search excludes cwd; external resolution not certified'
            return answer
        if i+1 >= len(args) or not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', args[i+1]):
            return answer
        parts = args[i+1].split('.'); directory = root; initializers = []
        for part in parts[:-1]:
            directory /= part
            init = directory/'__init__.py'
            if not init.is_file():
                answer['reason'] = 'namespace/external packages require explicit evidence'; return answer
            initializers.append(str(init.resolve()))
        package = directory/parts[-1]
        if (package/'__init__.py').is_file():
            initializers.append(str((package/'__init__.py').resolve()))
            entry = package/'__main__.py'
        else:
            entry = directory/(parts[-1]+'.py')
        answer['kind'] = 'PYTHON_LOCAL_MODULE'
        answer['module_initializers'] = initializers
    elif arg.startswith('-'):
        answer['reason'] = 'unrecognized interpreter option; no substring inference'; return answer
    else:
        entry = Path(arg) if Path(arg).is_absolute() else root/arg
        if entry.suffix.lower() != '.py' or not entry.is_file():
            answer['reason'] = 'only direct .py files and local source modules are auto-bound'; return answer
        answer['kind'] = 'PYTHON_SCRIPT'
    if not entry.is_file():
        answer['reason'] = 'local module entry not found'; return answer
    entry = entry.resolve(); answer['entrypoint'] = str(entry)
    declared = {(Path(x) if Path(x).is_absolute() else root/x).resolve() for x in code}
    answer['status'] = 'VERIFIED_ENTRY' if entry in declared else 'MISMATCH'
    answer['reason'] = 'canonical entry matches declared code' if entry in declared else 'actual Python entry is not a declared code artifact'
    return answer


def run_provenance_limitations(receipt: dict):
    if receipt.get('schema_version') != '5.1.2':
        return ['LEGACY_POST_RUN_ONLY: no execution-time pre-hash or mutation history; argv entry rechecked only']
    return ['PRE_POST_ONLY: unchanged endpoints do not prove absence of transient changes',
            'ENTRY_ONLY: no full dynamic import/child-process/input-read proof; complex entries require reviewed evidence']


def audit_entry_review(base:Path, review:dict, command:list, code:list):
    """Reuse REVIEWED_ARGUMENT, explicitly not automatic command certification."""
    if not isinstance(review,dict) or review.get('kind')!='REVIEWED_ARGUMENT':
        return ['complex entry requires a substantive reviewed argument']
    issues=audit_verification(base,review,{})
    if review.get('command')!=command or set(review.get('code',[]))!=set(code):
        issues.append('entry review does not bind the actual argv and code hashes')
    return issues


def source_equal(a, b):
    """Source transcription is exact; computational uncertainty belongs elsewhere."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isfinite(a) and math.isfinite(b) and a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(source_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(source_equal(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def display_matches(raw, display):
    """Allow only rounding implied by the displayed decimal quantum, not a user tol."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return str(raw) == str(display)
    try:
        number = Decimal(str(raw)); shown = Decimal(str(display))
        if not number.is_finite() or not shown.is_finite():
            return False
        quantum = Decimal(1).scaleb(shown.as_tuple().exponent)
        # A shown integer must actually be nearest that integer; large source
        # errors cannot be hidden behind an inflated display_tolerance.
        return abs(number - shown) <= abs(quantum) / 2
    except (InvalidOperation, ValueError):
        return False


def check_assertions(output):
    """Re-evaluate supported relations; status text alone has no weight."""
    from core import equal_value
    rows = output.get("checks", []) if isinstance(output, dict) else []
    if not rows:
        return ["no machine-readable verification assertions"]
    issues = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("purpose"):
            issues.append(f"assertion {i}: purpose missing"); continue
        relation = row.get("relation")
        if relation == "exact":
            ok = source_equal(row.get("actual"), row.get("expected"))
        elif relation == "close":
            try:
                atol, rtol = float(row["atol"]), float(row["rtol"])
                expected = float(row["expected"])
                ok = (all(math.isfinite(v) and v >= 0 for v in (atol, rtol))
                      and bool(row.get("tolerance_basis"))
                      and equal_value(row.get("actual"), expected, atol + rtol * abs(expected)))
            except (KeyError, ValueError, TypeError):
                ok = False
        else:
            ok = False
        if not ok:
            issues.append(f"assertion {i}: unsupported or failed relation")
    return issues


def audit_run(base: Path, binding: str, expected_output: str | None = None):
    from core import load_json, resolve, sha256, validate_file_binding
    if not validate_file_binding(base, binding):
        return ["execution receipt missing or stale"], None
    receipt_path = resolve(base, binding.rsplit("@", 1)[0])
    receipt = load_json(receipt_path); rb = receipt_path.parent; issues = []
    if receipt.get("kind") != "EXECUTION_RECEIPT" or receipt.get("exit_code") != 0:
        issues.append("receipt is not a successful recorded execution")
    cwd = Path(receipt.get('cwd', str(base))).resolve()
    entry = execution_entry(cwd, receipt.get('command', []),
                            [str(resolve(rb, x.rsplit('@', 1)[0])) for x in receipt.get('code', [])],
                            receipt.get('runtime', {}).get('environment', {}))
    reviewed_entry=False
    if entry['status'] == 'UNVERIFIED' and receipt.get('entry_review'):
        review_issues=audit_entry_review(cwd,receipt['entry_review'],receipt.get('command',[]),receipt.get('code',[]))
        issues.extend(review_issues); reviewed_entry=not review_issues
    if entry['status'] != 'VERIFIED_ENTRY' and not reviewed_entry:
        issues.append('execution entry not verified: '+entry['reason'])
    if receipt.get('schema_version') == '5.1.2':
        if receipt.get('process_exit_code') != receipt.get('exit_code') or receipt.get('process_exit_code') != 0:
            issues.append('actual process exit status is unsuccessful or inconsistent')
        allowed_status=('PASS','LIMITED') if reviewed_entry else ('PASS',)
        if receipt.get('provenance_status') not in allowed_status or receipt.get('fresh_output_errors'):
            issues.append('recorded source/output integrity did not pass')
        if receipt.get('execution_binding') != entry:
            issues.append('execution entry binding differs from recorded argv')
        integrity = receipt.get('integrity', {})
        if integrity.get('status') != 'PASS' or integrity.get('changed'):
            issues.append('code/input changed during execution')
        for key in ('code', 'inputs'):
            pre = integrity.get('before', {}).get(key)
            post = integrity.get('after', {}).get(key)
            if not isinstance(pre, list) or pre != post or not pre and key == 'code':
                issues.append('missing or inconsistent pre/post snapshot: '+key); continue
            specs = receipt.get(key, [])
            snapshot_bindings = [x.get('resolved_path', '')+'@'+str(x.get('sha256', '')) for x in pre]
            if specs != snapshot_bindings:
                issues.append('dependency binding differs from pre-run snapshot: '+key)
            for item in pre:
                artifact = Path(item.get('path', ''))
                if not artifact.is_file() or str(artifact.resolve()) != item.get('resolved_path') or sha256(artifact) != item.get('sha256'):
                    issues.append('snapshot dependency changed or retargeted: '+str(artifact))
        declared_paths = {str(resolve(rb, x.rsplit('@', 1)[0]).resolve()) for x in receipt.get('code', [])}
        if not set(entry['module_initializers']).issubset(declared_paths):
            issues.append('module initialization source not bound')
    else:
        # Old valid receipts retain only their original, post-run evidence scope.
        receipt = dict(receipt, validation_limitations=run_provenance_limitations(receipt))
    if reviewed_entry:
        receipt=dict(receipt, entry_assurance='REVIEWED_ARGUMENT_NOT_AUTOMATIC_ENTRY_CERTIFICATION')
    for key in ("command", "started_at", "finished_at", "runtime", "code", "outputs", "log"):
        if not receipt.get(key):
            issues.append(f"execution receipt missing {key}")
    for spec in receipt.get("code", []) + receipt.get("inputs", []) + receipt.get("outputs", []) + [receipt.get("log", "")]:
        if not validate_file_binding(rb, spec):
            issues.append("execution dependency missing or stale: " + spec)
    output_paths = [resolve(rb, x.rsplit("@", 1)[0]).resolve() for x in receipt.get("outputs", [])]
    if expected_output and resolve(base, expected_output).resolve() not in output_paths:
        issues.append("verification output not produced by the recorded execution")
    return issues, receipt


def audit_verification(base: Path, record: dict, result: dict):
    from core import load_json, resolve, json_pointer, validate_hashed_locator, equal_value
    kind = record.get("kind"); issues = []
    if kind == "EXECUTED_CHECK":
        local, receipt = audit_run(base, record.get("run_receipt", ""), record.get("output_artifact"))
        issues.extend(local)
        output = resolve(base, record.get("output_artifact", ""))
        if not output.is_file():
            return issues + ["verification output missing"]
        try:
            data = load_json(output)
            issues.extend(check_assertions(data))
            observed = json_pointer(data, record.get("observed_pointer", "/observed_value"))
        except (ValueError, KeyError, TypeError, IndexError):
            return issues + ["verification output/pointer invalid"]
        if "observed_value" in record and not source_equal(observed,record["observed_value"]):
            issues.append("declared observed value differs from executed verification output")
        try:
            accuracy = record.get("accuracy", {})
            atol, rtol = float(accuracy.get("atol", 0)), float(accuracy.get("rtol", 0))
            if not all(math.isfinite(x) and x >= 0 for x in (atol, rtol)):
                raise ValueError("accuracy")
            if (atol or rtol) and not validate_hashed_locator(base, accuracy.get("basis", "")):
                issues.append("numerical comparison tolerance lacks a reviewed basis")
            expected = result.get("raw_value")
            tol = atol + rtol * abs(float(expected)) if isinstance(expected, (int, float)) else 0
            if not equal_value(observed, expected, tol):
                issues.append("executed verification output disagrees with registered result")
        except (ValueError, TypeError):
            issues.append("verification accuracy invalid")
        if record.get("independent"):
            primary = result.get("computation_receipt", "")
            pissues, primary_receipt = audit_run(base, primary)
            issues.extend(pissues)
            # Distinct receipts/method strings alone are not independence.
            if receipt and primary_receipt:
                def entry_hashes(run):
                    rb=Path(run.get('cwd',str(base))).resolve()
                    paths=[x.rsplit('@',1)[0] for x in run.get('code',[])]
                    entry=execution_entry(rb,run.get('command',[]),paths,run.get('runtime',{}).get('environment',{})).get('entrypoint')
                    return {x.rsplit('@',1)[-1] for x in run.get('code',[]) if Path(x.rsplit('@',1)[0]).resolve()==Path(entry or rb).resolve()}
                # Attaching an unused helper is not an independent implementation.
                verifier_hashes = entry_hashes(receipt)
                primary_hashes = entry_hashes(primary_receipt)
                if not verifier_hashes - primary_hashes:
                    issues.append("independent implementation not demonstrated")
            if not record.get("independence_basis"):
                issues.append("independence scope/basis missing")
    elif kind == "REVIEWED_ARGUMENT":
        # These are explicit, attributed judgments, never an automatic proof.
        for key in ("argument", "review_evidence"):
            if not validate_hashed_locator(base, record.get(key, "")):
                issues.append(f"reviewed argument lacks {key}")
        review = record.get("substantive_review", {})
        if not all(review.get(k) for k in ("reviewer", "reasoning", "scope", "limitations")) or review.get("outcome") != "ACCEPTED":
            issues.append("argument requires substantive, attributed scientific review")
        if record.get("independent"):
            issues.append("independent computation cannot be claimed for a reviewed argument")
    else:
        issues.append("verification is only a declaration; executed check or reviewed argument required")
    return issues


def audit_result_origin(base:Path,result:dict):
    """Source nature is distinct from its JSON/CSV addressing format."""
    from core import load_json, resolve, validate_hashed_locator
    source=result.get('source',{})
    category=source.get('category')
    if category is None:
        category={'analytical':'ANALYTICAL','json_pointer':'COMPUTED'}.get(source.get('type'))
    if category not in ('COMPUTED','ANALYTICAL','OBSERVED','GIVEN','DEMO'):
        return ['source category unresolved; distinguish computation, derivation, observation, given parameter and demo']
    issues=[]
    if category=='COMPUTED':
        local,_=audit_run(base,result.get('computation_receipt',''),source.get('artifact'))
        issues.extend('production computation: '+x for x in local)
    elif category=='ANALYTICAL':
        arguments=[]
        for binding in result.get('verification',[]):
            path=resolve(base,binding.get('artifact',''))
            if not path.is_file(): continue
            try: record=load_json(path)
            except (ValueError,OSError): continue
            if record.get('kind')=='REVIEWED_ARGUMENT': arguments.append(record)
            if record.get('argument_check'): arguments.append(record['argument_check'])
        valid=[x for x in arguments if isinstance(x,dict) and x.get('kind')=='REVIEWED_ARGUMENT'
               and 'observed_value' in x and source_equal(x['observed_value'],result.get('raw_value'))
               and not audit_verification(base,x,result)]
        if not valid: issues.append('analytical result requires a bound derivation and substantive review, not a handwritten numeric JSON or numerical substitution alone')
    elif category in ('OBSERVED','GIVEN'):
        origin=source.get('origin',{})
        if not origin.get('nature') or not origin.get('provider') or not validate_hashed_locator(base,origin.get('locator','')):
            issues.append('observation/given parameter requires original provenance, provider and explicit nature')
    else:
        if not source.get('demo_label'): issues.append('demo data must be explicitly labelled')
        if result.get('approved'): issues.append('demo data cannot be promoted as an approved scientific result')
    return issues
