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

### Day 1 — Completed ✅

| Area | Status | Notes |
|------|--------|-------|
| Firebase Auth (frontend) | ✅ Done | All pages use `onAuthStateChanged`; no hardcoded `demo` uid |
| Per-user Firestore data | ✅ Done | All reads/writes scoped to `currentUser.uid` |
| Backend token validation | ✅ Done | `/api/projection/<uid>` verifies Firebase ID token via `Authorization: Bearer` header |
| 3-year projection card (dashboard) | ✅ Done | Chart.js line chart, real calendar labels, KPI summary (net/month, 12/24/36-month balance) |
| 3-year projection (reports page) | ✅ Done | Same API-backed chart with improved UX, loading & empty states |
| README update | ✅ Done | This file |

### Architecture overview

```
Frontend (Browser)
  ├── Firebase Auth SDK  →  onAuthStateChanged  →  currentUser.uid + getIdToken()
  ├── Firestore SDK      →  direct per-user reads/writes (budget, goals, transactions, …)
  └── fetch /api/projection/<uid>  →  Authorization: Bearer <idToken>

Backend (Flask)
  ├── /api/projection/<uid>   ← require_firebase_token decorator validates token
  │     reads Firestore (accounts + transactions) and returns 36-month projection JSON
  ├── /api/exchange-rates     ← public exchange-rate proxy
  └── all other routes        ← serve HTML templates
```

## Korte gebruikershandleiding — Budgets & Accounts (nieuw)

- Bovenaan zie je nu direct de 3 belangrijkste signalen: **To budget**, **Available funds** en **Overspent warning**.
- Onder **Quick actions** staat de primaire actie (**New Payment**) en snelle budgetstart (**Add Budget**).
- Minder gebruikte acties staan onder **More actions** (Salary, Deposit, Transfer, Add Account).
- Via **Open Smart Tools** ga je direct naar import/scenario tools (Dag 3 pagina).
- In Smart Tools kun je na parse nu **Apply to Budgets & Accounts** gebruiken (met target account), waarna Budgets & Accounts automatisch verversen; gebruik **Refresh now** als handmatige fallback.

## Testinstructie

1. Open `/budget` en controleer of KPI’s bovenaan direct zichtbaar zijn.
2. Test **Quick actions**:
   - `New Payment` opent payment-modal.
   - `Add Budget` opent category/budget-flow.
3. Open **More actions** en verifieer Salary/Deposit/Transfer/Add Account.
4. Ga naar `/day3`, parse een bankbestand of loonstrook, kies een target account en klik **Apply to Budgets & Accounts**.
5. Keer terug naar `/budget`.
   - Controleer dat account- en budgetoverzichten automatisch updaten.
   - Controleer dat `Sync ready/Auto-sync active` status wijzigt na updates.
6. Verifieer dat bestaande berekeningen ongewijzigd zijn:
   - `To Budget`, `Overspent`, `Budgeted`, `Total spent` blijven consistent met transacties.
