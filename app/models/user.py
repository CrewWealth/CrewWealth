"""
user.py — CrewWealth user and account model field documentation.

CrewWealth uses Firebase Firestore as its database; there is no ORM.
This module documents the expected shape of Firestore documents so that
field names, types, and defaults are defined in one place.

Firestore document paths
------------------------
users/{uid}
    fullName        : str
    email           : str
    baseCurrency    : str  – ISO 4217 (e.g. "EUR").  Default: DEFAULT_BASE_CURRENCY.
                            This is the currency used for all dashboard totals and
                            wealth projections.  Set by the user in Settings.
    locale          : str  – BCP 47 locale string (e.g. "en-NL").  Optional.
    settings        : dict
        currency    : str  – legacy alias kept for backward-compat; mirrors baseCurrency.
        language    : str  – e.g. "en"
        theme       : str  – "light" | "dark"
        monthlySavings : float | None  – manual monthly savings override for projection
    createdAt       : Timestamp
    updatedAt       : Timestamp

users/{uid}/accounts/{accountId}
    name            : str
    balance         : float  – current balance in the account's own currency
    currency        : str    – ISO 4217.  Default: user.baseCurrency at creation time.
    offBudget       : bool   – True → included in wealth projection starting balance
    icon            : str    – emoji
    createdAt       : Timestamp

users/{uid}/transactions/{txId}
    type            : str    – "income" | "expense" | "transfer" | "deposit"
                               | "payment" | "salary"
    amount          : float  – absolute value in the transaction's own currency
    currency        : str    – ISO 4217.  Default: account.currency.
    accountId       : str
    toAccountId     : str | None  – only for "transfer" type
    categoryId      : str | None
    date            : Timestamp
    note            : str | None
    createdAt       : Timestamp

users/{uid}/fxRates/{rateId}   (placeholder – full CRUD in Day 4)
    base            : str    – from-currency ISO 4217
    quote           : str    – to-currency ISO 4217 (typically user.baseCurrency)
    rate            : float  – 1 unit of base = rate units of quote
    updatedAt       : Timestamp
    source          : str    – "manual" (MVP); future: "automatic"
"""

from config.currencies import (  # noqa: F401  – re-export for convenience
    SUPPORTED_CURRENCIES,
    DEFAULT_BASE_CURRENCY,
    CURRENCY_META,
    is_supported_currency,
)

# Firestore field names — use these constants to avoid typos across the codebase.
FIELD_BASE_CURRENCY = 'baseCurrency'
FIELD_ACCOUNT_CURRENCY = 'currency'
FIELD_TX_CURRENCY = 'currency'
