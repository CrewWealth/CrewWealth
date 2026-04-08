# CrewWealth

CrewWealth is an income planning tool designed for **maritime professionals** across all sectors. Whether you work on cruise ships, cargo vessels, offshore rigs, ferries, or yachts—if you have variable income and want better control over your finances—CrewWealth is for you.

## What CrewWealth does

- Estimate your **real yearly income** based on your sector, position, base salary, and variable earnings (tips, overtime, bonuses, commissions).
- Set **budget allocations** so you know exactly how much to save, invest, and spend each month.
- Track **actual spending vs. targets** to stay on course.
- See **3-year wealth projections** based on your current monthly net income/spending.
- Run **scenario planning** to understand how income changes affect your long-term goals.

## Who it is for

CrewWealth is built for:
- Maritime officers and ratings (all sectors)
- Hotel, F&B, retail, and hospitality crew
- Offshore workers with rotation schedules
- Any seafarer with variable income who wants more financial clarity and less stress

## Day 1 Deliverables Checklist

### ✅ Completed

- [x] **Firebase Auth end-to-end (frontend)**  
  All pages use `firebase-auth-compat.js`, check `auth.onAuthStateChanged()`, and redirect to `/login` when the user is not authenticated. Every Firestore read is scoped to `currentUser.uid`.

- [x] **Firebase ID token sent with API calls (frontend)**  
  A `getAuthHeaders()` helper calls `currentUser.getIdToken()` and attaches an `Authorization: Bearer <id_token>` header to every Flask API request (`index.html`, `reports.html`).

- [x] **Firebase Admin SDK token verification (backend)**  
  `app/auth.py` exposes a `@firebase_token_required` decorator that validates the Bearer token via `firebase_admin.auth.verify_id_token()` and injects `g.uid` for downstream use.

- [x] **UID enforcement in API endpoints (backend)**  
  The `/api/projection` endpoint is protected with `@firebase_token_required`; the verified UID is returned in the response so the frontend can confirm identity.

- [x] **3-year projection card on main dashboard**  
  `index.html` now includes a "3-Year Wealth Projection" widget backed by Chart.js and powered by the new `/api/projection` endpoint. The card shows monthly net, projected balance after 1 year, and projected balance after 3 years.

- [x] **3-year projection chart on Reports page**  
  `reports.html` already contained a 36-month Chart.js graph; the `getAuthHeaders()` helper has been added for future API calls.

- [x] **Flask backend `/api/projection` endpoint**  
  `app/routes/projection.py` implements `POST /api/projection`. Requires a valid Firebase ID token. Accepts `monthly_income`, `monthly_spending`, and optional `current_savings`; returns a 36-month projection array.

- [x] **Basic error handling**  
  Token verification returns structured `{"error": "..."}` JSON with HTTP 401. Income and projection endpoints validate inputs and return HTTP 400 on bad data.

### 🔲 Next Steps (Day 2+)

- [ ] **Persist projection inputs** – save/load `monthly_income`, `monthly_spending`, and `current_savings` from the user's Firestore profile so the projection card pre-fills on every visit.
- [ ] **Income calculation endpoint auth** – apply `@firebase_token_required` to `/income/calculate-income` once it is converted from a form-post endpoint to a proper JSON API.
- [ ] **Currency exchange rates auth** – optionally protect `/api/exchange-rates` with `@firebase_token_required` for rate-limiting per authenticated user.
- [ ] **Scenario analysis** – let users adjust savings rate, inflation, or expected return to see alternate projection curves.
- [ ] **Maritime-specific data model** – add contract periods, days-at-sea tracking, and rank/position to the Firestore user profile.
- [ ] **Mobile-first UI polish** – ensure the projection card and all widgets render correctly on small screens.
- [ ] **PDF / Excel export** – allow users to download their projection and transaction history.
- [ ] **Multi-currency normalisation** – convert all amounts to the user's home currency before running projections.
- [ ] **GDPR & security audit** – review data retention, add encrypted-at-rest notes to Firestore rules, document privacy policy.

## Project status

CrewWealth is currently in **early MVP stage**.  
Day 1 deliverables (auth end-to-end, 3-year projection card, token verification) are complete. The next phase focuses on persistence, scenario analysis, and maritime-specific features.

## Architecture overview

```
CrewWealth/
├── app.py                      # Flask entry point
├── app/
│   ├── __init__.py             # App factory, blueprint registration
│   ├── auth.py                 # Firebase token verification decorator
│   ├── firebase.py             # Firebase Admin SDK initialisation
│   ├── routes/
│   │   ├── main.py             # Page routes (dashboard, login, etc.)
│   │   ├── income.py           # POST /income/calculate-income
│   │   ├── currency.py         # GET /api/exchange-rates
│   │   └── projection.py       # POST /api/projection  ← NEW (auth required)
│   ├── models/
│   │   └── user.py
│   └── templates/              # Jinja2 HTML templates
│       ├── index.html          # Main dashboard (3-year projection card added)
│       ├── reports.html        # Reports + 36-month Chart.js graph
│       ├── budget.html
│       ├── goals.html
│       ├── settings.html
│       ├── login.html
│       └── register.html
├── config/config.py            # Flask config (dev/prod/test)
├── requirements.txt
├── docs/API.md                 # API documentation
└── README.md
```

### How the pieces communicate

1. **User opens any page** → Firebase Auth SDK checks auth state; unauthenticated users are redirected to `/login`.
2. **Firestore reads** → frontend uses `currentUser.uid` directly; no Flask backend involved.
3. **Flask API calls** → frontend calls `getAuthHeaders()` to fetch a fresh Firebase ID token, then includes it as `Authorization: Bearer <token>` in every `fetch()` call to Flask endpoints.
4. **Flask validates token** → `@firebase_token_required` verifies the token with Firebase Admin SDK; sets `g.uid`; returns HTTP 401 on failure.
5. **Projection calculation** → `/api/projection` returns 36 months of projected balances, which Chart.js renders in the dashboard widget.


