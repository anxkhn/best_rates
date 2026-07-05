"""
bestrates.py - shared core for talking to the Visa and Mastercard public
currency-conversion calculators.

Both networks publish a daily card exchange rate through the same on-page
calculators you can open in a browser. We read them with curl_cffi using a real
Chrome fingerprint, so there are no cookies, no API keys and no personal data.

Two directions exist, and they are NOT the inverse of each other (each network
charges a directional spread):

  traveller / "reverse"  -> you spend `spend` abroad, you are billed in `home`.
                            rate = HOME currency per 1 unit of SPEND currency.
                            Lower is better for you.
  "forward"              -> a `spend`-currency card is used in the `home`
                            country, billed in `spend`.
                            rate = SPEND currency per 1 unit of HOME currency.

The traveller direction is the one that matters when you travel, so it is the
default everywhere in this project.
"""
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


def session():
    return requests.Session(impersonate="chrome")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _get(s, url, headers, params, tries=4):
    for i in range(tries):
        try:
            r = s.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 400:
                return None  # date outside the trailing-year window / no rate
        except Exception:
            pass
        time.sleep(1.2 * (i + 1))
    return None


def visa_traveller(s, date, home, spend, amount=1000):
    """Spend `amount` of `spend` abroad, billed in `home`. rate = home per spend.

    Note: Visa's calculator swaps the from/to params relative to the result, so
    to get "home per 1 spend unit" we pass fromCurr=home, toCurr=spend.
    """
    mdy = date.strftime("%m/%d/%Y")
    j = _get(s, VISA, HV, {"amount": str(amount), "fee": "0", "utcConvertedDate": mdy,
                           "exchangedate": mdy, "fromCurr": home, "toCurr": spend})
    if not j or j.get("status") != "success":
        return None
    ov = j["originalValues"]
    b = (ov.get("benchmarks") or [{}])[0]
    return {"rate": _f(ov.get("fxRateVisa")), "bill": _f(ov.get("toAmountWithVisaRate")),
            "benchmark": _f(b.get("benchmarkFxRate"))}


def mc_traveller(s, date, home, spend, amount=1000):
    """Spend `amount` of `spend` abroad, billed in `home`. rate = home per spend."""
    iso = date.strftime("%Y-%m-%d")
    j = _get(s, MC, HM, {"exchange_date": iso, "transaction_currency": spend,
                         "cardholder_billing_currency": home, "bank_fee": "0",
                         "transaction_amount": str(amount)})
    if not j or "data" not in j or j["data"].get("errorCode"):
        return None
    d = j["data"]
    return {"rate": _f(d.get("conversionRate")), "bill": _f(d.get("crdhldBillAmt"))}


def visa_forward(s, date, home, spend, amount=100000):
    """A `spend` card used in the `home` country. rate = spend per 1 home unit."""
    mdy = date.strftime("%m/%d/%Y")
    j = _get(s, VISA, HV, {"amount": str(amount), "fee": "0", "utcConvertedDate": mdy,
                           "exchangedate": mdy, "fromCurr": spend, "toCurr": home})
    if not j or j.get("status") != "success":
        return None
    ov = j["originalValues"]
    return {"rate": _f(ov.get("fxRateVisa"))}


def mc_forward(s, date, home, spend, amount=100000):
    """A `spend` card used in the `home` country. rate = spend per 1 home unit."""
    iso = date.strftime("%Y-%m-%d")
    j = _get(s, MC, HM, {"exchange_date": iso, "transaction_currency": home,
                         "cardholder_billing_currency": spend, "bank_fee": "0",
                         "transaction_amount": str(amount)})
    if not j or "data" not in j or j["data"].get("errorCode"):
        return None
    return {"rate": _f(j["data"].get("conversionRate"))}


def latest_traveller(s, home, spend, amount=1000, look_back=8):
    """Most recent day (today first, stepping back over weekends/holidays) for
    which BOTH networks return a traveller rate. Returns (date, visa, mc)."""
    d = dt.date.today()
    for _ in range(look_back):
        v = visa_traveller(s, d, home, spend, amount)
        m = mc_traveller(s, d, home, spend, amount)
        if v and m and v["rate"] and m["rate"]:
            return d, v, m
        d -= dt.timedelta(days=1)
    return None, None, None
