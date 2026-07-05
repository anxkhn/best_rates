"""
eda.py - India case-study charts + summary.json (origin INR, spending USD/EUR).

Reads the archived datasets in data/INR/USD.csv and data/INR/EUR.csv and draws
the direction-correct charts used in the README, plus writes summary.json.

Every chart uses the REAL data for its direction (nothing is inverted):
  traveller / reverse -> visa_rate / mc_rate    (INR per 1 foreign unit; lower better)
  forward             -> visa_fwd / mc_fwd      (foreign per 1 INR; a foreign card in India)

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
CURRENCIES = ["USD", "EUR"]


def load(cur):
    rows = []
    for r in csv.DictReader(open(f"data/INR/{cur}.csv")):
        if not r["visa_rate"] or not r["mc_rate"]:
            continue
        rows.append({
            "date": r["date"], "d": datetime.strptime(r["date"], "%Y-%m-%d"),
            "visa": float(r["visa_rate"]), "mc": float(r["mc_rate"]),
            "bench": float(r["visa_benchmark"]) if r["visa_benchmark"] else None,
            "visa_fwd": float(r["visa_fwd"]) if r["visa_fwd"] else None,
            "mc_fwd": float(r["mc_fwd"]) if r["mc_fwd"] else None,
        })
    rows.sort(key=lambda x: x["d"])
    return rows


def _dates(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))


def gap_chart(rows, advs, title, path):
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
    fig.savefig(path)
    plt.close(fig)


def main():
    summary = {}
    winrate = {}
    for cur in CURRENCIES:
        rows = load(cur)
        rev_adv = [(r["visa"] - r["mc"]) / r["visa"] * 100 for r in rows]
        fwd_rows = [r for r in rows if r["visa_fwd"] and r["mc_fwd"]]
        fwd_adv = [(r["visa_fwd"] - r["mc_fwd"]) / r["visa_fwd"] * 100 for r in fwd_rows]

        # 1) traveller rate trend (INR per 1 unit foreign)
        fig, ax = plt.subplots(figsize=(11, 4.6))
        ax.plot([r["d"] for r in rows], [r["visa"] for r in rows], color=VISA, lw=2, label="Visa")
        ax.plot([r["d"] for r in rows], [r["mc"] for r in rows], color=MC, lw=2, label="Mastercard")
        ax.set_title(f"{cur} to INR: rate billed to an INR card spent abroad (INR per 1 {cur})")
        ax.set_ylabel(f"INR per 1 {cur}")
        ax.legend(frameon=False, loc="upper left")
        _dates(ax)
        fig.savefig(f"charts/{cur}_01_rate.png")
        plt.close(fig)

        # 2) forward gap, 3) reverse gap
        gap_chart(fwd_rows, fwd_adv,
                  f"{cur} FORWARD: foreign card spent in India (billed {cur})",
                  f"charts/{cur}_02_forward_gap.png")
        gap_chart(rows, rev_adv,
                  f"{cur} REVERSE: INR card spent abroad (billed INR)",
                  f"charts/{cur}_03_reverse_gap.png")

        # 4) reverse reality check: naive 1/forward estimate vs real reverse
        dd, est, real = [], [], []
        for r in fwd_rows:
            dd.append(r["d"])
            inv_v, inv_m = 1.0 / r["visa_fwd"], 1.0 / r["mc_fwd"]
            est.append((inv_v - inv_m) / inv_v * 100)                 # MC adv, inverted estimate
            real.append((r["visa"] - r["mc"]) / r["visa"] * 100)      # MC adv, real reverse
        fig, ax = plt.subplots(figsize=(11, 4.3))
        ax.plot(dd, est, color=MC2, lw=1.5, label=f"naive 1/forward estimate (mean {st.mean(est):+.3f}%)")
        ax.plot(dd, real, color=VISA, lw=1.7, label=f"REAL reverse query (mean {st.mean(real):+.3f}%)")
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_title(f"{cur}: why you cannot invert the forward rate (MC advantage, reverse)")
        ax.set_ylabel("Mastercard advantage (%)")
        ax.legend(frameon=False, loc="upper left")
        _dates(ax)
        fig.savefig(f"charts/{cur}_04_reverse_check.png")
        plt.close(fig)

        # markup over ECB mid (traveller direction)
        vmk = [(r["visa"] / r["bench"] - 1) * 100 for r in rows if r["bench"]]
        mmk = [(r["mc"] / r["bench"] - 1) * 100 for r in rows if r["bench"]]

        winrate[cur] = {
            "fwd_mc": sum(1 for a in fwd_adv if a > 0), "fwd_visa": sum(1 for a in fwd_adv if a < 0),
            "rev_mc": sum(1 for a in rev_adv if a > 0), "rev_visa": sum(1 for a in rev_adv if a < 0),
        }
        summary[cur] = {
            "days": len(rows), "window": f"{rows[0]['date']} to {rows[-1]['date']}",
            "traveller_mc_win_pct": round(winrate[cur]["rev_mc"] / len(rows) * 100, 1),
            "traveller_mc_adv_mean_pct": round(st.mean(rev_adv), 4),
            "traveller_mc_adv_min_pct": round(min(rev_adv), 4),
            "traveller_mc_adv_max_pct": round(max(rev_adv), 4),
            "traveller_avg_visa_inr": round(st.mean([r["visa"] for r in rows]), 4),
            "traveller_avg_mc_inr": round(st.mean([r["mc"] for r in rows]), 4),
            "markup_vs_ecb_visa_pct": round(st.mean(vmk), 4),
            "markup_vs_ecb_mc_pct": round(st.mean(mmk), 4),
            "forward_mc_win_pct": round(winrate[cur]["fwd_mc"] / len(fwd_rows) * 100, 1),
            "forward_mc_adv_mean_pct": round(st.mean(fwd_adv), 4),
        }

    # summary grouped bars (traveller + forward)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    groups = []
    for cur in CURRENCIES:
        groups.append((f"{cur}\ntraveller", winrate[cur]["rev_visa"], winrate[cur]["rev_mc"]))
        groups.append((f"{cur}\nforward", winrate[cur]["fwd_visa"], winrate[cur]["fwd_mc"]))
    labels = [g[0] for g in groups]
    v = [g[1] for g in groups]
    m = [g[2] for g in groups]
    x = range(len(groups))
    ax.bar([i - 0.2 for i in x], v, 0.4, color=VISA, label="Visa cheaper")
    ax.bar([i + 0.2 for i in x], m, 0.4, color=MC, label="Mastercard cheaper")
    for i, (vv, mm) in enumerate(zip(v, m)):
        ax.text(i - 0.2, vv + 4, str(vv), ha="center", fontweight="bold", fontsize=9)
        ax.text(i + 0.2, mm + 4, str(mm), ha="center", fontweight="bold", fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 365 * 0.85)
    ax.set_title("Days won by each network (of 365)")
    ax.set_ylabel("days won")
    ax.legend(frameon=False, loc="upper center", ncol=2)
    fig.savefig("charts/00_winrate.png")
    plt.close(fig)

    with open("summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    print("charts written to charts/ ; summary.json:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
