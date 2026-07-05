"""
eda_reverse.py - charts for the reverse-direction validation.
Shows that the naive 1/forward inversion misstates the reverse winner, and
compares the REAL reverse-direction win rates.
"""
import csv
import os
import statistics as st
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

os.makedirs("charts", exist_ok=True)
VISA, MC, MC2, INK, GRID, BG = "#1a1f71", "#eb001b", "#f79e1b", "#111827", "#e5e7eb", "#ffffff"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "axes.edgecolor": GRID,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "figure.dpi": 130, "savefig.bbox": "tight", "savefig.facecolor": BG,
})


def f(x):
    return float(x) if x not in (None, "") else None


def load(path, pair, cols):
    out = {}
    for r in csv.DictReader(open(path)):
        if r["pair"] == pair:
            out[r["date"]] = {k: f(r[k]) for k in cols}
    return out


def _dates(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))


rev_wins = {}
for pair in ["USD/INR", "EUR/INR"]:
    cur = pair[:3]
    fwd = load("rates.csv", pair, ["visa_inr_per_unit", "mc_inr_per_unit"])
    rev = load("rates_reverse.csv", pair, ["visa_inr_per_unit", "mc_inr_per_unit"])
    dates = sorted(set(fwd) & set(rev))
    dd = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
    real_adv = [(rev[d]["mc_inr_per_unit"] - rev[d]["visa_inr_per_unit"]) / rev[d]["mc_inr_per_unit"] * 100 for d in dates]
    inv_adv = [(fwd[d]["mc_inr_per_unit"] - fwd[d]["visa_inr_per_unit"]) / fwd[d]["mc_inr_per_unit"] * 100 for d in dates]
    rev_wins[pair] = (
        sum(1 for d in dates if rev[d]["visa_inr_per_unit"] < rev[d]["mc_inr_per_unit"]),
        sum(1 for d in dates if rev[d]["mc_inr_per_unit"] < rev[d]["visa_inr_per_unit"]),
    )

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(dd, inv_adv, color=MC2, lw=1.5, label=f"naive 1/forward estimate (mean {st.mean(inv_adv):+.3f}%)")
    ax.plot(dd, real_adv, color=VISA, lw=1.8, label=f"REAL reverse query (mean {st.mean(real_adv):+.3f}%)")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_title(f"{cur}: Visa advantage for an INR card spent abroad, estimate vs reality\n(above 0 = Visa cheaper)")
    ax.set_ylabel("Visa advantage (%)")
    ax.legend(frameon=False, loc="upper left")
    _dates(ax)
    p = f"charts/07_{cur}_reverse_check.png"
    fig.savefig(p); plt.close(fig)
    print("wrote", p)

# win-rate bars: real reverse direction
fig, ax = plt.subplots(figsize=(8, 4.5))
labels = list(rev_wins)
visa = [rev_wins[p][0] for p in labels]
mc = [rev_wins[p][1] for p in labels]
x = range(len(labels))
ax.bar([i - 0.2 for i in x], visa, 0.4, color=VISA, label="Visa cheaper")
ax.bar([i + 0.2 for i in x], mc, 0.4, color=MC, label="Mastercard cheaper")
for i, (v, m) in enumerate(zip(visa, mc)):
    ax.text(i - 0.2, v + 3, str(v), ha="center", fontweight="bold")
    ax.text(i + 0.2, m + 3, str(m), ha="center", fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(labels)
ax.set_ylim(0, 365 * 0.75)
ax.set_title("REAL reverse direction (INR card abroad): who is cheaper more often")
ax.set_ylabel("days won (of 365)")
ax.legend(frameon=False, loc="upper center", ncol=2)
fig.savefig("charts/08_reverse_winrate.png"); plt.close(fig)
print("wrote charts/08_reverse_winrate.png")
