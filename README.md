# CrewWealth

CrewWealth is an income planning tool designed for **maritime professionals** across all sectors. Whether you work on cruise ships, cargo vessels, offshore rigs, ferries, or yachts—if you have variable income and want better control over your finances—CrewWealth is for you.

## What CrewWealth does

- Estimate your **real yearly income** based on your sector, position, base salary, and variable earnings (tips, overtime, bonuses, commissions).
- Set **budget allocations** so you know exactly how much to save, invest, and spend each month.
- Track **actual spending vs. targets** to stay on course.
- See **3-year wealth projections** (36 months) based on consistent savings and investment returns.
- Run **scenario planning** (conservative / base / optimistic) to understand how income changes affect your long-term goals.

## Who it is for

CrewWealth is built for:
- Maritime officers and ratings (all sectors)
- Hotel, F&B, retail, and hospitality crew
- Offshore workers with rotation schedules
- Any seafarer with variable income who wants more financial clarity and less stress

## Project status

CrewWealth is currently in **early development / MVP stage**.  
The first version focuses on a simple web app with manual input and clear, easy-to-understand projections.

---

## Day 1 Completion Checklist

### ✅ Authentication & Security
- [x] Frontend uses Firebase Auth `currentUser` — no hardcoded UIDs anywhere
- [x] All Firestore calls are scoped to `currentUser.uid`
- [x] Flask projection API endpoint (`GET /api/projection/<uid>`) requires `Authorization: Bearer <token>` header
- [x] Flask backend verifies Firebase ID token via `firebase_admin.auth.verify_id_token()`
- [x] UID in URL is compared against the decoded token UID — mismatch returns 403
- [x] Firebase Admin SDK initialisation is graceful (logs a warning instead of crashing when credentials are absent)

### ✅ 3-Year Projection
- [x] New Flask blueprint: `app/routes/projection.py`
- [x] Projection endpoint returns 36-month data for **three scenarios**: conservative (−20 %), base, optimistic (+15 %)
- [x] Each scenario includes `year1_balance`, `year2_balance`, `year3_balance` summary fields
- [x] Month labels use real calendar dates (e.g. "May 2026") instead of "Month 1"
- [x] Projection widget on the main **Dashboard** shows base-scenario year-end balances
- [x] Full projection card on **Reports** page with:
  - [x] Loading state while data is fetched
  - [x] Scenario toggle buttons (Conservative / Base / Optimistic)
  - [x] Chart colours change per scenario
  - [x] Year-end summary metrics below the chart
  - [x] Error state when API call fails

### ✅ UI / UX
- [x] Currency-formatted tooltips and axis labels on the projection chart
- [x] X-axis shows only year-start labels to avoid crowding
- [x] Dashboard projection widget shows monthly net + saving summary text
- [x] Error and loading states for all new async operations

### ✅ Code Quality
- [x] Projection logic isolated in its own blueprint (`projection_bp`)
- [x] Token verification extracted into a reusable `require_firebase_auth` decorator
- [x] `app.firebase` is imported once at app startup (via `app/__init__.py`) to ensure a single SDK initialisation

---

## Next Steps (Day 2+)

### Short-term
- [ ] **Crew Profile page** — name, rank, vessel, contract start/end, nationality, preferred currency
- [ ] **Contract tracking** — link income/expenses to specific contracts; auto-calculate days at sea vs. on land
- [ ] **Multi-currency support** — normalise all amounts to the user's home currency using `/api/exchange-rates`
- [ ] **Income input form** (`income.html`) — connect to Firestore (currently shows a standalone calculator)
- [ ] **Expense categories** — tag transactions with maritime-specific categories (repatriation, allowances, etc.)

### Medium-term
- [ ] **Savings goals** — target amounts, target dates, automatic progress tracking
- [ ] **CSV / PDF export** for tax declarations and personal records
- [ ] **Push notifications** (PWA) for upcoming bills and contract renewals
- [ ] **Offline support** — cache latest data for use without internet connection (common on ships)

### Infrastructure
- [ ] Firestore security rules — enforce that users can only read/write their own sub-collections
- [ ] Rate limiting on Flask API endpoints
- [ ] CI/CD pipeline (GitHub Actions → Render deploy)
- [ ] GDPR / data retention policy documentation

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML + CSS (mobile-first) + Vanilla JS + Chart.js |
| Auth & Data | Firebase Auth + Cloud Firestore |
| Backend API | Python / Flask |
| Deployment | Render (gunicorn) |

## Local Development

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Provide Firebase credentials (one of):
#    a) Copy your service-account JSON to: serviceAccountKey.json
#    b) Export env var:
export FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# 4. Run
python app.py
```

The app runs at `http://localhost:5000`.  
If no Firebase credentials are present the app still starts — Firebase-dependent endpoints return 503 in production or skip token verification in debug mode.

