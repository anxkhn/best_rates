# Best Rates: Visa vs Mastercard before your trip

A small tool to compare the currency conversion rates of **both card networks,
Visa and Mastercard, on the same day**, so you can pick the one that costs you
less abroad. I built it for my own international trip and then turned it into
something anyone can point at their own currencies.

Every time you tap a card abroad, the **card network** (Visa or Mastercard), not
your bank, sets the base exchange rate that converts the foreign price into your
home currency. Visa and Mastercard both publish these daily rates, but they are
buried inside on-page calculators. This tool reads both, side by side, and tells
you who is cheaper.

---

## Quick start: check your own trip

Requires [uv](https://docs.astral.sh/uv/). No cookies, no API keys, no personal
data: it uses [`curl_cffi`](https://github.com/lexiforest/curl_cffi) with a real
Chrome fingerprint to read the same public calculators you can open in a
browser.

```bash
uv sync
uv run trip.py --home INR --spend EUR
```

- `--home` is your card's currency (what you get billed in).
- `--spend` is the currency of the country you are visiting.
- `--amount` (optional) is an example amount, to see the rupee/dollar impact.

```bash
uv run trip.py --home INR --spend USD --amount 2500
uv run trip.py --home USD --spend JPY          # a US card holidaying in Japan
uv run trip.py --home GBP --spend EUR          # a UK card in the Eurozone
```

It fetches today's live rate from both networks and prints who is cheaper and by
how much. Example:

```
====================================================================
  EUR on a INR card   (rate as of 2026-07-05, latest available)
====================================================================
  You spend abroad : EUR 2,000
  Network           rate (INR/EUR)        you are billed
  ------------------------------------------------------
  Visa                    109.3778        INR 218,755.61
  Mastercard              109.2175        INR 218,435.03
  ECB mid                 109.0020        INR 218,004.00
  ------------------------------------------------------
  Verdict: Mastercard is cheaper today by INR 320.58 (0.147%).
  Markup over ECB mid: Visa +0.345%   Mastercard +0.198%
```

If you have archived a full year for that pair (see below), `trip.py` also prints
the one-year track record: who wins more often, this week / month / year, and the
best and worst days.

---

## The data only lasts a year, so I archived it

Both calculators only serve the **trailing ~365 days**; older dates return
`400`. To study a whole year you have to capture it while it is still live, so I
archived it. This repo ships a year of daily rates for an **Indian (INR) card**
spending in nine popular destinations, under [`data/INR/`](data/INR):

`USD` `EUR` `GBP` `CAD` `SGD` `JPY` `CNY` `AUD` `AED`

You can archive (download) your own year for any currency pair the calculators
support, to compare the last 12 months offline:

```bash
uv run archive.py --home INR --spend USD EUR GBP CAD SGD JPY CNY AUD AED
uv run archive.py --home GBP --spend EUR USD          # any home currency works
```

Each pair is saved to `data/<HOME>/<SPEND>.csv`. Add `--both` to also record the
reverse "forward" direction (only needed for the direction-trap analysis below).

---

## Case study: an Indian (INR) card spending USD and EUR

My actual question was: *if I spend in USD or EUR abroad on my INR card, is Visa
or Mastercard cheaper, and by how much?* Here is a full year of daily rates
(**2025-07-06 to 2026-07-05**, 365 days per pair), spending abroad and billed in
INR (lower INR per foreign unit = better).

**TL;DR: Mastercard is cheaper slightly more often, on ~58-61% of days, by about
0.06% on average. It is close to a coin flip, but Mastercard has the small,
consistent edge because it prices closer to the interbank mid-rate.**

| Metric | USD/INR | EUR/INR |
| --- | --- | --- |
| Days **Mastercard** was cheaper | **213 / 365 (58%)** | **223 / 365 (61%)** |
| Days Visa was cheaper | 152 / 365 | 142 / 365 |
| Average Mastercard advantage | +0.057% | +0.067% |
| Range of the daily gap | -1.27% to +1.54% | -1.27% to +1.95% |
| Avg markup over ECB mid (Visa / MC) | 0.15% / 0.10% | 0.49% / 0.42% |

### How much money is that, really?

| You spend abroad | Avg Visa bill | Avg Mastercard bill | Mastercard saves |
| --- | --- | --- | --- |
| $1,000 | Rs 90,871 | Rs 90,818 | **~Rs 53** on average |
| Euro 1,000 | Rs 1,06,272 | Rs 1,06,198 | **~Rs 74** on average |

The gap is tiny (a fraction of a percent) and swings both ways day to day, so for
a single trip it barely moves the needle. What dominates your real cost is your
**bank's own forex markup and fees (typically 2 to 3.5%)**, which neither network
controls and this tool does not model. Pick the card with the lower bank markup
first; the network is the tie-breaker.

### It holds across other destinations too

The same INR card, one year, spending in nine currencies. Mastercard is cheaper
more often in every single one:

| Spend | Mastercard win rate | Avg MC advantage |
| --- | --- | --- |
| USD | 213/365 (58%) | +0.057% |
| EUR | 223/365 (61%) | +0.067% |
| GBP | 214/365 (59%) | +0.063% |
| CAD | 217/365 (59%) | +0.077% |
| SGD | 222/365 (61%) | +0.069% |
| JPY | 217/365 (59%) | +0.089% |
| CNY | 185/365 (51%) | +0.016% |
| AUD | 205/365 (56%) | +0.050% |
| AED | 226/365 (62%) | +0.067% |

CNY is almost a dead heat (51%); the rest lean Mastercard by a clear but small
margin.

---

## Charts

Every chart uses the **real** data for its direction (nothing is inverted). "MC
advantage" = the percentage by which Mastercard is cheaper than Visa that day
(above 0 = Mastercard cheaper, below 0 = Visa cheaper).

### Who wins, USD and EUR, both directions
Mastercard leads all four bars.

![Win rate](charts/00_winrate.png)

### USD rate billed to an INR card spent abroad
Visa and Mastercard track each other closely; the edge lives in the tiny daily
gap between the lines.

![USD rate](charts/USD_01_rate.png)

### USD, spending abroad on an INR card (the direction that matters for a traveller)
![USD reverse gap](charts/USD_03_reverse_gap.png)

The EUR/INR equivalents are in [`charts/`](charts/): `EUR_01_rate.png`,
`EUR_03_reverse_gap.png`, and the forward / reality-check charts described next.

---

## Anomalies I ran into

### 1. The direction trap: you cannot invert the rate

A conversion looks symmetric, so it is tempting to take the "spend INR, billed
USD" rate and invert it (`1 / rate`) to guess "spend USD, billed INR". **That is
wrong.** Each network charges a **directional spread**, so the real reverse rate
is worse than the naive inverse by, on average:

- **+0.38% (Visa) / +0.18% (Mastercard)** for USD, and
- **+1.00% (Visa) / +0.79% (Mastercard)** for EUR.

EUR's spread is larger because an INR card settles Eurozone spend through a USD
base, so it crosses the spread twice. Because the spread is directional, the
predicted winner from the inverted rate disagrees with the real winner on
**124/365 days (USD)** and **135/365 days (EUR)**, about one day in three.

Concrete flip, 2026-07-01, USD:

| Direction | Visa | Mastercard | Cheaper |
| --- | --- | --- | --- |
| Forward: spend 100,000 INR, billed USD | 1,058.03 USD | 1,050.25 USD | Mastercard |
| Reverse: spend 1,000 USD, billed INR | 94,765 INR | 95,290 INR | Visa |

The lesson: **always query the direction you actually use.** That is why
`trip.py` only ever queries the traveller direction, and never inverts.

![USD reality check](charts/USD_04_reverse_check.png)

An earlier version of this project concluded "Visa wins" precisely by inverting
instead of measuring. Measured directly, Mastercard comes out ahead. Retracted.

### 2. Big single-day swings

Most days the two networks are within ~0.1%, but the gap occasionally blows out
past 1.5% (for example Mastercard was **+1.95% cheaper on 2026-02-03** for EUR,
and Visa was **1.27% cheaper on 2026-03-20**). These are usually days where one
network updates its rate a few hours before the other around a volatile market
move, so for one day the stale side looks very cheap or very expensive.

### 3. Weekend and holiday carry-over

Neither network refreshes on weekends and bank holidays; the last business-day
rate carries over. So a run of identical daily rates is expected, not a bug.

---

## How to regenerate the case study

```bash
uv run eda.py     # redraws every chart in charts/ and rewrites summary.json
```

`eda.py` reads `data/INR/USD.csv` and `data/INR/EUR.csv`.

---

## Files

| File | What it does |
| --- | --- |
| `trip.py` | The tool: live "who is cheaper right now" verdict for `--home`/`--spend`, plus the one-year track record if archived. |
| `archive.py` | Download and save the last ~365 days for any currency pairs to `data/<HOME>/<SPEND>.csv`. |
| `eda.py` | Regenerate the India case-study charts (`charts/`) and `summary.json`. |
| `bestrates.py` | Shared core: the Visa and Mastercard fetch functions. |
| `data/INR/*.csv` | Archived year of INR-card rates for nine spend currencies. |
| `charts/` | Generated PNG charts. |
| `summary.json` | Case-study statistics as JSON. |

### `data/<HOME>/<SPEND>.csv` columns

| Column | Meaning |
| --- | --- |
| `date` | Rate date (YYYY-MM-DD). |
| `home` / `spend` | Home (billing) and spend currency codes. |
| `visa_rate` / `mc_rate` | Home currency per 1 spend unit, spending abroad (lower = cheaper). |
| `visa_benchmark` | ECB mid-market rate (home per spend), from Visa's response. |
| `visa_fwd` / `mc_fwd` | Forward rate (spend per 1 home unit); only filled when archived with `--both`. |

---

## Data sources and method

- **Visa:** `https://www.visa.co.in/cmsapi/fx/rates` (the public
  [Visa exchange-rate calculator](https://www.visa.co.in/support/consumer/travel-support/exchange-rate-calculator.html)).
  Also returns the ECB benchmark and Visa's own markup.
- **Mastercard:** `https://www.mastercard.com/marketingservices/public/mccom-services/currency-conversions/conversion-rates`
  (the public
  [Mastercard currency converter](https://www.mastercard.com/in/en/personal/get-support/currency-exchange-rate-converter.html)).
- Both endpoints serve only the **trailing ~365 days**; older dates return
  `400 Bad Request`, which is why the year is archived while it is live.
- Requests use `curl_cffi` (`impersonate="chrome"`) to present a real browser
  TLS/HTTP fingerprint, which cleanly passes the Cloudflare (Visa) and Akamai
  (Mastercard) bot protection without any cookies or credentials.
- The card rate is **amount-independent** (verified against 1, 100 and 100,000
  units), so the per-unit rate is all you need.

## Caveats

- These are **network base rates**. Your final cost also includes your issuing
  bank's markup and forex fee, which this tool does not model and which usually
  dwarf the network difference.
- **Direction is not symmetric.** Never infer the reverse rate by inverting the
  forward one; query the direction you actually use.
- The margin between the two networks is small (well under 0.2% on a typical day)
  and swings both ways, so for a single trip the choice barely matters. Over many
  transactions Mastercard has the slight, consistent edge.
- Rates on weekends and holidays carry over the last business-day value.

## Disclaimer

This project is **not affiliated with, endorsed by, or connected to Visa or
Mastercard** in any way. "Visa" and "Mastercard" are trademarks of their
respective owners. It only reads the same public rate calculators anyone can open
in a browser. Please **use it responsibly**: keep request volumes modest, respect
each site's terms of use, and treat the output as informational only, not
financial advice.

## License

Licensed under the **GNU General Public License v3.0** (GPLv3). See
[`LICENSE`](LICENSE). For informational purposes only; not financial advice.
