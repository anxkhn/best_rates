import csv
import statistics as st

rows = list(csv.DictReader(open("rates.csv")))


def f(x):
    return float(x) if x not in (None, "") else None


def analyze(pair):
    data = [r for r in rows if r["pair"] == pair]
    recs = []
    for r in data:
        vr = f(r["visa_fx_per_inr"])   # USD/EUR per INR (Visa)
        mr = f(r["mc_fx_per_inr"])     # USD/EUR per INR (Mastercard)
        bench = f(r["visa_benchmark"]) # ECB mid benchmark
        vbill = f(r["visa_bill_amt"])  # foreign billed for 100000 INR (Visa)
        mbill = f(r["mc_bill_amt"])    # foreign billed for 100000 INR (MC)
        vinr = f(r["visa_inr_per_unit"])
        minr = f(r["mc_inr_per_unit"])
        recs.append({
            "date": r["date"], "vr": vr, "mr": mr, "bench": bench,
            "vbill": vbill, "mbill": mbill, "vinr": vinr, "minr": minr,
            # signed % gap of Visa vs MC on the rate
            "gap_pct": (vr - mr) / mr * 100,
            "v_markup": (vr - bench) / bench * 100 if bench else None,
            "m_markup": (mr - bench) / bench * 100 if bench else None,
        })

    n = len(recs)
    gaps = [x["gap_pct"] for x in recs]
    absgaps = [abs(g) for g in gaps]

    # Scenario A: spend 100000 INR, billed in foreign currency -> lower bill is better
    a_visa_win = sum(1 for x in recs if x["vbill"] < x["mbill"] - 1e-9)
    a_mc_win = sum(1 for x in recs if x["mbill"] < x["vbill"] - 1e-9)
    a_tie = n - a_visa_win - a_mc_win
    # average foreign saved per 100000 INR by choosing cheaper
    a_visa_saving = st.mean([x["mbill"] - x["vbill"] for x in recs])  # + means visa cheaper

    # Scenario B: spend 100 units foreign, billed in INR -> lower INR is better
    b_visa_win = sum(1 for x in recs if x["vinr"] < x["minr"] - 1e-9)
    b_mc_win = sum(1 for x in recs if x["minr"] < x["vinr"] - 1e-9)
    b_tie = n - b_visa_win - b_mc_win

    v_mk = [x["v_markup"] for x in recs if x["v_markup"] is not None]
    m_mk = [x["m_markup"] for x in recs if x["m_markup"] is not None]

    mx = max(recs, key=lambda x: abs(x["gap_pct"]))
    mn = min(recs, key=lambda x: abs(x["gap_pct"]))

    print("=" * 70)
    print(f"  {pair}   ({n} days, {recs[0]['date']} -> {recs[-1]['date']})")
    print("=" * 70)
    print(f"Rate gap (Visa vs MC), signed %:  mean {st.mean(gaps):+.4f}%  median {st.median(gaps):+.4f}%")
    print(f"Abs gap %:  mean {st.mean(absgaps):.4f}%  min {min(absgaps):.4f}%  max {max(absgaps):.4f}%  stdev {st.pstdev(absgaps):.4f}%")
    print(f"Max divergence: {mx['date']} gap {mx['gap_pct']:+.4f}%  (Visa {mx['vr']:.7f} vs MC {mx['mr']:.7f})")
    print(f"Days Visa rate > MC: {sum(1 for g in gaps if g>1e-9)} | MC > Visa: {sum(1 for g in gaps if g<-1e-9)} | equal: {sum(1 for g in gaps if abs(g)<=1e-9)}")
    print()
    print("MARKUP OVER ECB MID-MARKET (lower = fairer):")
    print(f"  Visa:        mean {st.mean(v_mk):.4f}%  min {min(v_mk):.4f}%  max {max(v_mk):.4f}%")
    print(f"  Mastercard:  mean {st.mean(m_mk):.4f}%  min {min(m_mk):.4f}%  max {max(m_mk):.4f}%")
    print(f"  Avg markup difference (MC - Visa): {st.mean(m_mk)-st.mean(v_mk):+.4f} pp")
    print()
    print("SCENARIO A - you SPEND INR, card billed in foreign (calculator's mode); lower foreign bill wins:")
    print(f"  Cheaper: Visa {a_visa_win} days | Mastercard {a_mc_win} days | tie {a_tie}")
    print(f"  Avg saving by using cheaper... Visa is on avg {a_visa_saving:+.4f} {pair[:3]} cheaper per 100000 INR")
    print()
    print("SCENARIO B - you SPEND foreign abroad, card billed in INR; lower INR wins:")
    print(f"  Cheaper: Visa {b_visa_win} days | Mastercard {b_mc_win} days | tie {b_tie}")
    print()
    return recs


for p in ["USD/INR", "EUR/INR"]:
    analyze(p)
