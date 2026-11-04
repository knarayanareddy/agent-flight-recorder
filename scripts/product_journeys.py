"""Run bounded authenticated journeys against an implementation.
Standalone-scoped: Configured to test AFR domain journeys by default.
Override with BASELINE_PRODUCT=all to run full cross-product suite.
"""
import os, sys, json, uuid, time, hashlib, io, zipfile, copy
from pathlib import Path
import httpx

P = Path(__file__).resolve().parents[1]

def main():
    target_mode = os.getenv('BASELINE_PRODUCT', 'afr').lower()
    VALID_PRODUCTS = {'afr', 'skb', 'evf', 'all'}
    if target_mode not in VALID_PRODUCTS:
        print(f"BLOCKED: Invalid BASELINE_PRODUCT='{target_mode}'. Allowed values: {sorted(VALID_PRODUCTS)}")
        return 2

    required = ['BASELINE_URL', 'BASELINE_TEST_KEY', 'BASELINE_TEST_PROJECT']
    if any(not os.getenv(k) for k in required) or os.getenv('BASELINE_TEST_CONFIRM') != 'synthetic_disposable_project':
        print('BLOCKED: configure URL/key/project and explicit disposable-project confirmation.')
        return 2
    base = os.environ['BASELINE_URL']
    project = os.environ['BASELINE_TEST_PROJECT']
    key = os.environ['BASELINE_TEST_KEY']
    if not (base.startswith('https://') or base.startswith('http://127.0.0.1:') or base.startswith('http://localhost:')):
        raise ValueError('TLS or loopback required')
    headers = {'X-API-Key': key, 'X-Project-ID': project}
    results = []
    with httpx.Client(base_url=base, headers=headers, timeout=15, follow_redirects=False, trust_env=False) as c:
        def call(method, path, body=None, status=200, extra=None, raw=None):
            h = {'Idempotency-Key': str(uuid.uuid4())}
            h.update(extra or {})
            kw = {'headers': h}
            if raw is not None:
                kw['content'] = raw
                h['Content-Type'] = 'application/octet-stream'
            elif body is not None:
                kw['json'] = body
            r = c.request(method, path, **kw)
            if r.status_code != status:
                raise AssertionError(f'{method} {path}: expected {status}, got {r.status_code}; request_id={r.headers.get("x-request-id","unknown")}')
            return r

        def upload(blob, media, name):
            sha = hashlib.sha256(blob).hexdigest()
            u = call('POST', f'/api/v1/projects/{project}/uploads', {'filename': name, 'media_type': media, 'byte_size': len(blob), 'sha256': sha, 'classification': 'synthetic'}, 201).json()
            call('PUT', u['put_path'], raw=blob)
            return call('POST', f'/api/v1/uploads/{u["id"]}:finalize', {'sha256': sha, 'byte_size': len(blob)}).json()

        def wait_job(j):
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                x = call('GET', '/api/v1/jobs/' + j['id']).json()
                if x['state'] == 'succeeded':
                    return x
                if x['state'] in ('failed', 'cancelled', 'timed_out', 'failed_unknown_effect'):
                    raise AssertionError('job ' + x['state'])
                time.sleep(.2)
            raise AssertionError('job timeout at acceptance boundary')

        def afr():
            e = json.loads((P / 'contracts/examples/Event.valid.json').read_text())
            run = str(uuid.uuid4())
            e.update(event_id=str(uuid.uuid4()), run_id=run, producer_id='acceptance', producer_seq=0, event_type='run.started', capture_policy_id=str(uuid.uuid5(uuid.UUID(project), 'metadata_only:v1')))
            e['payload'] = {}
            end = copy.deepcopy(e)
            end.update(event_id=str(uuid.uuid4()), producer_seq=1, event_type='run.finished')
            end['payload'] = {'outcome': 'success'}
            body = {'events': [e, end]}
            url = f'/api/v1/projects/{project}/afr/events:batch'
            x = call('POST', url, body, 202).json()
            assert len(x['accepted']) == 2
            y = call('POST', url, body, 202).json()
            assert len(y['duplicates']) == 2
            r = call('GET', '/api/v1/afr/runs/' + run).json()
            recording = {'schema_version': 'afr-recording/1', 'final_output': {'ok': True}, 'final_state': {'balance': 0}, 'tool_results': []}
            artifact = upload(json.dumps(recording).encode(), 'application/json', 'recording.json')
            case = call('POST', f'/api/v1/projects/{project}/afr/cases', {'run_id': run, 'run_revision': r['revision'], 'name': 'acceptance case', 'mode': 'recorded', 'checks': [{'kind': 'json_equals', 'path': '/ok', 'expected': True}, {'kind': 'mock_state_equals', 'path': '/balance', 'expected': 0}], 'fixture_artifact_ids': [artifact['id']]}, 201).json()
            job = call('POST', f'/api/v1/projects/{project}/afr/replays', {'case_id': case['id'], 'case_version': case['version'], 'mode': 'recorded', 'maximum_seconds': 30}, 202).json()
            done = wait_job(job)
            out = call('GET', '/api/v1/afr/replays/' + done['result_id']).json()
            assert out['state'] == 'pass' and out['network_calls'] == 0

        def skb():
            b = io.BytesIO()
            with zipfile.ZipFile(b, 'w') as z:
                z.writestr('SKILL.md', '---\nname: dummy\ndescription: dummy\n---\nbody')
            blob = b.getvalue()
            sha = hashlib.sha256(blob).hexdigest()
            u = upload(blob, 'application/zip', 'skill.zip')
            pkg = call('POST', f'/api/v1/projects/{project}/skb/packages', {'artifact_id': u['id'], 'name': 'dummy skill', 'source_commit': 'a' * 40, 'license_expression': 'MIT'}, 201).json()
            call('POST', f'/api/v1/skb/packages/{pkg["id"]}:inspect', status=202)
            r = call('GET', f'/api/v1/skb/packages/{pkg["id"]}')
            etag = r.headers['etag']
            call('POST', f'/api/v1/skb/packages/{pkg["id"]}/reviews', {'decision': 'approved', 'package_sha256': sha, 'reason': 'human audit verified safe sandbox profile'}, 201, {'If-Match': etag})
            task_raw = {'id': 't1', 'category': 'math', 'input_artifact_id': u['id'], 'split': 'validation', 'scorer_id': 'exact_match'}
            suite = call('POST', f'/api/v1/projects/{project}/skb/suites', {'name': 'acceptance suite', 'tasks': [task_raw], 'rights_manifest_artifact_id': u['id']}, 201).json()
            plan = call('POST', f'/api/v1/projects/{project}/skb/plans', {'package_id': pkg['id'], 'suite_id': suite['id'], 'tasks': [task_raw]}, 201).json()
            call('POST', f'/api/v1/skb/plans/{plan["id"]}:preregister', status=200, extra={'If-Match': call('GET', f'/api/v1/skb/plans/{plan["id"]}').headers['etag']})
            exp = call('POST', f'/api/v1/projects/{project}/skb/experiments', {'plan_id': plan['id']}, 202).json()
            wait_job({'id': exp['job_id']})
            call('POST', f'/api/v1/skb/experiments/{exp["id"]}/analyses', status=201)

        def evf():
            a = upload((P / 'fixtures/synthetic-report.pdf').read_bytes(), 'application/pdf', 'synthetic-report.pdf')
            doc = call('POST', f'/api/v1/projects/{project}/evf/documents', {'artifact_id': a['id'], 'title': 'Synthetic acceptance report'}, 201).json()
            parse = call('POST', f'/api/v1/evf/documents/{doc["id"]}/parses', {'profile': 'fixture/1', 'source_sha256': a['sha256']}, 202).json()
            wait_job({'id': parse['job_id']})
            e = call('POST', f'/api/v1/projects/{project}/evf/extractions', {'schema_version': 'annual-report-8/1', 'method': 'fixture', 'parse_id': parse['id']}, 201).json()
            fields = {f['key']: f for f in e['fields']}
            assert len(fields) == 8
            assert fields['revenue_current']['value'] == '1234000'
            rr = call('GET', f'/api/v1/evf/extractions/{e["id"]}')
            etag = rr.headers['etag']
            body = {'base_revision': e['revision'], 'patches': [{'key': 'revenue_current', 'action': 'accept', 'reason': 'checked synthetic source evidence'}]}
            rev = call('POST', f'/api/v1/evf/extractions/{e["id"]}/reviews', body, 201, {'If-Match': etag}).json()
            call('POST', f'/api/v1/evf/extractions/{e["id"]}/reviews', body, 412, {'If-Match': etag})
            out = call('POST', f'/api/v1/evf/extractions/{e["id"]}/exports', {'review_revision': rev['revision'], 'format': 'json', 'allow_incomplete': True}, 201).json()
            assert out['incomplete'] is True
            data = call('GET', f'/api/v1/artifacts/{out["artifact_id"]}/bytes').json()
            assert data['schema_version'] == 'evf-export/1'
            call('DELETE', f'/api/v1/evf/documents/{doc["id"]}', status=202)
            call('GET', f'/api/v1/evf/documents/{doc["id"]}', status=404)

        all_journeys = [('afr', afr), ('skb', skb), ('evf', evf)]
        if target_mode != 'all':
            all_journeys = [(k, fn) for k, fn in all_journeys if k == target_mode]

        if not all_journeys:
            print(f"BLOCKED: No journeys matched product filter '{target_mode}'")
            return 2

        for name, f in all_journeys:
            try:
                f()
                results.append({'journey': name, 'status': 'passed'})
            except Exception as e:
                results.append({'journey': name, 'status': 'failed', 'error_type': type(e).__name__, 'detail': str(e)[:400]})

    out = {
        'kind': 'bounded_real_api_journeys',
        'product_scope': target_mode,
        'results': results,
        'not_covered': ['browser UI', 'role matrix', 'OIDC login', 'actual Docling', 'hostile execution', 'production operations']
    }
    (P / 'evidence/product-journeys.json').write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0 if (results and all(x['status'] == 'passed' for x in results)) else 1

if __name__ == '__main__':
    sys.exit(main())
