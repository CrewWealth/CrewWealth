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

## Quick user guide — Budgets & Accounts

- The top priority strip shows the three most important signals: **To budget**, **Available funds**, and **Overspent warning**.
- **Quick actions** keeps the main entry points close by (**New Payment** and **Add Budget**).
- Secondary actions are grouped under **More actions** (Salary, Deposit, Transfer, Add Account).
- **Open Smart Tools** takes you directly to import and scenario tooling (Day 3 page).
- In Smart Tools, use **Apply to Budgets & Accounts** after parsing and select a target account. Budget data refreshes automatically, and **Refresh now** remains available as a manual fallback.

## Live polish additions

- **PDF export**: in `Reports`, use **Export complete PDF** for a printable package that includes dashboard summary, account overview, projection, and full transaction history.
- **Fast export shortcuts**: Dashboard and Budget include direct **Export PDF** actions.
- **First-login onboarding**: new users receive a one-time in-app tour automatically.
- **Single guide entry point**: the guide is now available only through the **ℹ️ App Guide** icon next to the CrewWealth logo on the Dashboard.

## Test instructions

1. Open `/budget` and confirm the KPI strip is visible at the top.
2. Test **Quick actions**:
   - `New Payment` opens the payment modal.
   - `Add Budget` opens the category/budget flow.
3. Open **More actions** and verify Salary/Deposit/Transfer/Add Account.
4. Go to `/day3`, parse a bank file or payslip, choose a target account, and click **Apply to Budgets & Accounts**.
5. Return to `/budget`.
   - Confirm account and budget overviews update automatically.
   - Confirm `Sync ready/Auto-sync active` status changes after updates.
6. Verify that existing calculations remain unchanged:
   - `To Budget`, `Overspent`, `Budgeted`, and `Total spent` remain consistent with transactions.

## Firestore structure (transactions)

Transactions are stored as a user subcollection:

```
users/{userId}/transactions/{transactionId}
```

Like `accounts` and `fxRateHistory`, `transactions` is stored directly under `users/{userId}` and is fully manageable in Firebase Console (create, read, update, delete).

### Example save/load logic

```javascript
const userRef = db.collection('users').doc(currentUser.uid);

// Save
const txRef = userRef.collection('transactions').doc();
await txRef.set({
  type: 'payment',
  amount: 60,
  accountId: 'account123',
  date: firebase.firestore.Timestamp.fromDate(new Date()),
  createdAt: firebase.firestore.Timestamp.now()
});

// Load
const txSnapshot = await userRef
  .collection('transactions')
  .orderBy('date', 'desc')
  .get({ source: 'server' });
```

### Quick guide: where transactions live now

1. Log in to Firebase Console and open **Firestore Database**.
2. Go to `users` → `<your userId>` → **transactions**.
3. Each transaction is stored as a separate document (`transactionId`) with fields such as `type`, `amount`, `accountId`, and `date`.
4. In CrewWealth, dashboard widgets and overviews are populated only from this subcollection.
5. Legacy local “ghost” transactions are cleaned up and no longer shown when they are not present in Firestore.
