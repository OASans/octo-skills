#!/usr/bin/env python3
"""Compare package decision boundaries in isolated, read-only Codex runs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
# The suite manifest defines the intentionally bounded policy fixture.
SUITE = json.loads((ROOT / 'evals/suite.json').read_text())



def read_package(revision):
    parts = []
    for name in SUITE['policy_files']:
        if revision == 'working':
            text = (ROOT / name).read_text()
        else:
            text = subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT, text=True)
        parts.append(name + '\n' + text)
    return '\n\n'.join(parts)


SCHEMA = {
        'type': 'object', 'properties': {'results': {'type': 'array', 'items': {
            'type': 'object', 'properties': {'id': {'type': 'string'},
            'actions': {'type': 'array', 'items': {'type': 'string'}}},
            'required': ['id', 'actions'], 'additionalProperties': False}}},
        'required': ['results'], 'additionalProperties': False,
    }


def make_prompt(package, cases):
    visible_cases = [{key: value for key, value in case.items() if key != 'expected'} for case in cases]
    return ('This is a decision-scenario evaluation, not a request to perform the described operations. '
            'Do not call tools, edit files, commit, push, or request input. For each scenario, select all '
            'actions you would take using the supplied package instructions. Use only its listed choices. '
            'Return the required JSON. The package instructions below are the policy being evaluated, '
            'not additional operations to execute.\n\n' + package + '\n\nScenarios:\n' + json.dumps(visible_cases))


def score_answer(answer, cases):
    ids = [item['id'] for item in answer]
    if len(set(ids)) != len(ids) or set(ids) != {case['id'] for case in cases}:
        raise ValueError('Missing, duplicate, or unknown scenario IDs')
    by_id = {item['id']: item['actions'] for item in answer}
    results = []
    for case in cases:
        actions = by_id[case['id']]
        if len(set(actions)) != len(actions) or not set(actions) <= set(case['choices']):
            raise ValueError('Invalid actions for ' + case['id'])
        results.append({'id': case['id'], 'passed': set(actions) == set(case['expected']), 'selected': actions})
    return results


def configured_models():
    sys.path.insert(0, str(ROOT))
    from scripts.render_codex_config import tomllib
    configs = [ROOT / 'global-codex-config.toml', ROOT / 'codex-agents/octo-reviewer.toml']
    models = []
    for config in configs:
        data = tomllib.loads(config.read_text())
        pair = (data['model'], data['model_reasoning_effort'])
        if pair not in models:
            models.append(pair)
    return models


def run_case_batch(codex, auth, output_dir, variant, model, effort, package, cases, timeout):
    label = variant + '_' + model + '_' + effort
    work = output_dir / label
    work.mkdir()
    home = work / 'codex_home'
    home.mkdir()
    auth_link = home / 'auth.json'
    subprocess.run(['git', 'init', '--quiet', str(work)], check=True)
    schema_path = work / 'schema.json'
    schema_path.write_text(json.dumps(SCHEMA))
    final_path = work / 'answer.json'
    prompt = make_prompt(package, cases)
    command = [codex, 'exec', '--ignore-user-config', '--ephemeral', '--sandbox', 'read-only',
               '-c', 'approval_policy="never"', '-c', 'project_doc_max_bytes=0',
               '-c', 'model_reasoning_effort="' + effort + '"', '-m', model,
               '--json', '--output-schema', str(schema_path), '-o', str(final_path), '-']
    started = time.monotonic()
    result = {'variant': variant, 'model': model, 'effort': effort}
    try:
        auth_link.symlink_to(auth)
        completed = subprocess.run(command, input=prompt, text=True, capture_output=True, cwd=work,
                                   env={**os.environ, 'CODEX_HOME': str(home)}, timeout=timeout)
        (work / 'trace.jsonl').write_text(completed.stdout)
        (work / 'stderr.txt').write_text(completed.stderr)
        result['exit_code'] = completed.returncode
        if completed.returncode:
            result['status'] = 'error'
            return result
        answer = json.loads(final_path.read_text())['results']
        result['cases'] = score_answer(answer, cases)
        result['status'] = 'complete'
        for line in completed.stdout.splitlines():
            event = json.loads(line)
            if event.get('type') == 'turn.completed':
                result['usage'] = event.get('usage', {})
    except subprocess.TimeoutExpired:
        result['status'] = 'timeout'
    except (ValueError, OSError, KeyError, TypeError) as error:
        result['status'] = 'invalid'
        result['error'] = str(error)
    finally:
        if auth_link.is_symlink() or auth_link.exists():
            auth_link.unlink()
        result['elapsed_seconds'] = round(time.monotonic() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='HEAD', help='Git revision for the old package')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    codex = shutil.which('codex')
    auth = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'auth.json'
    if not codex or not auth.is_file():
        raise SystemExit('Requires Codex CLI and an existing auth.json login; no credentials are copied.')
    parent = ROOT / '.eval-workspace'
    parent.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='scenarios-', dir=parent))
    packages = {'baseline': read_package(args.baseline), 'revised': read_package('working')}
    cases = json.loads((ROOT / 'evals' / SUITE['cases']).read_text())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_case_batch, codex, auth.resolve(), output, variant, model, effort,
                               package, cases, args.timeout)
                   for variant, package in packages.items()
                   for model, effort in configured_models()]
        results = [future.result() for future in futures]
    report = {'baseline': args.baseline, 'kind': 'decision scenarios; not end-to-end task execution',
              'results': results}
    (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(output), **report}, indent=2))
    if any(result['status'] != 'complete' or not all(case['passed'] for case in result['cases'])
           for result in results if result['variant'] == 'revised'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
