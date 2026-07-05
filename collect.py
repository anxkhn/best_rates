import csv
import datetime as dt
import time

from curl_cffi import requests

VISA = "https://www.visa.co.in/cmsapi/fx/rates"
MC = "https://www.mastercard.com/marketingservices/public/mccom-services/currency-conversions/conversion-rates"

HV = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.visa.co.in/support/consumer/travel-support/exchange-rate-calculator.html",
}
HM = {
    "Accept": "*/*",
    "Referer": "https://www.mastercard.com/in/en/personal/get-support/currency-exchange-rate-converter.html",
}

AMOUNT = "100000"  # transaction amount in INR
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
                return None  # date outside range / no rate
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def visa_rate(d, cur):
    mdy = d.strftime("%m/%d/%Y")
    j = get(VISA, HV, {
        "amount": AMOUNT, "fee": "0",
        "utcConvertedDate": mdy, "exchangedate": mdy,
        "fromCurr": cur, "toCurr": "INR",
    })
    if not j or j.get("status") != "success":
        return None
    ov = j["originalValues"]
    bench = ov.get("benchmarks") or [{}]
    return {
        "rate_fx_per_inr": ov.get("fxRateVisa"),
        "inr_per_unit": j.get("reverseAmount"),
        "bill_amt": ov.get("toAmountWithVisaRate"),
        "benchmark_rate": bench[0].get("benchmarkFxRate"),
        "markup": bench[0].get("markupWithoutAdditionalFee"),
    }


def mc_rate(d, cur):
    iso = d.strftime("%Y-%m-%d")
    j = get(MC, HM, {
        "exchange_date": iso, "transaction_currency": "INR",
        "cardholder_billing_currency": cur, "bank_fee": "0",
        "transaction_amount": AMOUNT,
    })
    if not j or "data" not in j or j["data"].get("errorCode"):
        return None
    dta = j["data"]
    rate = dta.get("conversionRate")
    bill = dta.get("crdhldBillAmt")
    inr_per = None
    try:
        inr_per = round(1.0 / float(rate), 6)
    except Exception:
        pass
    return {
        "rate_fx_per_inr": rate,
        "inr_per_unit": inr_per,
        "bill_amt": bill,
    }


def main():
    rows = []
    d = START
    n = (END - START).days + 1
    i = 0
    while d <= END:
        i += 1
        for cur in CURRENCIES:
            v = visa_rate(d, cur)
            m = mc_rate(d, cur)
            rows.append({
                "date": d.isoformat(),
                "pair": f"{cur}/INR",
                "visa_fx_per_inr": v["rate_fx_per_inr"] if v else "",
                "visa_inr_per_unit": v["inr_per_unit"] if v else "",
                "visa_bill_amt": v["bill_amt"] if v else "",
                "visa_benchmark": v.get("benchmark_rate") if v else "",
                "visa_markup": v.get("markup") if v else "",
                "mc_fx_per_inr": m["rate_fx_per_inr"] if m else "",
                "mc_inr_per_unit": m["inr_per_unit"] if m else "",
                "mc_bill_amt": m["bill_amt"] if m else "",
            })
        if i % 20 == 0:
            print(f"{i}/{n} days ... {d}")
        d += dt.timedelta(days=1)

    fields = list(rows[0].keys())
    with open("rates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote rates.csv with {len(rows)} rows")


if __name__ == "__main__":
    main()
