"""
Exploratory Data Analysis + chart generation for Visa vs Mastercard
INR conversion rates. Reads rates.csv, writes charts to charts/ and a
machine-readable summary to summary.json.
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

CHART_DIR = "charts"
os.makedirs(CHART_DIR, exist_ok=True)

# ---- theme -----------------------------------------------------------------
VISA = "#1a1f71"      # Visa blue
MC = "#eb001b"        # Mastercard red
MC2 = "#f79e1b"       # Mastercard orange (accent)
BENCH = "#6b7280"     # grey
BG = "#ffffff"
GRID = "#e5e7eb"
INK = "#111827"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "figure.dpi": 130,
    "savefig.bbox": "tight",
    "savefig.facecolor": BG,
})


def f(x):
    return float(x) if x not in (None, "") else None


def load(pair):
    rows = []
    with open("rates.csv") as fh:
        for r in csv.DictReader(fh):
            if r["pair"] != pair:
                continue
            r = dict(r)
            r["d"] = datetime.strptime(r["date"], "%Y-%m-%d")
            for k in ("visa_fx_per_inr", "mc_fx_per_inr", "visa_inr_per_unit",
                      "mc_inr_per_unit", "visa_benchmark", "visa_bill_amt",
                      "mc_bill_amt"):
                r[k] = f(r[k])
            r["gap_pct"] = (r["visa_fx_per_inr"] - r["mc_fx_per_inr"]) / r["mc_fx_per_inr"] * 100
            # savings for INR-card holder spending abroad (per 1 unit foreign)
            r["visa_saves_inr"] = r["mc_inr_per_unit"] - r["visa_inr_per_unit"]
            r["visa_saves_pct"] = r["visa_saves_inr"] / r["mc_inr_per_unit"] * 100
            r["v_markup"] = (r["visa_fx_per_inr"] - r["visa_benchmark"]) / r["visa_benchmark"] * 100
            r["m_markup"] = (r["mc_fx_per_inr"] - r["visa_benchmark"]) / r["visa_benchmark"] * 100
            rows.append(r)
    rows.sort(key=lambda x: x["d"])
    return rows


def _fmt_dates(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))
    for lb in ax.get_xticklabels():
        lb.set_rotation(0)


def chart_rates(pair, rows):
    cur = pair[:3]
    dates = [r["d"] for r in rows]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(dates, [r["visa_inr_per_unit"] for r in rows], color=VISA, lw=2, label="Visa")
    ax.plot(dates, [r["mc_inr_per_unit"] for r in rows], color=MC, lw=2, label="Mastercard")
    ax.set_title(f"{cur} to INR - daily rate you are billed (INR per 1 {cur})")
    ax.set_ylabel(f"INR per 1 {cur}")
    ax.legend(frameon=False, loc="upper left")
    _fmt_dates(ax)
    p = f"{CHART_DIR}/01_{cur}_rates.png"
    fig.savefig(p); plt.close(fig)
    return p


def chart_gap(pair, rows):
    cur = pair[:3]
    dates = [r["d"] for r in rows]
    gaps = [r["visa_saves_pct"] for r in rows]  # + => Visa cheaper for INR card abroad
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.fill_between(dates, gaps, 0, where=[g >= 0 for g in gaps], color=VISA, alpha=0.55, interpolate=True, label="Visa cheaper")
    ax.fill_between(dates, gaps, 0, where=[g < 0 for g in gaps], color=MC, alpha=0.55, interpolate=True, label="Mastercard cheaper")
    ax.axhline(0, color=INK, lw=0.8)
    ax.axhline(st.mean(gaps), color=MC2, lw=1.4, ls="--", label=f"mean {st.mean(gaps):+.3f}%")
    ax.set_title(f"{cur}: how much cheaper Visa is vs Mastercard (INR card spending abroad)")
    ax.set_ylabel("Visa advantage (%)")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    _fmt_dates(ax)
    p = f"{CHART_DIR}/02_{cur}_gap.png"
    fig.savefig(p); plt.close(fig)
    return p


def chart_hist(pair, rows):
    cur = pair[:3]
    gaps = [r["visa_saves_pct"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(gaps, bins=40, color=VISA, alpha=0.85, edgecolor="white")
    ax.axvline(0, color=INK, lw=1)
    ax.axvline(st.mean(gaps), color=MC, lw=1.6, ls="--", label=f"mean {st.mean(gaps):+.3f}%")
    ax.axvline(st.median(gaps), color=MC2, lw=1.6, ls=":", label=f"median {st.median(gaps):+.3f}%")
    ax.set_title(f"{cur}: distribution of daily Visa advantage")
    ax.set_xlabel("Visa cheaper by (%)  |  negative = Mastercard cheaper")
    ax.set_ylabel("days")
    ax.legend(frameon=False)
    p = f"{CHART_DIR}/03_{cur}_hist.png"
    fig.savefig(p); plt.close(fig)
    return p


def chart_markup(pair, rows):
    cur = pair[:3]
    dates = [r["d"] for r in rows]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(dates, [r["v_markup"] for r in rows], color=VISA, lw=1.6, label=f"Visa markup (avg {st.mean([r['v_markup'] for r in rows]):.3f}%)")
    ax.plot(dates, [r["m_markup"] for r in rows], color=MC, lw=1.6, label=f"Mastercard markup (avg {st.mean([r['m_markup'] for r in rows]):.3f}%)")
    ax.axhline(0, color=BENCH, lw=1, ls="--", label="ECB mid-market")
    ax.set_title(f"{cur}: network rate vs ECB mid-market (markup %)")
    ax.set_ylabel("markup over ECB mid (%)")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    _fmt_dates(ax)
    p = f"{CHART_DIR}/04_{cur}_markup.png"
    fig.savefig(p); plt.close(fig)
    return p


def chart_winrate(pairs_rows):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = list(pairs_rows.keys())
    visa = [sum(1 for r in rows if r["visa_saves_pct"] > 0) for rows in pairs_rows.values()]
    mc = [sum(1 for r in rows if r["visa_saves_pct"] < 0) for rows in pairs_rows.values()]
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], visa, width=0.4, color=VISA, label="Visa cheaper")
    ax.bar([i + 0.2 for i in x], mc, width=0.4, color=MC, label="Mastercard cheaper")
    for i, (v, m) in enumerate(zip(visa, mc)):
        ax.text(i - 0.2, v + 3, str(v), ha="center", fontweight="bold")
        ax.text(i + 0.2, m + 3, str(m), ha="center", fontweight="bold")
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_title("Who gives the better rate more often (days won, INR card abroad)")
    ax.set_ylabel("days won (of 365)")
    ax.set_ylim(0, max(visa + mc) * 1.18)
    ax.legend(frameon=False, loc="upper center", ncol=2)
    p = f"{CHART_DIR}/05_winrate.png"
    fig.savefig(p); plt.close(fig)
    return p


def chart_monthly(pairs_rows):
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for pair, rows in pairs_rows.items():
        cur = pair[:3]
        buckets = {}
        for r in rows:
            key = r["d"].strftime("%Y-%m")
            buckets.setdefault(key, []).append(r["visa_saves_pct"])
        keys = sorted(buckets)
        vals = [st.mean(buckets[k]) for k in keys]
        ax.plot(keys, vals, marker="o", lw=2,
                color=VISA if cur == "USD" else MC, label=cur)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_title("Monthly average Visa advantage (%)")
    ax.set_ylabel("Visa cheaper by (%)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False)
    p = f"{CHART_DIR}/06_monthly.png"
    fig.savefig(p); plt.close(fig)
    return p


def stats(pair, rows):
    gaps = [r["visa_saves_pct"] for r in rows]
    absg = [abs(r["gap_pct"]) for r in rows]
    return {
        "pair": pair,
        "days": len(rows),
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "visa_cheaper_days": sum(1 for g in gaps if g > 0),
        "mc_cheaper_days": sum(1 for g in gaps if g < 0),
        "visa_win_pct": round(sum(1 for g in gaps if g > 0) / len(gaps) * 100, 1),
        "mean_visa_adv_pct": round(st.mean(gaps), 4),
        "median_visa_adv_pct": round(st.median(gaps), 4),
        "best_day_visa_adv_pct": round(max(gaps), 4),
        "worst_day_visa_adv_pct": round(min(gaps), 4),
        "mean_abs_gap_pct": round(st.mean(absg), 4),
        "max_abs_gap_pct": round(max(absg), 4),
        "visa_mean_markup_pct": round(st.mean([r["v_markup"] for r in rows]), 4),
        "mc_mean_markup_pct": round(st.mean([r["m_markup"] for r in rows]), 4),
    }


def main():
    pairs = ["USD/INR", "EUR/INR"]
    pr = {p: load(p) for p in pairs}
    charts = []
    for p in pairs:
        charts += [chart_rates(p, pr[p]), chart_gap(p, pr[p]),
                   chart_hist(p, pr[p]), chart_markup(p, pr[p])]
    charts.append(chart_winrate(pr))
    charts.append(chart_monthly(pr))
    summary = {p: stats(p, pr[p]) for p in pairs}
    with open("summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    print("charts written:")
    for c in charts:
        print("  ", c)
    print("\nsummary.json:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
