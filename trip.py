"""
trip.py - "which card wins on my trip?" Point it at your home currency and the
currency you'll spend in, and it tells you which network (Visa or Mastercard)
gives the better rate right now, and by how much.

Usage:
    uv run trip.py --home INR --spend EUR
    uv run trip.py --home INR --spend USD --amount 2500

It fetches today's live rate from both networks (no cookies, no keys). If you
have already archived a year for that pair (data/<HOME>/<SPEND>.csv, via
archive.py), it also prints the one-year track record: who wins more often, the
average gap, the best and worst days, and this week / month / year.
"""
import argparse
import csv
import os
import statistics as st
from datetime import datetime, timedelta

import bestrates as br

BAR = "=" * 68


def money(x, code):
    return f"{code} {x:,.2f}"


def live_verdict(home, spend, amount):
    s = br.session()
    print(f"Fetching today's {spend} rate for a {home} card ...")
    date, v, m = br.latest_traveller(s, home, spend, amount)
    if not date:
        print("Could not get a live rate for that pair from both networks.")
        print("Check the currency codes (must be ones both calculators support).")
        return None

    vr, mr = v["rate"], m["rate"]
    vbill, mbill = vr * amount, mr * amount
    cheaper = "Mastercard" if mr < vr else ("Visa" if vr < mr else "Tie")
    gap_abs = abs(vbill - mbill)
    gap_pct = abs(vr - mr) / max(vr, mr) * 100
    bench = v.get("benchmark")

    print()
    print(BAR)
    print(f"  {spend} on a {home} card   (rate as of {date}, latest available)")
    print(BAR)
    print(f"  You spend abroad : {spend} {amount:,.0f}")
    print(f"  {'Network':<12}{'rate (' + home + '/' + spend + ')':>20}{'you are billed':>22}")
    print(f"  {'-'*54}")
    print(f"  {'Visa':<12}{vr:>20.4f}{money(vbill, home):>22}")
    print(f"  {'Mastercard':<12}{mr:>20.4f}{money(mbill, home):>22}")
    if bench:
        print(f"  {'ECB mid':<12}{bench:>20.4f}{money(bench*amount, home):>22}")
    print(f"  {'-'*54}")
    if cheaper == "Tie":
        print(f"  Verdict: identical rate today.")
    else:
        print(f"  Verdict: {cheaper} is cheaper today by {money(gap_abs, home)} "
              f"({gap_pct:.3f}%).")
        if bench:
            vmk = (vr / bench - 1) * 100
            mmk = (mr / bench - 1) * 100
            print(f"  Markup over ECB mid: Visa {vmk:+.3f}%   Mastercard {mmk:+.3f}%")
    return date


def load_archive(home, spend):
    path = os.path.join("data", home, f"{spend}.csv")
    if not os.path.exists(path):
        return None
    rows = []
    for r in csv.DictReader(open(path)):
        if not r["visa_rate"] or not r["mc_rate"]:
            continue
        rows.append({"d": datetime.strptime(r["date"], "%Y-%m-%d"),
                     "visa": float(r["visa_rate"]), "mc": float(r["mc_rate"])})
    rows.sort(key=lambda x: x["d"])
    return rows or None


def window(rows, days):
    cutoff = rows[-1]["d"] - timedelta(days=days - 1)
    return [r for r in rows if r["d"] >= cutoff]


def advs(rows):
    # % Mastercard is cheaper than Visa (positive = Mastercard cheaper)
    return [(r["visa"] - r["mc"]) / r["visa"] * 100 for r in rows]


def verdict_line(rows):
    a = advs(rows)
    mc = sum(1 for x in a if x > 0)
    vi = sum(1 for x in a if x < 0)
    mean = st.mean(a)
    who = "Mastercard" if mean > 0 else ("Visa" if mean < 0 else "Tie")
    return (f"{who} cheaper on avg by {abs(mean):.3f}%   "
            f"(MC won {mc}/{len(a)}, Visa {vi}/{len(a)})")


def archive_report(home, spend):
    rows = load_archive(home, spend)
    if not rows:
        print()
        print(f"  Tip: archive a full year for the deep report:")
        print(f"       uv run archive.py --home {home} --spend {spend}")
        return
    a = advs(rows)
    best = max(range(len(a)), key=lambda i: a[i])   # most Mastercard-favourable
    worst = min(range(len(a)), key=lambda i: a[i])  # most Visa-favourable
    print()
    print(BAR)
    print(f"  One-year track record   [{rows[0]['d'].date()} -> {rows[-1]['d'].date()}, "
          f"{len(rows)} days]")
    print(BAR)
    for label, days in [("This week ", 7), ("This month", 30), ("This year ", 365)]:
        sub = window(rows, days)
        print(f"  {label}: {verdict_line(sub)}")
    print(f"  {'-'*60}")
    print(f"  Best day for Mastercard: {rows[best]['d'].date()}  "
          f"(MC {a[best]:+.3f}% vs Visa)")
    print(f"  Best day for Visa:       {rows[worst]['d'].date()}  "
          f"(MC {a[worst]:+.3f}% vs Visa)")


def main():
    ap = argparse.ArgumentParser(description="Which card wins on your trip?")
    ap.add_argument("--home", required=True, help="your card's home currency, e.g. INR")
    ap.add_argument("--spend", required=True, help="the currency you'll spend, e.g. EUR")
    ap.add_argument("--amount", type=float, default=1000, help="example amount you'll spend")
    args = ap.parse_args()
    home, spend = args.home.upper(), args.spend.upper()

    live_verdict(home, spend, args.amount)
    archive_report(home, spend)
    print()


if __name__ == "__main__":
    main()
