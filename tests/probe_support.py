"""A real subprocess writes snapshots using the current wire protocol."""
import textwrap


def probe_writer(path='probe.json', **overrides):
    payload = dict(probe='pluginmatrix', schema=2, run_id='', target_present=True,
                   target_enabled=True, target_name='Example', target_version='1.0',
                   target_main='example.Main', target_source='', target_ever_disabled=False)
    payload.update(overrides)
    return textwrap.dedent(f'''
        import json, pathlib, threading, time, os
        def emit_probe():
            payload = {payload!r}
            sequence = 0
            while True:
                sequence += 1
                payload.update(sequence=sequence, emitted_at_ms=int(time.time()*1000))
                temporary = pathlib.Path({(path+'.tmp')!r})
                temporary.write_text(json.dumps(payload), encoding='utf-8')
                try:
                    os.replace(temporary, {path!r})
                except PermissionError:
                    pass
                time.sleep(.025)
        threading.Thread(target=emit_probe, daemon=True).start()
    ''')


def one_probe(**overrides):
    payload = dict(probe='pluginmatrix', schema=2, run_id='', target_present=True,
                   target_enabled=True, target_name='Example', target_version='1.0',
                   target_main='example.Main', target_source='', target_ever_disabled=False,
                   sequence=1)
    payload.update(overrides)
    return f"import json,time,pathlib; p={payload!r}; p['emitted_at_ms']=int(time.time()*1000); pathlib.Path('probe.json').write_text(json.dumps(p)); "
