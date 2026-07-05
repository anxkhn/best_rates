"""
compare.py - who gives the better card FX rate, this week / month / year?

Reads the tracked history in rates.csv and reports, for each currency pair,
which network (Visa or Mastercard) an Indian INR-card holder spending abroad
should prefer, and the average percentage difference.

Usage:
    uv run compare.py                # all windows, both pairs
    uv run compare.py --pair USD/INR # single pair
    uv run compare.py --window month # week | month | year
"""
import argparse
import csv
import statistics as st
from datetime import datetime, timedelta

WINDOWS = {"week": 7, "month": 30, "year": 365}


def load(pair):
    out = []
    with open("rates.csv") as fh:
        for r in csv.DictReader(fh):
            if r["pair"] != pair or not r["visa_inr_per_unit"]:
                continue
            out.append({
                "d": datetime.strptime(r["date"], "%Y-%m-%d"),
                "visa_inr": float(r["visa_inr_per_unit"]),
                "mc_inr": float(r["mc_inr_per_unit"]),
            })
    out.sort(key=lambda x: x["d"])
    return out


def window_report(pair, rows, days):
    last = rows[-1]["d"]
    cutoff = last - timedelta(days=days - 1)
    sub = [r for r in rows if r["d"] >= cutoff]
    if not sub:
        return None
    # INR paid per 1 unit foreign; lower is better for the traveller
    advs = [(r["mc_inr"] - r["visa_inr"]) / r["mc_inr"] * 100 for r in sub]
    visa_days = sum(1 for a in advs if a > 0)
    mc_days = sum(1 for a in advs if a < 0)
    mean_adv = st.mean(advs)
    winner = "Visa" if mean_adv > 0 else ("Mastercard" if mean_adv < 0 else "Tie")
    return {
        "pair": pair, "days": len(sub),
        "from": sub[0]["d"].date().isoformat(),
        "to": sub[-1]["d"].date().isoformat(),
        "winner": winner,
        "mean_visa_adv_pct": mean_adv,
        "visa_days": visa_days, "mc_days": mc_days,
        "visa_inr_latest": sub[-1]["visa_inr"], "mc_inr_latest": sub[-1]["mc_inr"],
    }


def fmt(cur, r):
    if not r:
        return f"  (no data)"
    sign = "cheaper" if r["mean_visa_adv_pct"] >= 0 else "pricier"
    verdict = r["winner"]
    adv = abs(r["mean_visa_adv_pct"])
    return (
        f"  Winner: {verdict:<10}  |  Visa avg {sign} by {adv:.3f}%\n"
        f"    days won: Visa {r['visa_days']} vs Mastercard {r['mc_days']} "
        f"(of {r['days']})  [{r['from']} -> {r['to']}]\n"
        f"    latest rate: Visa Rs {r['visa_inr_latest']:.4f}/{cur}  |  "
        f"Mastercard Rs {r['mc_inr_latest']:.4f}/{cur}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", choices=["USD/INR", "EUR/INR"], default=None)
    ap.add_argument("--window", choices=list(WINDOWS), default=None)
    args = ap.parse_args()

    pairs = [args.pair] if args.pair else ["USD/INR", "EUR/INR"]
    windows = [args.window] if args.window else list(WINDOWS)

    print("=" * 66)
    print("  Visa vs Mastercard - card FX for an INR card spent abroad")
    print("  (lower INR paid per 1 unit foreign = better)")
    print("=" * 66)
    for pair in pairs:
        rows = load(pair)
        cur = pair[:3]
        print(f"\n### {pair}")
        for w in windows:
            r = window_report(pair, rows, WINDOWS[w])
            print(f"\n  This {w} (last {WINDOWS[w]} days):")
            print(fmt(cur, r))
    print()


if __name__ == "__main__":
    main()
