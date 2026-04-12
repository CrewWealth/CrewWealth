# CrewWealth API Documentation

## Overview

CrewWealth exposes a set of HTTP endpoints for web pages, income calculations, currency exchange rates, and a WhatsApp bot integration powered by Twilio.

Base URL (production): `https://crewwealth.onrender.com`

---

## Page Routes

These routes render HTML templates for the web application.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home / Dashboard |
| GET | `/budget` | Budget & Accounts page |
| GET | `/goals` | Financial Goals page |
| GET | `/reports` | Reports page |
| GET | `/settings` | Settings page |
| GET | `/guide` | Compact user guide page |
| GET | `/migrate-goals` | Goals Migration page |
| GET | `/login` | Login page |
| GET | `/register` | Registration page |
| GET | `/logout` | Redirects to `/login` |
| GET | `/dashboard` | Redirects to `/` |
| GET | `/income` | Redirects to `/` |

---

## Income API

### POST `/income/calculate-income`

Calculates net contract income based on salary details submitted via a form.

**Request** — `application/x-www-form-urlencoded`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `monthly_salary` | float | yes | Base monthly salary in euros |
| `contract_months` | int | yes | Duration of the contract in months |
| `position` | string | no | Job position (default: `Other`) |
| `allowances` | float | no | Monthly allowances (default: `0`) |
| `bonus` | float | no | One-time contract bonus (default: `0`) |
| `tax_rate` | float | no | Tax rate as a percentage, 0–100 (default: `19`) |

**Response** — renders `income.html` with a `results` object or an `error` message.

**Example `results` object**

```json
{
  "monthly_salary": 3000.0,
  "monthly_allowances": 200.0,
  "gross_monthly": 3200.0,
  "contract_months": 6,
  "contract_bonus": 500.0,
  "gross_contract_income": 19700.0,
  "taxes": 3743.0,
  "net_contract_income": 15957.0,
  "position": "Officer",
  "tax_rate": 19.0
}
```

---

## Currency API

### GET `/api/exchange-rates`

Returns current exchange rates for a set of maritime-relevant currencies.

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base` | string | no | Base currency code (default: `EUR`) |

**Response** — `application/json`

```json
{
  "success": true,
  "timestamp": "2026-01-24T12:00:00.000000",
  "base": "EUR",
  "rates": {
    "EUR": 1.0,
    "USD": 1.08,
    "IDR": 17500.0,
    "THB": 38.5,
    "PHP": 62.0,
    "GBP": 0.86
  }
}
```

**Error Response**

```json
{
  "success": false,
  "error": "Failed to fetch exchange rates. Please try again later."
}
```

---

## WhatsApp Bot

CrewWealth integrates with Twilio to offer a WhatsApp bot that lets crew members manage their finances from their phone.

### Webhook Setup

Configure your Twilio WhatsApp sandbox or number to send incoming messages to:

```
POST /webhook/whatsapp
```

Twilio will `POST` form-encoded data to this URL whenever a message is received.

### POST `/webhook/whatsapp`

Handles incoming WhatsApp messages and returns a TwiML response.

**Request** — sent automatically by Twilio (`application/x-www-form-urlencoded`)

| Field | Description |
|-------|-------------|
| `Body` | The text of the incoming WhatsApp message |
| `From` | The sender's phone number (e.g. `whatsapp:+31612345678`) |

#### Supported Commands

| Command | Description |
|---------|-------------|
| `link <email>` | Links the WhatsApp number to a CrewWealth account |
| `unlink` | Removes the WhatsApp link from your account |
| `balance` | Shows your total income, expenses, and current balance |
| `spent €<amount> <description>` | Logs an expense transaction |
| `earned €<amount> <description>` | Logs an income transaction |
| `help` | Lists all available commands |

#### Command Examples

**Link an account**
```
link crew@example.com
```
*Response:* `✅ Linked! Welcome to CrewWealth, Alex! Send *help* to see what I can do for you. 🚢`

**Check balance**
```
balance
```
*Response:*
```
📊 Your Balance

Income:   €5,000.00
Expenses: €1,234.56
─────────────
Balance:  €3,765.44
```

**Log an expense**
```
spent €45 dinner ashore
```
*Response:* `💸 Logged: Dinner ashore — €45.00`

**Log income**
```
earned €3000 monthly salary
```
*Response:* `💰 Logged: Monthly salary — €3000.00`

**Unlink account**
```
unlink
```
*Response:* `✅ Your WhatsApp has been unlinked from CrewWealth.`

#### Flow: First-time user

When a message is received from a phone number that has not been linked yet, the bot responds with an onboarding prompt:

```
👋 Welcome to CrewWealth!

To get started, link your account:
*link your@email.com*

Don't have an account yet? Sign up at crewwealth.app
```

---

## Error Handling

| HTTP Status | Meaning |
|-------------|---------|
| 404 | Page not found — renders `index.html` |
| 500 | Internal server error — renders `index.html` |
