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
are converted to the user's base currency.

Rules:

1. Use manual user FX override first (`users/{uid}/fxRates`).
2. If no manual rate exists, use latest public API FX rates.
3. If no valid path is still available, apply safe fallback `1.0` so totals are
   still fully included and never excluded.

Same rule applies to the 36-month projection: all accounts contribute to the
projected balance (manual rate → API rate → fallback `1.0`).

---

## Manual FX Rates

Manual rates can be entered in **Settings → Manual FX Rates** and always
override auto-fetched rates from the public FX API.

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

Rates are directional, but conversion resolution supports:

1. Direct pair (`EUR -> GBP`)
2. Inverse pair (`GBP -> EUR` used as `1 / rate`)
3. Indirect path over known rates (for example `EUR -> USD -> GBP`)

If no valid path exists, a safe fallback (`1.0`) is applied so the amount is
still included in totals.

---

## Missing-Rate Fallback Policy

When a conversion is needed but no valid FX path is available:

- **Dashboard/Budget/Reports**: keep totals complete by applying fallback rate
  (`1.0`) and avoid yellow "excluded amounts" warnings.

- **Projection API**: also applies the same fallback logic so API totals match
  UI totals.

- **Settings UX**: users can add manual rates for any pair, which then take
  precedence over API/fallback values.

---

## Manual Test Steps (FX fallback)

1. Create two accounts:
   - `EUR` account balance `1200`
   - `USD` account balance `100`
2. Set user base currency to `GBP`.
3. Leave `EUR->GBP` unset.
4. Verify:
   - totals still include both account amounts in GBP (no exclusions),
   - no yellow "missing FX/excluded" warning is shown,
   - optional manual FX override can be saved in Settings and takes effect,
   - recent transaction rows keep original amount + original currency.

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

- Tax calculation or reservation logic
- Historical rate tracking
- Currency conversion on individual transaction rows

These will be addressed in subsequent days of the multi-currency rollout.
