"""
eda.py - direction-correct charts + summary.json for Visa vs Mastercard.

Uses REAL data for each direction (never inverts one to fake the other):
  forward  -> rates.csv          (foreign card spent in India, billed foreign)
  reverse  -> rates_reverse.csv  (INR card spent abroad, billed INR)

"MC advantage" = % by which Mastercard is cheaper than Visa that day
(positive = Mastercard cheaper).
"""
import csv
import json
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
PAIRS = ["USD/INR", "EUR/INR"]


def fnum(x):
    return float(x) if x not in (None, "") else None


def load(path, pair, cols):
    rows = []
    for r in csv.DictReader(open(path)):
        if r["pair"] != pair or any(r[c] in (None, "") for c in cols):
            continue
        rows.append({"date": r["date"], "d": datetime.strptime(r["date"], "%Y-%m-%d"),
                     **{c: fnum(r[c]) for c in cols}})
    rows.sort(key=lambda x: x["d"])
    return rows


def _dates(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))


def gap_chart(cur, rows, advs, title, path):
    dd = [r["d"] for r in rows]
    fig, ax = plt.subplots(figsize=(11, 4.3))
    ax.fill_between(dd, advs, 0, where=[a >= 0 for a in advs], color=MC, alpha=0.55,
                    interpolate=True, label="Mastercard cheaper")
    ax.fill_between(dd, advs, 0, where=[a < 0 for a in advs], color=VISA, alpha=0.55,
                    interpolate=True, label="Visa cheaper")
    ax.axhline(0, color=INK, lw=0.8)
    ax.axhline(st.mean(advs), color=MC2, lw=1.4, ls="--", label=f"mean {st.mean(advs):+.3f}%")
    ax.set_title(title)
    ax.set_ylabel("Mastercard advantage (%)")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    _dates(ax)
    fig.savefig(path); plt.close(fig)


def main():
    summary = {}
    winrate = {}
    for pair in PAIRS:
        cur = pair[:3]
        fwd = load("rates.csv", pair, ["visa_fx_per_inr", "mc_fx_per_inr"])
        rev = load("rates_reverse.csv", pair, ["visa_inr_per_unit", "mc_inr_per_unit"])
        fwd_adv = [(r["visa_fx_per_inr"] - r["mc_fx_per_inr"]) / r["visa_fx_per_inr"] * 100 for r in fwd]
        rev_adv = [(r["visa_inr_per_unit"] - r["mc_inr_per_unit"]) / r["visa_inr_per_unit"] * 100 for r in rev]

        # 1) rate trend (traveller view: INR per 1 unit foreign, real reverse data)
        fig, ax = plt.subplots(figsize=(11, 4.6))
        ax.plot([r["d"] for r in rev], [r["visa_inr_per_unit"] for r in rev], color=VISA, lw=2, label="Visa")
        ax.plot([r["d"] for r in rev], [r["mc_inr_per_unit"] for r in rev], color=MC, lw=2, label="Mastercard")
        ax.set_title(f"{cur} to INR: rate billed to an INR card spent abroad (INR per 1 {cur})")
        ax.set_ylabel(f"INR per 1 {cur}")
        ax.legend(frameon=False, loc="upper left")
        _dates(ax)
        fig.savefig(f"charts/{cur}_01_rate.png"); plt.close(fig)

        # 2) forward gap, 3) reverse gap
        gap_chart(cur, fwd, fwd_adv,
                  f"{cur} FORWARD: foreign card spent in India (billed {cur})",
                  f"charts/{cur}_02_forward_gap.png")
        gap_chart(cur, rev, rev_adv,
                  f"{cur} REVERSE: INR card spent abroad (billed INR)",
                  f"charts/{cur}_03_reverse_gap.png")

        # 4) reverse reality check: naive 1/forward estimate vs real reverse
        by_date = {r["date"]: r for r in fwd}
        dd, est, real = [], [], []
        for r in rev:
            fr = by_date.get(r["date"])
            if not fr:
                continue
            dd.append(r["d"])
            # Visa advantage in reverse: real vs the naive inverted-forward estimate
            inv_v, inv_m = 1.0 / fr["visa_fx_per_inr"], 1.0 / fr["mc_fx_per_inr"]
            est.append((inv_v - inv_m) / inv_v * 100)        # MC advantage, inverted estimate
            real.append((r["visa_inr_per_unit"] - r["mc_inr_per_unit"]) / r["visa_inr_per_unit"] * 100)
        fig, ax = plt.subplots(figsize=(11, 4.3))
        ax.plot(dd, est, color=MC2, lw=1.5, label=f"naive 1/forward estimate (mean {st.mean(est):+.3f}%)")
        ax.plot(dd, real, color=VISA, lw=1.7, label=f"REAL reverse query (mean {st.mean(real):+.3f}%)")
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_title(f"{cur}: why you cannot invert the forward rate (MC advantage, reverse)")
        ax.set_ylabel("Mastercard advantage (%)")
        ax.legend(frameon=False, loc="upper left")
        _dates(ax)
        fig.savefig(f"charts/{cur}_04_reverse_check.png"); plt.close(fig)

        winrate[pair] = {
            "fwd_mc": sum(1 for a in fwd_adv if a > 0), "fwd_visa": sum(1 for a in fwd_adv if a < 0),
            "rev_mc": sum(1 for a in rev_adv if a > 0), "rev_visa": sum(1 for a in rev_adv if a < 0),
        }
        summary[pair] = {
            "days": len(rev), "window": f"{rev[0]['date']} to {rev[-1]['date']}",
            "forward_mc_win_pct": round(winrate[pair]["fwd_mc"] / len(fwd) * 100, 1),
            "forward_mc_adv_mean_pct": round(st.mean(fwd_adv), 4),
            "reverse_mc_win_pct": round(winrate[pair]["rev_mc"] / len(rev) * 100, 1),
            "reverse_mc_adv_mean_pct": round(st.mean(rev_adv), 4),
            "reverse_mc_adv_min_pct": round(min(rev_adv), 4),
            "reverse_mc_adv_max_pct": round(max(rev_adv), 4),
        }

    # summary winrate grouped bars (forward + reverse)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    groups = []
    for pair in PAIRS:
        groups.append((f"{pair[:3]}\nforward", winrate[pair]["fwd_visa"], winrate[pair]["fwd_mc"]))
        groups.append((f"{pair[:3]}\nreverse", winrate[pair]["rev_visa"], winrate[pair]["rev_mc"]))
    labels = [g[0] for g in groups]
    v = [g[1] for g in groups]
    m = [g[2] for g in groups]
    x = range(len(groups))
    ax.bar([i - 0.2 for i in x], v, 0.4, color=VISA, label="Visa cheaper")
    ax.bar([i + 0.2 for i in x], m, 0.4, color=MC, label="Mastercard cheaper")
    for i, (vv, mm) in enumerate(zip(v, m)):
        ax.text(i - 0.2, vv + 4, str(vv), ha="center", fontweight="bold", fontsize=9)
        ax.text(i + 0.2, mm + 4, str(mm), ha="center", fontweight="bold", fontsize=9)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_ylim(0, 365 * 0.85)
    ax.set_title("Days won by each network, both directions (of 365)")
    ax.set_ylabel("days won")
    ax.legend(frameon=False, loc="upper center", ncol=2)
    fig.savefig("charts/00_winrate.png"); plt.close(fig)

    with open("summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    print("charts written to charts/ ; summary.json:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
