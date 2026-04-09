# Currency Approach — CrewWealth (Day 1)

## Overview

CrewWealth supports a fixed set of currencies suited to the maritime/seafarer
audience.  All monetary data is stored in its **original currency** and totals
on the dashboard and projection pages are always displayed in the user's chosen
**base currency** so there is always one clear headline number.

---

## Supported Currencies

| Code | Symbol | Name              | Notes                          |
|------|--------|-------------------|--------------------------------|
| EUR  | €      | Euro              | Default base currency          |
| USD  | $      | US Dollar         | Common contract/wage currency  |
| GBP  | £      | British Pound     | Common in UK / international   |
| PHP  | ₱      | Philippine Peso   | Remittance — Philippine crew   |
| IDR  | Rp     | Indonesian Rupiah | Remittance — Indonesian crew   |

Only ISO 4217 codes from the list above are accepted by the API and validated
on the frontend.  Any value outside this set is rejected with a clear error
message.

---

## Base Currency Per User

Every user has a single **base currency** (`users.baseCurrency`, default `EUR`).
This field drives:

- Dashboard totals (Net Worth, Savings, etc.)
- 12/24/36-month wealth projections
- Any report that needs a single summarised number

The base currency is set during registration and can be changed in **Settings →
Currency**.  Changing the base currency does **not** alter stored amounts; it
only changes how conversions are displayed.

---

## Account Currency

Each account carries its own currency (`accounts.currency`, default = user
`baseCurrency`).  Transaction lists always show the **original currency** of
the account so the user sees exactly what was recorded.

---

## Dashboard & Projection Totals

All multi-currency account balances shown on the dashboard or in projections
are converted to the user's base currency using the current manual FX rate for
that currency pair.

Rules:

1. Look up the manual FX rate for `(account.currency → user.baseCurrency)`.
2. If a rate exists → multiply and sum.
3. If **no rate is configured** → do **not** silently include the account in the
   total; instead surface a visible warning (see below).

Same accounts rule applies to the 36-month projection: only accounts whose
currency can be converted to base currency contribute to the projected balance.

---

## Manual FX Rates

For MVP the only source of exchange rates is **manual rates** entered by the
user in Settings.  There is no automatic rate feed.

Data structure (Firestore — `fxRates` sub-collection under each user document):

```
users/{uid}/fxRates/{rateId}
  base:       "USD"          # source currency (ISO 4217)
  quote:      "EUR"          # target / base currency (ISO 4217)
  rate:       0.92           # 1 base unit = rate quote units
  updatedAt:  <timestamp>
  source:     "manual"
```

A rate of `USD → EUR = 0.92` means $1 = €0.92.

Rates are directional: the backend always looks up `(account.currency → user.baseCurrency)`.
If only the reverse direction is stored, the backend will **not** silently invert
it; the user must enter the correct direction.

---

## Missing-Rate Warning Policy

When a conversion is needed but no manual FX rate is available:

- **Dashboard**: display a non-blocking inline warning
  *"⚠ USD accounts excluded from total — add a FX rate in Settings"*  
  next to the affected total.  The total is shown without those accounts rather
  than using a wrong or zero-filled value.

- **Projection**: the affected accounts are excluded and a warning key
  `missing_fx_currencies` is included in the JSON response so the frontend can
  render the same notice.

- **Never**: silently return `0` or an incorrect sum when a rate is missing.

---

## Data Model Summary

```
users/{uid}
  baseCurrency: "EUR"          # ISO 4217 — default EUR
  settings:
    currency: "EUR"            # legacy field (kept for backwards compat)
    ...

users/{uid}/accounts/{accountId}
  name:     "Seafarer Savings"
  currency: "USD"              # ISO 4217 — default = user.baseCurrency
  balance:  5000
  ...

users/{uid}/fxRates/{rateId}   # optional, placeholder for MVP
  base:      "USD"
  quote:     "EUR"
  rate:      0.92
  updatedAt: <timestamp>
  source:    "manual"
```

---

## Frontend Formatting

All monetary values rendered in the UI **must** go through the shared
`formatMoney(amount, currency, locale)` helper defined in
`app/static/js/currency.js`.  Hardcoded `€` symbols are forbidden in new
code; existing occurrences should be migrated to use `currency-symbol` spans
that are updated by the helper.

The helper uses the browser's `Intl.NumberFormat` API for locale-aware
formatting (correct thousands separators, decimal marks, and currency symbols).

---

## Not In Scope (Day 1)

- Automatic exchange-rate feeds (e.g. ECB or exchangerate-api)
- Tax calculation or reservation logic
- Historical rate tracking
- Currency conversion on individual transaction rows

These will be addressed in subsequent days of the multi-currency rollout.
