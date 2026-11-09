#!/usr/bin/env python3
"""Builds the summary tables from the raw files in results/. Reads only; never edits raw data."""
import csv, glob, os, re, statistics as st, sys
from collections import defaultdict

BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/hybrid-bench/results')
RUNS = [1, 2, 3, 4, 5]
CLIENTS = [1, 10, 50]
SIZES = [10240, 1048576, 10485760]
HEAD = ['table', 'group', 'metric', 'unit', 'n', 'mean', 'sd', 'median', 'p95', 'min', 'max']
rows = []


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def fail(msg):
    sys.exit('STOPPED: ' + msg)


def add(table, group, metric, unit, values, p95=False):
    v = sorted(values)
    pct = st.quantiles(v, n=20, method='inclusive')[18] if p95 else ''
    rows.append([table, group, metric, unit, len(v), round(st.mean(v), 4), round(st.stdev(v), 4),
                 round(st.median(v), 4), round(pct, 4) if p95 else '', v[0], v[-1]])
    return st.mean(v), st.stdev(v)


# ---- Caliper: the final results table in each run's log ----
PAT = re.compile(r'^\|\s*((?:register|access|audit)-\d+tps)\s*\|' + r'\s*([\d.]+)\s*\|' * 7 + r'\s*$')
FIELDS = ['succ', 'fail', 'send', 'max_s', 'min_s', 'avg_s', 'tput']
runs = {}
for r in RUNS:
    text = read(f'{BASE}/caliper/caliper-run{r}.log')
    found = {}
    for line in text.splitlines():
        m = PAT.match(line.rstrip())
        if m:
            found[m.group(1)] = dict(zip(FIELDS, map(float, m.groups()[1:])))
    if len(found) != 8:
        fail(f'run {r}: expected 8 rounds, found {len(found)}')
    runs[r] = found
    print(f'caliper run {r}: MVCC_READ_CONFLICT count = {text.count("MVCC_READ_CONFLICT")}')

print('\nCALIPER (5 runs; latency is Caliper\'s per-round average and max)')
print('round            send   tput mean+-sd    tput/send  success%  avg s mean+-sd  max s mean  runs meeting criterion')
labels = list(runs[1])
passes_all, passes_mean = {}, {}
for label in labels:
    per = [runs[r][label] for r in RUNS]
    send, _ = add('caliper', label, 'send_rate', 'tps', [p['send'] for p in per])
    tput, tput_sd = add('caliper', label, 'throughput', 'tps', [p['tput'] for p in per])
    avg, avg_sd = add('caliper', label, 'latency_avg', 's', [p['avg_s'] for p in per])
    mx, _ = add('caliper', label, 'latency_max', 's', [p['max_s'] for p in per])
    add('caliper', label, 'latency_min', 's', [p['min_s'] for p in per])
    add('caliper', label, 'succeeded', 'tx', [p['succ'] for p in per])
    add('caliper', label, 'failed', 'tx', [p['fail'] for p in per])
    succ = [100 * p['succ'] / (p['succ'] + p['fail']) for p in per]
    ratio = [100 * p['tput'] / p['send'] for p in per]
    add('caliper', label, 'success_rate', 'percent', succ)
    add('caliper', label, 'throughput_over_send', 'percent', ratio)
    ok = [1 if s >= 99 and q >= 95 else 0 for s, q in zip(succ, ratio)]
    add('caliper', label, 'meets_criterion', '0_or_1', ok)
    mean_ratio = 100 * tput / send
    passes_all[label] = sum(ok) == 5
    passes_mean[label] = st.mean(succ) >= 99 and mean_ratio >= 95
    print(f'{label:16} {send:5.1f}  {tput:7.2f} +- {tput_sd:5.2f}  {mean_ratio:7.2f}%  {st.mean(succ):7.2f}  '
          f'{avg:7.3f} +- {avg_sd:6.3f}  {mx:9.3f}  {sum(ok)} of 5')

reg = sorted((l for l in labels if l.startswith('register')), key=lambda l: int(re.search(r'\d+', l).group()))
print('highest register rate passing in all 5 runs :', ([l for l in reg if passes_all[l]] or ['none'])[-1])
print('highest register rate passing on the mean   :', ([l for l in reg if passes_mean[l]] or ['none'])[-1])

