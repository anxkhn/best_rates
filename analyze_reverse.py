"""
analyze_reverse.py - validate the "reverse flips the winner" claim using REAL
reverse-direction data (INR card spending abroad), and quantify how far the
naive 1/forward inversion was off.
"""
import csv
import statistics as st


def f(x):
    return float(x) if x not in (None, "") else None


def load(path, pair, cols):
    out = {}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            if r["pair"] != pair:
                continue
            out[r["date"]] = {k: f(r[k]) for k in cols}
    return out


for pair in ["USD/INR", "EUR/INR"]:
    cur = pair[:3]
    fwd = load("rates.csv", pair, ["visa_inr_per_unit", "mc_inr_per_unit"])
    rev = load("rates_reverse.csv", pair,
               ["visa_inr_per_unit", "mc_inr_per_unit", "visa_benchmark", "mc_inr_per_unit"])

    dates = sorted(set(fwd) & set(rev))
    v_win = m_win = 0
    advs = []            # % Visa cheaper in REAL reverse (INR card abroad)
    v_spread = []        # Visa reverse vs its own inverse-of-forward (%)
    m_spread = []        # Mastercard reverse vs its own inverse-of-forward (%)
    inv_advs = []        # % Visa cheaper if we had used the INVERTED forward
    flip_days = 0
    for d in dates:
        vr = rev[d]["visa_inr_per_unit"]     # real INR per unit, Visa
        mr = rev[d]["mc_inr_per_unit"]       # real INR per unit, Mastercard
        # inverse of forward (what the old analysis assumed)
        v_inv = fwd[d]["visa_inr_per_unit"]  # note: forward csv already stored inr_per_unit = 1/rate
        m_inv = fwd[d]["mc_inr_per_unit"]
        adv = (mr - vr) / mr * 100           # + => Visa cheaper (real reverse)
        inv_adv = (m_inv - v_inv) / m_inv * 100
        advs.append(adv)
        inv_advs.append(inv_adv)
        v_spread.append((vr - v_inv) / v_inv * 100)
        m_spread.append((mr - m_inv) / m_inv * 100)
        if vr < mr:
            v_win += 1
        elif mr < vr:
            m_win += 1
        # did the winner flip between inverted-estimate and real reverse?
        if (adv > 0) != (inv_adv > 0):
            flip_days += 1

    print("=" * 72)
    print(f"  {pair}  REAL reverse direction: INR card spending {cur} abroad")
    print(f"  (rate = INR paid per 1 {cur}; lower is better; {len(dates)} days)")
    print("=" * 72)
    print(f"Winner (real reverse):  Visa {v_win} days | Mastercard {m_win} days | Visa win% {v_win/len(dates)*100:.1f}")
    print(f"Visa advantage (real):  mean {st.mean(advs):+.4f}%  median {st.median(advs):+.4f}%  "
          f"min {min(advs):+.4f}%  max {max(advs):+.4f}%")
    print()
    print("Directional spread vs naive 1/forward inversion (how wrong inversion was):")
    print(f"  Visa reverse is on avg {st.mean(v_spread):+.4f}% vs its own inverse-of-forward")
    print(f"  MC   reverse is on avg {st.mean(m_spread):+.4f}% vs its own inverse-of-forward")
    print()
    print("Old (inverted-forward) estimate vs real:")
    print(f"  Inverted-estimate Visa advantage: mean {st.mean(inv_advs):+.4f}%")
    print(f"  Real            Visa advantage:    mean {st.mean(advs):+.4f}%")
    print(f"  Days the winner FLIPPED between estimate and reality: {flip_days}/{len(dates)}")
    print()
