# Currency Approach — CrewWealth

## Overview

CrewWealth is designed for maritime professionals who are often paid in one currency (e.g. USD) while spending in another (EUR, PHP, IDR). This document captures the currency design decisions, data model, and the multi-day implementation plan.

---

## Supported Currencies (MVP)

Only the following five ISO 4217 codes are supported in the MVP:

| Code | Symbol | Currency           | Primary use case              |
|------|--------|--------------------|-------------------------------|
| EUR  | €      | Euro               | European home spending        |
| USD  | $      | US Dollar          | Most maritime contracts       |
| GBP  | £      | British Pound      | UK-based crew / spending      |
| PHP  | ₱      | Philippine Peso    | Filipino crew remittances     |
| IDR  | Rp     | Indonesian Rupiah  | Indonesian crew remittances   |

Any other currency code is rejected by the backend with a 400 error.

---

## Core Rules

1. **Base currency per user** — every user has a single `baseCurrency` (default: `EUR`). This is set in Settings and stored on the user document.
2. **Account currency** — every account has an explicit `currency` field (default: user's `baseCurrency`).
3. **Transaction currency** — every transaction has an explicit `currency` field (default: the account's `currency`).
4. **Dashboard / projections** — totals and projections are always shown in the user's `baseCurrency`. A "Converted to \<code\>" label is shown whenever a conversion happened.
5. **Account and transaction lists** — show the original amount + original currency code (e.g. `$300 USD`, `₱12,000 PHP`).
6. **FX rates** — MVP uses **manual FX rates** stored in Firestore. There is no automatic external rate sync. Rates are entered by the user in Settings.
7. **Missing FX rate** — if a required FX rate is absent, a visible warning is shown and the total is **never silently computed as 0 or a wrong value**. Affected accounts/totals are excluded from the converted sum until the rate is provided.

---

## Data Model

```
users/{uid}
  baseCurrency: "EUR"          # ISO 4217; default "EUR"
  locale: "en-NL"              # BCP 47; used for Intl.NumberFormat
  settings:
    currency: "EUR"            # legacy field; kept for backward-compat
    language: "en"
    theme: "light"

users/{uid}/accounts/{accountId}
  name: "Offshore Savings"
  balance: 2500
  currency: "USD"              # ISO 4217; default = user.baseCurrency
  offBudget: false
  icon: "🏦"

users/{uid}/transactions/{txId}
  type: "income" | "expense" | "transfer" | "deposit" | "payment" | "salary"
  amount: 250
  currency: "USD"              # ISO 4217; default = account.currency
  accountId: "..."
  date: <timestamp>

users/{uid}/fxRates/{rateId}   # placeholder – Day 2/3 full CRUD
  base: "USD"                  # from currency
  quote: "EUR"                 # to currency (user's baseCurrency)
  rate: 0.92
  updatedAt: <timestamp>
  source: "manual"
```

---

## Multi-Day Implementation Plan

### Day 1 — Scaffolding (this PR) ✅
- `docs/currency-approach.md` (this file)
- Backend: `config/currencies.py` with `SUPPORTED_CURRENCIES` + `DEFAULT_BASE_CURRENCY`
- Backend: `app/models/user.py` model field documentation
- Backend: `app/routes/currency.py` – align to supported currencies; add manual FX rates placeholder endpoint
- Backend: `app/routes/api.py` – return `baseCurrency` in projection response
- Frontend: `app/static/js/currency.js` – `SUPPORTED_CURRENCIES`, `formatMoney(amount, currency, locale)`
- Frontend: `settings.html` – limit dropdown to 5 supported currencies, save as `baseCurrency`
- Frontend: `register.html` – write `baseCurrency` + account `currency` on user creation
- Tests: `tests/test_currency.py` – validate supported currencies + format helper

### Day 2 — Backend: Currency on Accounts & Transactions
- Validate `currency` field on account create/update API (if REST endpoints are added)
- Ensure all transaction writes include `currency` (fallback = account currency)
- Data migration note: existing accounts/transactions without `currency` default to user's `baseCurrency`

### Day 3 — Frontend: Currency UI
- Account editor: currency dropdown (5 options)
- Transaction add/edit: show locked currency from account
- Replace all hardcoded `€` symbols in templates with the shared `formatMoney` helper
- Load `baseCurrency` from Firestore and pass to `formatMoney` everywhere

### Day 4 — Settings: FX Rates Management
- Settings section: list of manual FX rates (e.g. USD→EUR: 0.92)
- Add / edit / delete rate rows
- "Last updated" timestamp per rate
- Live preview: "With current rates, your total in EUR is …"

### Day 5 — Projections: Multi-Currency Consistency
- Projection always computed in `baseCurrency`
- If mixed currencies exist and a rate is missing: show warning banner instead of wrong total
- Net / month KPI uses the same `baseCurrency` conversion path as the chart
- Unit tests: sum-in-base-currency with manual FX rate, missing-rate warning

---

## Out of Scope (Day 1)

- Full migration of all existing Firestore data to add `currency` fields
- Automatic FX rate fetching / sync
- Tax reservation features
- Full CRUD for FX rates (Day 4)
- Projection conversion with real FX (Day 5)
