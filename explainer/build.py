"""Refresh the explainer's flight map data from a recorded run.

    python3 explainer/build.py                       # default: runs/s5-live-owner
    python3 explainer/build.py runs/<another-run>    # any search run with mission.jsonl, scene.json, score.json

Writes explainer/data/flight.json and injects the same JSON into index.html between the
<script type="application/json" id="flight-data"> tags, so the page works when opened as a
local file (browsers block fetch() from file://). Standard library only; reads run files, calls no model.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
KEEP = ('type', 't', 'id', 'clue', 'g', 'conf', 'h', 'verdict', 'noul', 'reason', 'proposed',
        'applied', 'state', 'spot', 'alert', 'check')


def r(v, n=1):
    return round(v, n)


def extract(run: Path) -> dict:
    ev = [json.loads(line) for line in open(run / 'mission.jsonl')]
    start = next(e for e in ev if e['type'] == 'start')
    summ = next(e for e in ev if e['type'] == 'summary')
    scene = json.load(open(run / 'scene.json'))
    score = json.load(open(run / 'score.json'))
    spec, cfg = start['spec'], start['config']

    # Track: one point every 1.5 s of sim time, plus every state change.
    track, last, last_t = [], None, -9.0
    for e in ev:
        if e['type'] != 'tick':
            continue
        tel, st = e['tel'], e['state']
        if st != last or e['t'] - last_t >= 1.5:
            track.append([r(e['t']), r(tel['x']), r(tel['y']), r(tel['z']), st,
                          r(e.get('battery', 0)), r(e.get('coverage', 0), 3)])
            last, last_t = st, e['t']

    events = []
    for e in ev:
        if e['type'] not in ('investigate', 'confirm', 'dismiss', 'alert', 'note', 'plan', 'state'):
            continue
        out = {k: v for k, v in e.items() if k in KEEP}
        if e['type'] == 'investigate':
            s = e['spot']
            out.update(id=s['id'], g=[r(s['g'][0], 2), r(s['g'][1], 2)], clue=s['clue'],
                       noul=s['noul'], p_inv=s['p_inv'])
        events.append(out)

    return {
        'run': str(run.relative_to(PROJECT)) if run.is_relative_to(PROJECT) else str(run),
        'seed': spec['seed'], 'terrain': spec['terrain'],
        'area': cfg['area'], 'home': start['home'], 'lkp': spec['map']['lkp'],
        'trail': [[r(x), r(y)] for x, y in spec['map']['trail']],
        'stream': [[r(x), r(y)] for x, y in spec['map']['stream']],
        'trees': [[r(t['x']), r(t['y']), r(t['h'])] for t in scene.get('trees', [])],
        'lanes': start['lanes'],
        'sectors': [{k: (r(v, 2) if isinstance(v, float) else v) for k, v in s.items()} for s in start['sectors']],
        'sweep_h': start['sweep_h'], 'clues': start['clues'],
        'items': [{'name': i['name'], 'role': i['role'], 'xy': i['xy']} for i in score['items']],
        'track': track, 'events': events,
        'summary': {k: summ.get(k) for k in ('sim_s', 'wall_s', 'battery_used_pct', 'sweep_h', 'lanes', 'coverage',
                                              'area_m2_covered', 'frames', 'candidates', 'clef_sweep', 'clef_confirm',
                                              'fallback', 'investigations', 'dismissed', 'mean_investigate_s',
                                              'llm_calls', 'llm_by_role', 'time_to_first_alert', 'return_reason')},
        'score': {k: score.get(k) for k in ('recall', 'found', 'clues', 'false_alerts', 'decoys_investigated',
                                             'loc_err_m', 'time_to_first_find')},
    }


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / 'runs' / 's5-live-owner'
    if not run.is_absolute():
        run = (Path.cwd() / run).resolve()
    data = extract(run)
    blob = json.dumps(data, separators=(',', ':'))
    (HERE / 'data').mkdir(exist_ok=True)
    (HERE / 'data' / 'flight.json').write_text(blob)
    page = HERE / 'index.html'
    html = page.read_text()
    pat = re.compile(r'(<script type="application/json" id="flight-data">)(.*?)(</script>)', re.S)
    if not pat.search(html):
        sys.exit('index.html has no flight-data block')
    html = pat.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)
    sys.path.insert(0, str(HERE))
    import figures
    for name, fn in figures.FIGURES.items():
        fpat = re.compile(r'(<!-- FIG:%s -->)(.*?)(<!-- /FIG:%s -->)' % (name, name), re.S)
        if fpat.search(html):
            svg = fn()
            html = fpat.sub(lambda m: m.group(1) + svg + m.group(3), html, count=1)
        else:
            print(f'note: no marker for figure {name}')
    page.write_text(html)
    print(f"{data['run']}: {len(data['track'])} track points, {len(data['events'])} events, {len(blob) // 1024} KB")


if __name__ == '__main__':
    main()
