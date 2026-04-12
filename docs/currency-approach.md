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

---

## Day 2 — Advanced FX (Delivered)

### What changed

1. **Dedicated FX Center page (`/fx`)**
   - New advanced tab/page for FX operations so dashboard/main screens stay minimal.
   - Supports pair-level configuration (`auto` vs `fixed`), manual overrides, and manual on-demand refresh.

2. **Automatic/daily FX sync flow**
   - FX Center performs daily freshness check (24h) and can refresh all auto pairs on demand.
   - FX rates are stored per pair in `users/{uid}/fxRates/{BASE_QUOTE}` with:
     - `base`, `quote`, `rate`
     - `mode` (`auto` / `fixed`)
     - `source` (`auto` / `manual`)
     - `updatedAt`, `updatedAtMs`

3. **History/audit trail**
   - Every manual or auto update is appended to `users/{uid}/fxRateHistory`.
   - History is visible in FX Center.

4. **Subtle “Rate as of …” labels**
   - Dashboard and Reports now show a compact **Rate as of ...** label.
   - No noisy FX warning banners on primary screens.

5. **Fallback policy (clean UX)**
   - On API failure, app keeps last valid saved rates.
   - Short failure/sync status is shown on FX Center only.

6. **Reports/export extended with FX context**
   - Reports page now has **Export report + FX info** button.
   - Export includes report totals, selected currency, rate-as-of label, and effective FX map.

7. **FX API endpoint metadata**
   - `/api/exchange-rates` now returns source metadata and normalized base fallback for unsupported currencies.

### Day 2 quick test checklist

1. Open **FX Center** (`/fx`), confirm onboarding tip appears once.
2. Click **Refresh auto rates now**, verify status becomes success and pair list fills/updates.
3. Set a pair to **Fixed** with manual rate, save, then refresh all auto rates:
   - Fixed pair rate must remain unchanged.
4. Open Dashboard and Reports:
   - Verify subtle **Rate as of ...** appears.
   - Verify no prominent FX warning banners.
5. In Reports, click **Export report + FX info**:
   - Confirm JSON contains `fxRateAsOf` and `rates`.
6. Simulate API failure (network/dev tools) while using FX Center refresh:
   - Verify short error status on FX Center.
   - Verify previously saved rates remain available.

---

## Day 3 — Integrated Collaboration & Intelligence (Delivered)

### What changed

1. **New Smart Tools Hub (Day 3) page (`/day3`)**
   - Subtle dedicated workspace so advanced features do not clutter the dashboard.
   - Quick links added from Dashboard, FX Center and Settings.

2. **Multi-user/sharing controls**
   - Invite flow with `email`, `role` (`viewer`/`editor`/`owner`) and `visibility` scope.
   - Saved under `users/{uid}/sharedMembers/{email}`.
   - Undo support for invite add/remove.

3. **Advanced scenario forecasting (temporary activation)**
   - New API: `POST /api/day3/scenario/forecast`.
   - Supports what-if deltas (income, expense, FX shift, one-off).
   - Scenario preview can be toggled active in UI without permanent writes.

4. **Smarter transaction recognition/categorization**
   - New API: `POST /api/day3/transactions/categorize`.
   - Description + amount heuristics return category, confidence and smart tags.
   - Optional user smart-tag presets stored in `users/{uid}/smartTagRules`.

5. **Import/export integrations**
   - New API: `POST /api/day3/import/parse` for CSV and MT940 parsing.
   - New API: `POST /api/day3/export` for CSV/JSON export payload generation.
   - Preview table in Smart Tools Hub for quick validation before export.

6. **Mobile/UX polish**
   - Mobile-friendly responsive layout for all Day 3 cards.
   - Quick transaction input widget for fast mobile entry.
   - Tutorial tip, undo action stack and personalized presets (favorite currency + report preset).

### Day 3 quick test checklist

1. Open **Smart Tools Hub** (`/day3`) on desktop and mobile widths:
   - Verify layout remains readable and cards stack cleanly.
2. Add a sharing invite with role/visibility:
   - Verify invite appears in member list and can be removed.
   - Click **Undo last action** to restore.
3. Run a scenario with non-zero deltas:
   - Verify baseline/scenario/delta values are returned.
   - Toggle preview active/inactive without any permanent data mutation.
4. Enter a sample transaction description (`Uber airport`) and amount:
   - Verify suggested category + confidence + smart tags.
   - Save smart-tag preset and test undo.
5. Import a CSV file and (optionally) an MT940 sample:
   - Verify parsed rows are shown in preview.
   - Export to CSV and JSON and verify downloaded content exists.
6. Use mobile quick transaction widget:
   - Save a quick entry and verify status success.
   - Undo should remove the newly created transaction.
7. Save personal presets:
   - Favorite currency + report preset persist after page reload.

### Day 3 evaluation (current state)

- **Feature summary (present now):**
  - Multi-user/sharing validation + UI invite workflow with undo.
  - Scenario forecasting API + temporary active/inactive preview flow.
  - Smart categorization API + smart-tag preset support.
  - Import/export APIs (CSV + MT940 parse, CSV/JSON export) with UI preview.
  - Mobile polish (responsive cards + quick input) and UX tutoring extras (quick start, undo, presets).
- **Potential Day 3 expansions (optional, not blockers):**
  - More granular permission roles for sharing and deeper visibility subsets.
  - Richer scenario charting/comparison history for multiple saved previews.
  - Additional direct banking connectors beyond file-based import formats.
- **Go/no-go for Day 4:** **Go** — Day 3 scope is delivered, integrated, and testable.
