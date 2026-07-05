"""
collect_reverse.py - collect the REVERSE direction from both networks.

Original rates.csv modelled: transaction in INR, billed in USD/EUR
  (a USD/EUR card used in India).
This collects: transaction in USD/EUR, billed in INR
  (an INR card used abroad) -> the rate is INR per 1 foreign unit.

We query each network directly in this direction instead of inverting the
forward rate, because the networks apply a directional spread, so the reverse
rate is NOT simply 1 / forward.
"""
import csv
import datetime as dt
import time

from curl_cffi import requests

VISA = "https://www.visa.co.in/cmsapi/fx/rates"
MC = "https://www.mastercard.com/marketingservices/public/mccom-services/currency-conversions/conversion-rates"
HV = {"Accept": "application/json, text/plain, */*",
      "Referer": "https://www.visa.co.in/support/consumer/travel-support/exchange-rate-calculator.html"}
HM = {"Accept": "*/*",
      "Referer": "https://www.mastercard.com/in/en/personal/get-support/currency-exchange-rate-converter.html"}

AMOUNT = "1000"            # spend 1000 USD / 1000 EUR abroad
CURRENCIES = ["USD", "EUR"]
START = dt.date(2025, 7, 6)
END = dt.date(2026, 7, 5)

s = requests.Session(impersonate="chrome")


def get(url, headers, params, tries=4):
    for i in range(tries):
        try:
            r = s.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 400:
                return None
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def visa_rev(d, cur):
    # from foreign -> INR: rate returned as INR per 1 foreign unit
    mdy = d.strftime("%m/%d/%Y")
    j = get(VISA, HV, {"amount": AMOUNT, "fee": "0", "utcConvertedDate": mdy,
                       "exchangedate": mdy, "fromCurr": "INR", "toCurr": cur})
    if not j or j.get("status") != "success":
        return None
    ov = j["originalValues"]
    bench = (ov.get("benchmarks") or [{}])[0]
    return {"inr_per_unit": ov.get("fxRateVisa"),
            "bill_inr": ov.get("toAmountWithVisaRate"),
            "benchmark": bench.get("benchmarkFxRate")}


def mc_rev(d, cur):
    # transaction in foreign, billed in INR: conversionRate = INR per foreign unit
    iso = d.strftime("%Y-%m-%d")
    j = get(MC, HM, {"exchange_date": iso, "transaction_currency": cur,
                     "cardholder_billing_currency": "INR", "bank_fee": "0",
                     "transaction_amount": AMOUNT})
    if not j or "data" not in j or j["data"].get("errorCode"):
        return None
    dta = j["data"]
    return {"inr_per_unit": dta.get("conversionRate"),
            "bill_inr": dta.get("crdhldBillAmt")}


def main():
    rows = []
    d = START
    n = (END - START).days + 1
    i = 0
    while d <= END:
        i += 1
        for cur in CURRENCIES:
            v = visa_rev(d, cur)
            m = mc_rev(d, cur)
            rows.append({
                "date": d.isoformat(),
                "pair": f"{cur}/INR",
                "visa_inr_per_unit": v["inr_per_unit"] if v else "",
                "visa_bill_inr": v["bill_inr"] if v else "",
                "visa_benchmark": v["benchmark"] if v else "",
                "mc_inr_per_unit": m["inr_per_unit"] if m else "",
                "mc_bill_inr": m["bill_inr"] if m else "",
            })
        if i % 20 == 0:
            print(f"{i}/{n} days ... {d}")
        d += dt.timedelta(days=1)

    with open("rates_reverse.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote rates_reverse.csv with {len(rows)} rows")


if __name__ == "__main__":
    main()
