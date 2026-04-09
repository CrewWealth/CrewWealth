# CrewWealth

CrewWealth is an income planning tool designed for **maritime professionals** across all sectors. Whether you work on cruise ships, cargo vessels, offshore rigs, ferries, or yachts—if you have variable income and want better control over your finances—CrewWealth is for you.

## What CrewWealth does

- Estimate your **real yearly income** based on your sector, position, base salary, and variable earnings (tips, overtime, bonuses, commissions).
- Set **budget allocations** so you know exactly how much to save, invest, and spend each month.
- Track **actual spending vs. targets** to stay on course.
- See **3-year (36-month) wealth projections** based on your real transaction history, starting from your current account balance.
- Run **scenario planning** to understand how income changes affect your long-term goals.

## Who it is for

CrewWealth is built for:
- Maritime officers and ratings (all sectors)
- Hotel, F&B, retail, and hospitality crew
- Offshore workers with rotation schedules
- Any seafarer with variable income who wants more financial clarity and less stress

## Project status

CrewWealth is currently in **active development**.

### Multi-currency support (in progress) 🌍

CrewWealth is being extended with full multi-currency support — essential for maritime professionals who earn in one currency and spend in another.

**Supported currencies (MVP):** EUR, USD, GBP, PHP, IDR

**Approach:**
- Every user has a **base currency** (default EUR), set in Settings → Currency.
- Dashboard totals and projections are always shown in the base currency.
- Account and transaction lists show the original currency and amount.
- FX rates are entered manually for MVP (no external sync required).
- If a required FX rate is missing, a warning is shown — totals are never silently wrong.

See [`docs/currency-approach.md`](docs/currency-approach.md) for the full technical specification and implementation plan.

### Day 1 — Completed ✅

| Area | Status | Notes |
|------|--------|-------|
| Firebase Auth (frontend) | ✅ Done | All pages use `onAuthStateChanged`; no hardcoded `demo` uid |
| Per-user Firestore data | ✅ Done | All reads/writes scoped to `currentUser.uid` |
| Backend token validation | ✅ Done | `/api/projection/<uid>` verifies Firebase ID token via `Authorization: Bearer` header |
| 3-year projection card (dashboard) | ✅ Done | Chart.js line chart, real calendar labels, KPI summary (net/month, 12/24/36-month balance) |
| 3-year projection (reports page) | ✅ Done | Same API-backed chart with improved UX, loading & empty states |
| Multi-currency scaffolding (Day 1) | ✅ Done | Supported currencies constants, baseCurrency field, formatMoney helper, docs |
| README update | ✅ Done | This file |

### Architecture overview

```
Frontend (Browser)
  ├── Firebase Auth SDK  →  onAuthStateChanged  →  currentUser.uid + getIdToken()
  ├── Firestore SDK      →  direct per-user reads/writes (budget, goals, transactions, …)
  ├── /static/js/currency.js  →  SUPPORTED_CURRENCIES, formatMoney(amount, currency, locale)
  └── fetch /api/projection/<uid>  →  Authorization: Bearer <idToken>

Backend (Flask)
  ├── /api/projection/<uid>   ← require_firebase_token; returns baseCurrency in response
  ├── /api/currencies         ← list of supported currencies + metadata
  ├── /api/exchange-rates     ← external exchange-rate proxy (supported currencies only)
  ├── /api/fx-rates/<uid>     ← manual FX rates placeholder (full CRUD in Day 4)
  └── all other routes        ← serve HTML templates
```

