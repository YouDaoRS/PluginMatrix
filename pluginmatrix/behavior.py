"""Bounded behavior plans, host assertions and request/response orchestration.

The probe reports observations, never verdicts. Runtime success is a prerequisite,
not a consequence of behavior success. This protocol is not a hostile-JVM sandbox.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .control import RunCancelled
from .files import atomic_text, reject_links, read_evidence_bytes
from .probe import PROBE_FRESHNESS_SECONDS, read_probe_evidence

REQUEST_FILE = 'pluginmatrix-behavior-request.properties'
RESPONSE_FILE = 'pluginmatrix-behavior-response.json'
KINDS = ('command_registered', 'permission_registered', 'service_registered', 'console_command', 'wait')
STATUSES = ('PASS', 'FAIL', 'ERROR', 'TIMEOUT', 'CANCELLED', 'UNSUPPORTED', 'SKIPPED', 'NOT_RUN')


@dataclass(frozen=True)
class BehaviorPlan:
    # Canonical JSON is immutable, including nested checks/argument arrays.
    canonical: str

    def to_dict(self):
        return json.loads(self.canonical)

    @property
    def digest(self):
        return hashlib.sha256(self.canonical.encode('utf-8')).hexdigest()


def _seconds(value, label, maximum):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError(f'{label} must be finite seconds in (0, {maximum}]')
    return value


def parse_behavior(value) -> BehaviorPlan | None:
    if value is None:
        return None
    if isinstance(value, BehaviorPlan):
        value = value.to_dict()
    if not isinstance(value, dict) or set(value) - {'schema', 'timeout', 'checks'}:
        raise ValueError('behavior requires schema, optional timeout, and checks; unknown fields are rejected')
    if type(value.get('schema')) is not int or value['schema'] != 1:
        raise ValueError('behavior.schema must be 1')
    checks = value.get('checks')
    if not isinstance(checks, list) or not 1 <= len(checks) <= 64:
        raise ValueError('behavior.checks must contain 1..64 checks')
    normalized, seen = [], set()
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError('each behavior check must be an object')
        kind, ident = check.get('type'), check.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', ident) or ident in seen:
            raise ValueError('behavior check id must be unique and use 1..64 letters, digits, underscore or hyphen')
        seen.add(ident)
        if kind not in KINDS:
            raise ValueError(f'unsupported behavior check type: {kind!r}')
        allowed = {'id', 'type', 'timeout'} | ({'seconds'} if kind == 'wait' else {'name', 'expect'})
        if kind == 'console_command':
            allowed.add('args')
        if set(check) - allowed:
            raise ValueError(f'unknown fields in behavior check {ident}')
        item = {'id': ident, 'type': kind, 'timeout': _seconds(check.get('timeout', 5), ident + '.timeout', 30)}
        if kind == 'wait':
            item['seconds'] = _seconds(check.get('seconds'), ident + '.seconds', 30)
            if item['seconds'] >= item['timeout']:
                raise ValueError('wait.seconds must be less than its timeout (allow time for a fresh final sample)')
        else:
            name = check.get('name')
            pattern = r'[A-Za-z_$][A-Za-z0-9_.$]{0,255}' if kind == 'service_registered' else r'[a-z0-9_.:-]{1,128}'
            if not isinstance(name, str) or not re.fullmatch(pattern, name):
                raise ValueError(f'invalid behavior name in {ident}')
            if type(check.get('expect', True)) is not bool:
                raise ValueError(f'{ident}.expect must be a boolean')
            item.update(name=name, expect=check.get('expect', True))
            if kind == 'console_command':
                args = check.get('args', [])
                if not isinstance(args, list) or len(args) > 16 or any(
                    not isinstance(arg, str) or len(arg) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in arg)
                    for arg in args
                ):
                    raise ValueError('console args must be at most 16 strings of at most 256 characters without controls')
                item['args'] = args
        normalized.append(item)
    document = {'schema': 1, 'timeout': _seconds(value.get('timeout', 60), 'behavior.timeout', 300), 'checks': normalized}
    return BehaviorPlan(json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True))


def initial_behavior(plan, reason='runtime prerequisite did not pass'):
    return {'schema': 1, 'verdict': 'SKIPPED' if plan else 'NOT_RUN', 'reason': reason if plan else None,
            'scope': 'Assertions over declared observations only; console return values do not prove gameplay correctness.',
            'plan': plan.to_dict() if plan else None, 'plan_sha256': plan.digest if plan else None,
            'checks': [dict(id=c['id'], type=c['type'], status='SKIPPED', reason=reason, evidence={})
                       for c in plan.to_dict()['checks']] if plan else [],
            'post_health': {'status': 'NOT_RUN'}}


def verification_passed(runtime, behavior):
    return runtime == 'PASS' and behavior.get('verdict') in ('NOT_RUN', 'PASS')


def _read_response(path):
    try:
        data = read_evidence_bytes(path, 65536)
    except FileNotFoundError:
        return None
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError('behavior response must be an object')
    return value


def assert_observation(check, observation, target):
    """Strict typed observations; never accept a probe-supplied PASS or truthy string."""
    if not isinstance(observation, dict):
        raise ValueError('missing structured observation')
    kind = check['type']
    if kind in ('command_registered', 'console_command'):
        if type(observation.get('registered')) is not bool or type(observation.get('owned')) is not bool:
            raise ValueError('invalid command registration observation')
        if not isinstance(observation.get('owner'), str):
            raise ValueError('missing command owner')
        if observation['owned'] and (not observation['registered'] or observation['owner'] != target):
            raise ValueError('inconsistent command owner evidence')
        if kind == 'console_command':
            if not observation['owned']:
                return False  # expect=false cannot authorize a foreign/missing command.
            if type(observation.get('returned')) is not bool or observation.get('sender') != 'CONSOLE':
                raise ValueError('missing console execution evidence')
            actual = observation['returned']
        else:
            actual = observation['registered'] and observation['owned']
    elif kind == 'permission_registered':
        if type(observation.get('registered')) is not bool:
            raise ValueError('invalid permission observation')
        if observation['registered'] and observation.get('default') not in ('TRUE', 'FALSE', 'OP', 'NOT_OP'):
            raise ValueError('invalid permission default')
        actual = observation['registered']
    elif kind == 'service_registered':
        entries = observation.get('registrations')
        if not isinstance(entries, list) or len(entries) > 128:
            raise ValueError('invalid service registrations')
        for entry in entries:
            if (not isinstance(entry, dict) or entry.get('owner') != target or entry.get('service') != check['name']
                    or not isinstance(entry.get('implementation'), str) or not entry['implementation']
                    or entry.get('priority') not in ('Lowest', 'Low', 'Normal', 'High', 'Highest')):
                raise ValueError('service registration does not belong to the requested target/service')
        actual = bool(entries)
    else:
        raise ValueError('check has no server observation assertion')
    return actual is check['expect']


def validate_response(payload, *, request, check, plan, run_id, started_wall, target):
    expected = {'schema': 1, 'probe': 'pluginmatrix-behavior', 'run_id': run_id,
                'plan_sha256': plan.digest, 'request_id': request['request_id'],
                'index': request['index'], 'check_id': check['id'], 'type': check['type']}
    if any(type(payload.get(k)) is not type(v) or payload[k] != v for k, v in expected.items()):
        raise ValueError('behavior response correlation mismatch')
    completed = payload.get('completed_at_ms')
    if (type(completed) is not int or completed < started_wall
            or abs(time.time() * 1000 - completed) > PROBE_FRESHNESS_SECONDS * 1000):
        raise ValueError('behavior response timestamp is stale or in the future')
    status = payload.get('status')
    if status in ('ERROR', 'UNSUPPORTED'):
        if not isinstance(payload.get('reason'), str) or not payload['reason']:
            raise ValueError('missing behavior error/unsupported reason')
        return status, payload['reason']
    if status != 'OK':
        raise ValueError('invalid behavior response status')
    passed = assert_observation(check, payload.get('observation'), target)
    return ('PASS', None) if passed else ('FAIL', 'structured observation did not satisfy the assertion')


def run_behavior(plan, *, process, probe_path, runtime_evidence, run_id, control, environment_index, drain_log):
    """Run inside the verifier's existing process ownership/finally boundary."""
    import copy
    report = initial_behavior(plan)
    report['reason'] = None
    for entry in report['checks']:
        entry['reason'] = 'not executed because behavior verification stopped before this check'
    post = copy.deepcopy(runtime_evidence)
    post.events = []
    baseline = runtime_evidence.last_probe_payload
    sequence, emitted = baseline['sequence'], baseline['emitted_at_ms']
    last_fresh = time.monotonic()
    last_sample = baseline
    observed_sample = baseline
    started = time.monotonic()
    overall_deadline = started + plan.to_dict()['timeout']
    request_path, response_path = probe_path.parent / REQUEST_FILE, probe_path.parent / RESPONSE_FILE
    report['evidence_paths'] = {'runtime_probe': str(probe_path.resolve()), 'response': str(response_path.resolve())}
    post_error = None
    abort = None
    current_entry = None
    control.emit('behavior_started', environment_index, checks=len(report['checks']))

    def sample():
        nonlocal sequence, emitted, last_fresh, last_sample, observed_sample
        drain_log()  # preserve raw logs; log strings never supply behavior assertions.
        if process.poll() is not None:
            raise ValueError('server process exited during behavior verification')
        payload = read_probe_evidence(probe_path)
        if payload:
            observed_sample = payload
            if payload['run_id'] != run_id or payload['sequence'] < sequence or payload['emitted_at_ms'] < emitted:
                raise ValueError('post-behavior runtime sample correlation/sequence mismatch')
            if payload['sequence'] == sequence:
                if payload != last_sample:
                    raise ValueError('runtime sample changed without advancing sequence')
            else:
                if (payload['emitted_at_ms'] <= emitted or
                        abs(time.time() * 1000 - payload['emitted_at_ms']) > PROBE_FRESHNESS_SECONDS * 1000):
                    raise ValueError('post-behavior runtime timestamp invalid')
                post.observe_probe(payload, time.monotonic() - started)
                if post.direct_runtime_error or post.plugin_disabled or not post.direct_plugin_enabled:
                    raise ValueError(post.direct_runtime_error or 'target disabled or absent during behavior verification')
                sequence, emitted = payload['sequence'], payload['emitted_at_ms']
                last_fresh, last_sample = time.monotonic(), payload
        return payload

    try:
        for index, (check, entry) in enumerate(zip(plan.to_dict()['checks'], report['checks'])):
            current_entry = entry
            control.check()
            if time.monotonic() >= overall_deadline:
                raise TimeoutError('behavior total timeout')
            entry.update(status='ERROR', reason=None)
            request = {'request_id': uuid.uuid4().hex, 'index': index}
            wall = time.time() * 1000
            check_start = time.monotonic()
            deadline = min(overall_deadline, check_start + check['timeout'])
            minimum_sequence = sequence
            entry['evidence'] = {'request': request, 'started_at_ms': int(wall), 'start_sequence': sequence}
            control.emit('behavior_check_started', environment_index, check_id=check['id'], check_type=check['type'])
            control.check()
            if check['type'] != 'wait':
                # Sequential requests and exactly-once probe consumption. No retry of a command.
                reject_links(response_path)
                response_path.unlink(missing_ok=True)
                atomic_text(request_path, f"request_id={request['request_id']}\nindex={index}\n")
            while True:
                control.check()
                now = time.monotonic()
                if now >= deadline:
                    raise TimeoutError('behavior check timeout')
                sample()
                if check['type'] == 'wait':
                    if now >= check_start + check['seconds'] and sequence > minimum_sequence and last_fresh >= check_start + check['seconds']:
                        entry['evidence']['observed_seconds'] = now - check_start
                        entry.update(status='PASS', reason=None)
                        break
                else:
                    response = _read_response(response_path)
                    if response is not None:
                        entry['evidence']['response'] = response
                        status, reason = validate_response(response, request=request, check=check, plan=plan,
                                                           run_id=run_id, started_wall=wall, target=post.plugin_name)
                        entry.update(status=status, reason=reason)
                        # A NEW runtime sample after command completion, not the pre-call snapshot.
                        minimum_sequence = sequence
                        break
                if now - last_fresh > PROBE_FRESHNESS_SECONDS and check['type'] != 'console_command':
                    raise TimeoutError('runtime probe stopped producing fresh evidence during behavior')
                time.sleep(.05)
            # Barrier for every check, including exceptions and unsupported observations.
            barrier_wall = time.time() * 1000
            while True:
                control.check()
                if time.monotonic() >= deadline:
                    raise TimeoutError('post-check health confirmation timeout')
                sample()
                if sequence > minimum_sequence and emitted >= barrier_wall:
                    break
                time.sleep(.05)
            entry['evidence'].update(final_sample=last_sample, process_alive=True,
                                     duration_seconds=round(time.monotonic() - check_start, 3))
            control.emit('behavior_check_completed', environment_index, check_id=check['id'], verdict=entry['status'])
        control.check()
        report['post_health'] = {'status': 'PASS', 'sample': last_sample, 'process_alive': process.poll() is None}
        if not report['post_health']['process_alive']:
            raise ValueError('server exited after final behavior sample')
    except (RunCancelled, KeyboardInterrupt):
        control.cancel()
        abort, post_error = 'CANCELLED', 'behavior verification cancelled'
    except TimeoutError as exc:
        abort, post_error = 'TIMEOUT', str(exc)
    except Exception as exc:
        abort, post_error = 'ERROR', f'{type(exc).__name__}: {exc}'
    finally:
        try:
            reject_links(request_path)
            request_path.unlink(missing_ok=True)
        except (OSError, ValueError) as exc:
            abort, post_error = 'ERROR', f'could not disarm behavior request: {exc}'
        if abort:
            if current_entry:
                current_entry.update(status=abort, reason=post_error)
                current_entry['evidence'].update(last_sample=last_sample, process_alive=process.poll() is None)
            report['post_health'] = {'status': abort, 'reason': post_error, 'last_sample': last_sample,
                                     'observed_sample': observed_sample,
                                     'process_alive': process.poll() is None}
        report['duration_seconds'] = round(time.monotonic() - started, 3)
    statuses = {entry['status'] for entry in report['checks']}
    report['verdict'] = abort or next((status for status in ('ERROR', 'TIMEOUT', 'FAIL', 'UNSUPPORTED', 'SKIPPED') if status in statuses), 'PASS')
    report['reason'] = post_error
    if report['reason'] is None and report['verdict'] != 'PASS':
        report['reason'] = next((entry['reason'] for entry in report['checks'] if entry['status'] != 'PASS'), None)
    control.emit('behavior_completed', environment_index, verdict=report['verdict'])
    return report
