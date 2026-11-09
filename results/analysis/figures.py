#!/usr/bin/env python3
"""Draws Figures 2 and 3 from results/analysis/summary-tables.csv. Every value comes from that file."""
import csv, os, re, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/hybrid-bench/results')
OUT = f'{BASE}/analysis'
with open(f'{OUT}/summary-tables.csv', newline='') as f:
    T = {(r['table'], r['group'], r['metric']): r for r in csv.DictReader(f)}


def val(table, group, metric, key='mean'):
    return float(T[table, group, metric][key])


BLUE, ORANGE, INK, MUTED, GRID = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.titlesize': 10, 'axes.titlecolor': INK,
                     'axes.axisbelow': True})


def save(fig, name):
    for ext in ('png', 'pdf'):
        fig.savefig(f'{OUT}/{name}.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
    print(f'saved {name}.png and {name}.pdf')


# ---- Figure 2: throughput and latency against send rate (register rounds, 5 runs) ----
labels = sorted({g for (t, g, m) in T if t == 'caliper' and g.startswith('register')},
                key=lambda g: int(re.search(r'\d+', g).group()))
send = [val('caliper', g, 'send_rate') for g in labels]
tput = [val('caliper', g, 'throughput') for g in labels]
tsd = [val('caliper', g, 'throughput', 'sd') for g in labels]
lat = [val('caliper', g, 'latency_avg') for g in labels]
lsd = [val('caliper', g, 'latency_avg', 'sd') for g in labels]
sustain = [s for g, s in zip(labels, send) if val('caliper', g, 'meets_criterion') == 1][-1]
print('Figure 2: send', send, 'throughput', tput, 'avg latency', lat, 'sustainable send rate', sustain)

fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3))
top = max(send) * 1.05
a.plot([0, top], [0, top], ls='--', lw=1, color=MUTED)
a.text(sustain - top * 0.03, top * 0.78, 'ideal line', ha='right', color=MUTED, fontsize=8)
a.errorbar(send, tput, yerr=tsd, color=BLUE, marker='o', ms=5, lw=2, capsize=3)
a.set(xlabel='Send rate (TPS)', ylabel='Throughput (TPS)', xlim=(0, top), ylim=(0, top), title='Throughput')
b.errorbar(send, lat, yerr=lsd, color=BLUE, marker='o', ms=5, lw=2, capsize=3)
b.set(xlabel='Send rate (TPS)', ylabel='Average latency (s)', xlim=(0, top), ylim=(0, None), title='Latency')
for ax in (a, b):
    ax.axvline(sustain, color=MUTED, lw=1, ls=':')
    ax.grid(axis='y', color=GRID, lw=0.8)
a.text(sustain + top * 0.02, top * 0.06, f'{sustain:.0f} TPS\nsustainable', color=MUTED, fontsize=8)
b.text(sustain - top * 0.02, max(lat) * 0.92, f'{sustain:.0f} TPS\nsustainable', color=MUTED, fontsize=8, ha='right')
fig.tight_layout()
save(fig, 'figure2-throughput-latency')

# ---- Figure 3: ledger against off-chain time by document size (medians, single client) ----
SIZES = [(10240, '10 KB'), (1048576, '1 MB'), (10485760, '10 MB')]
x = list(range(len(SIZES)))
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3), sharey=True)
for ax, (mode, title) in zip(axes, [('fabric', 'Fabric'), ('postgres', 'PostgreSQL')]):
    ledger = [val('e2e', f'{mode}-{s}', 'ledger_ms', 'median') for s, _ in SIZES]
    off = [val('e2e', f'{mode}-{s}', 'offchain_ms', 'median') for s, _ in SIZES]
    print(f'Figure 3: {mode} ledger', ledger, 'offchain', off)
    ax.plot(x, ledger, color=BLUE, marker='o', ms=5, lw=2, label='Ledger write')
    ax.plot(x, off, color=ORANGE, marker='s', ms=5, lw=2, ls='--', label='Off-chain upload (MinIO)')
    ax.text(2.1, ledger[-1], 'Ledger', va='center', color=INK, fontsize=8)
    ax.text(2.1, off[-1], 'Off-chain', va='center', color=INK, fontsize=8)
    ax.set_yscale('log')
    ax.set(xticks=x, xticklabels=[n for _, n in SIZES], xlim=(-0.2, 2.75), ylim=(0.5, 5000),
           xlabel='Document size', title=title)
    ax.grid(axis='y', color=GRID, lw=0.8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g}'))
axes[0].set_ylabel('Median time (ms, log scale)')
handles, names = axes[0].get_legend_handles_labels()
fig.tight_layout()
fig.legend(handles, names, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)
save(fig, 'figure3-ledger-offchain')