# ---- pgbench ----
print('\nPGBENCH (5 runs per client count)')
print('clients   tps mean+-sd          latency ms mean+-sd   failed tx total')
for c in CLIENTS:
    tps, lat, failed = [], [], []
    for r in RUNS:
        t = read(f'{BASE}/pgbench/pgbench-c{c}-run{r}.txt')
        try:
            tps.append(float(re.search(r'^tps = ([\d.]+)', t, re.M).group(1)))
            lat.append(float(re.search(r'latency average = ([\d.]+) ms', t).group(1)))
            failed.append(float(re.search(r'failed transactions: (\d+)', t).group(1)))
        except AttributeError:
            fail(f'could not read pgbench-c{c}-run{r}.txt')
    a, b = add('pgbench', f'c{c}', 'tps', 'tps', tps)
    d, e = add('pgbench', f'c{c}', 'latency_avg', 'ms', lat)
    add('pgbench', f'c{c}', 'failed', 'tx', failed)
    print(f'{c:7}   {a:10.2f} +- {b:7.2f}   {d:7.3f} +- {e:6.3f}   {int(sum(failed))}')

# ---- End-to-end ----
print('\nE2E (single client; 200 registrations per size; times in ms)')
print('mode      size_bytes  n    offchain_median  ledger_median  ledger_p95  ledger_max  total_median  total_p95')
medians = {}
for mode in ['fabric', 'postgres']:
    files = glob.glob(f'{BASE}/e2e/e2e-{mode}-*.csv')
    if len(files) != 1:
        fail(f'expected one {mode} CSV, found {len(files)}')
    with open(files[0], newline='') as f:
        data = list(csv.DictReader(f))
    for size in SIZES:
        part = [d for d in data if int(d['size_bytes']) == size]
        col = {k: sorted(float(d[k]) for d in part) for k in ['hash_ms', 'offchain_ms', 'ledger_ms', 'total_ms']}
        for k, v in col.items():
            add('e2e', f'{mode}-{size}', k, 'ms', v, p95=True)
        p95 = lambda v: st.quantiles(v, n=20, method='inclusive')[18]
        medians[mode, size] = (st.median(col['offchain_ms']), st.median(col['ledger_ms']))
        print(f'{mode:9} {size:10}  {len(part):3}  {medians[mode, size][0]:15.3f}  {medians[mode, size][1]:13.3f}  '
              f'{p95(col["ledger_ms"]):10.3f}  {col["ledger_ms"][-1]:10.3f}  {st.median(col["total_ms"]):12.3f}  {p95(col["total_ms"]):9.3f}')
for mode in ['fabric', 'postgres']:
    a, b = medians[mode, SIZES[0]], medians[mode, SIZES[-1]]
    print(f'{mode}: median at 10 MB divided by median at 10 KB -> offchain {b[0] / a[0]:.2f}x, ledger {b[1] / a[1]:.2f}x')

# ---- docker stats, pooled over all five Caliper runs ----
UNITS = {'B': 1 / 1048576, 'KiB': 1 / 1024, 'MiB': 1, 'GiB': 1024}
cpu, mem = defaultdict(list), defaultdict(list)
for r in RUNS:
    for line in read(f'{BASE}/caliper/docker-stats-run{r}.txt').splitlines():
        p = line.split(',')
        m = re.match(r'([\d.]+)(B|KiB|MiB|GiB) /', p[3]) if len(p) >= 4 else None
        if not m or not p[2].endswith('%'):
            continue
        name = re.sub(r'dev-peer0\.org(\d)\.example\.com-hybrid.*', r'chaincode-org\1', p[1])
        cpu[name].append(float(p[2][:-1]))
        mem[name].append(float(m.group(1)) * UNITS[m.group(2)])
print('\nDOCKER STATS (5 s samples over all 5 Caliper runs; 100% CPU = one logical CPU)')
print('container                 samples  cpu_median  cpu_max  mem_median_MiB  mem_max_MiB')
for name in sorted(cpu):
    add('docker_stats', name, 'cpu', 'percent_of_one_cpu', cpu[name], p95=True)
    add('docker_stats', name, 'memory', 'MiB', mem[name], p95=True)
    print(f'{name:25} {len(cpu[name]):7}  {st.median(cpu[name]):10.2f}  {max(cpu[name]):7.2f}  '
          f'{st.median(mem[name]):14.1f}  {max(mem[name]):11.1f}')

os.makedirs(f'{BASE}/analysis', exist_ok=True)
with open(f'{BASE}/analysis/summary-tables.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(HEAD)
    w.writerows(rows)
print(f'\nWrote {len(rows)} rows to {BASE}/analysis/summary-tables.csv')
