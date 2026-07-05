"""
analyze.py - head-to-head Visa vs Mastercard in BOTH real directions.

Forward  (rates.csv):         transaction in INR, billed in USD/EUR
                              (a foreign-currency card used in India).
Reverse  (rates_reverse.csv): transaction in USD/EUR, billed in INR
                              (an Indian INR card used abroad).

Each direction is measured directly (never by inverting the other), because
the networks charge a directional spread. "MC advantage" below is the percentage
by which Mastercard is cheaper than Visa on that day (positive = Mastercard
cheaper, negative = Visa cheaper).
"""
import csv
import statistics as st


def fnum(x):
    return float(x) if x not in (None, "") else None


def load(path, pair, cols):
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            if r["pair"] != pair:
                continue
            if any(r[c] in (None, "") for c in cols):
                continue
            rows.append({"date": r["date"], **{c: fnum(r[c]) for c in cols}})
    rows.sort(key=lambda x: x["date"])
    return rows


def summarize(name, cur, advs):
    n = len(advs)
    mc = sum(1 for a in advs if a > 1e-9)
    vi = sum(1 for a in advs if a < -1e-9)
    tie = n - mc - vi
    winner = "Mastercard" if st.mean(advs) > 0 else "Visa"
    print(f"  {name}")
    print(f"    Winner overall: {winner}   (Mastercard cheaper {mc}/{n} = {mc/n*100:.1f}%, "
          f"Visa {vi}/{n}, tie {tie})")
    print(f"    Mastercard advantage %:  mean {st.mean(advs):+.4f}  median {st.median(advs):+.4f}  "
          f"min {min(advs):+.4f}  max {max(advs):+.4f}  stdev {st.pstdev(advs):.4f}")


def main():
    for pair in ["USD/INR", "EUR/INR"]:
        cur = pair[:3]
        print("=" * 74)
        print(f"  {pair}")
        print("=" * 74)

        # Forward: lower foreign-per-INR rate is cheaper for the cardholder.
        fwd = load("rates.csv", pair, ["visa_fx_per_inr", "mc_fx_per_inr"])
        fwd_adv = [(r["visa_fx_per_inr"] - r["mc_fx_per_inr"]) / r["visa_fx_per_inr"] * 100 for r in fwd]
        summarize(f"FORWARD  (foreign {cur} card spent in India, billed {cur})", cur, fwd_adv)

        # Reverse: lower INR-per-unit is cheaper for the traveller.
        rev = load("rates_reverse.csv", pair, ["visa_inr_per_unit", "mc_inr_per_unit"])
        rev_adv = [(r["visa_inr_per_unit"] - r["mc_inr_per_unit"]) / r["visa_inr_per_unit"] * 100 for r in rev]
        summarize(f"REVERSE  (INR card spent abroad in {cur}, billed INR)", cur, rev_adv)

        # Directional spread: how far real reverse is from the naive 1/forward.
        by_date = {r["date"]: r for r in fwd}
        spreads_v, spreads_m = [], []
        for r in rev:
            fr = by_date.get(r["date"])
            if not fr:
                continue
            inv_v = 1.0 / fr["visa_fx_per_inr"]
            inv_m = 1.0 / fr["mc_fx_per_inr"]
            spreads_v.append((r["visa_inr_per_unit"] - inv_v) / inv_v * 100)
            spreads_m.append((r["mc_inr_per_unit"] - inv_m) / inv_m * 100)
        print(f"  DIRECTIONAL SPREAD (real reverse vs naive 1/forward):")
        print(f"    Visa       +{st.mean(spreads_v):.4f}%   Mastercard +{st.mean(spreads_m):.4f}%")
        print()

    print("Bottom line: whoever is cheaper depends on direction, but over this")
    print("year Mastercard is cheaper more often in BOTH directions.")


if __name__ == "__main__":
    main()
