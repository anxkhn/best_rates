"""
archive.py - download and archive the last ~365 days of card rates for one or
more currency pairs, so you can compare a whole year offline.

The Visa and Mastercard calculators only serve the trailing ~365 days; older
dates return 400. This script walks that window day by day and saves one CSV per
pair to data/<HOME>/<SPEND>.csv.

Usage:
    uv run archive.py --home INR --spend USD EUR GBP CAD SGD JPY CNY AUD AED
    uv run archive.py --home INR --spend USD EUR --both   # also forward direction

--both additionally records the "forward" direction (a foreign card spent in the
home country); it doubles the number of requests and is only needed for the
direction-trap analysis in the README. The default (traveller direction) is what
you want before a trip.
"""
import argparse
import csv
import datetime as dt
import os

import bestrates as br

FIELDS = ["date", "home", "spend", "visa_rate", "mc_rate", "visa_benchmark",
          "visa_fwd", "mc_fwd"]


def archive_pair(s, home, spend, start, end, both):
    rows = []
    d = start
    n = (end - start).days + 1
    i = 0
    while d <= end:
        i += 1
        v = br.visa_traveller(s, d, home, spend)
        m = br.mc_traveller(s, d, home, spend)
        row = {
            "date": d.isoformat(), "home": home, "spend": spend,
            "visa_rate": v["rate"] if v else "",
            "mc_rate": m["rate"] if m else "",
            "visa_benchmark": v["benchmark"] if v else "",
            "visa_fwd": "", "mc_fwd": "",
        }
        if both:
            vf = br.visa_forward(s, d, home, spend)
            mf = br.mc_forward(s, d, home, spend)
            row["visa_fwd"] = vf["rate"] if vf else ""
            row["mc_fwd"] = mf["rate"] if mf else ""
        rows.append(row)
        if i % 30 == 0:
            print(f"  [{home}/{spend}] {i}/{n} ... {d}")
        d += dt.timedelta(days=1)

    got = sum(1 for r in rows if r["visa_rate"] != "" and r["mc_rate"] != "")
    out_dir = os.path.join("data", home)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{spend}.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path} ({got}/{len(rows)} days with both rates)")
    return path


def main():
    ap = argparse.ArgumentParser(description="Archive a year of Visa vs Mastercard rates.")
    ap.add_argument("--home", required=True, help="your card's home currency, e.g. INR")
    ap.add_argument("--spend", required=True, nargs="+", help="one or more spend currencies")
    ap.add_argument("--both", action="store_true", help="also capture the forward direction")
    ap.add_argument("--days", type=int, default=364, help="how many days back to archive")
    args = ap.parse_args()

    home = args.home.upper()
    end = dt.date.today() - dt.timedelta(days=1)   # yesterday: fully settled everywhere
    start = end - dt.timedelta(days=args.days)
    s = br.session()
    print(f"Archiving {home} vs {', '.join(x.upper() for x in args.spend)}  "
          f"[{start} -> {end}]  both_directions={args.both}")
    for spend in args.spend:
        archive_pair(s, home, spend.upper(), start, end, args.both)


if __name__ == "__main__":
    main()
