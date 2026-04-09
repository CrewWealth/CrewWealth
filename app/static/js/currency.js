/**
 * currency.js — CrewWealth shared currency constants and formatting helpers.
 *
 * Import/include this file before any page-level scripts that need to
 * display or validate monetary values.
 *
 * Usage:
 *   const label = formatMoney(1234.5, 'USD');        // "$1,234.50"
 *   const label = formatMoney(12000, 'IDR', 'id-ID'); // "Rp12.000"
 *   if (!SUPPORTED_CURRENCIES.includes(code)) { ... }
 */

'use strict';

// ---------------------------------------------------------------------------
// Supported currencies (ISO 4217).  Keep in sync with backend SUPPORTED_CURRENCIES.
// ---------------------------------------------------------------------------
const SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP', 'PHP', 'IDR'];

// Default base currency for new users.
const DEFAULT_CURRENCY = 'EUR';

// ---------------------------------------------------------------------------
// Per-currency display metadata (fallback for environments without Intl).
// ---------------------------------------------------------------------------
const CURRENCY_META = {
    EUR: { symbol: '€', decimals: 2, locale: 'en-EU' },
    USD: { symbol: '$', decimals: 2, locale: 'en-US' },
    GBP: { symbol: '£', decimals: 2, locale: 'en-GB' },
    PHP: { symbol: '₱', decimals: 2, locale: 'en-PH' },
    IDR: { symbol: 'Rp', decimals: 0, locale: 'id-ID' },
};

// ---------------------------------------------------------------------------
// formatMoney — primary formatting function.
//
// Params:
//   amount   {number}  The numeric value to format.
//   currency {string}  ISO 4217 currency code (defaults to DEFAULT_CURRENCY).
//   locale   {string}  BCP 47 locale tag (optional; uses currency default).
//
// Returns a localised string such as "€1,234.56" or "Rp12.000".
// Falls back to a simple symbol+fixed-decimal string when Intl is unavailable.
// ---------------------------------------------------------------------------
function formatMoney(amount, currency, locale) {
    const code = (currency || DEFAULT_CURRENCY).toUpperCase();
    const meta = CURRENCY_META[code] || { symbol: code, decimals: 2, locale: 'en-US' };
    const resolvedLocale = locale || meta.locale;
    const value = typeof amount === 'number' && isFinite(amount) ? amount : 0;

    if (typeof Intl !== 'undefined' && Intl.NumberFormat) {
        try {
            return new Intl.NumberFormat(resolvedLocale, {
                style: 'currency',
                currency: code,
                minimumFractionDigits: meta.decimals,
                maximumFractionDigits: meta.decimals,
            }).format(value);
        } catch (_) {
            // Intl present but currency code unrecognised — fall through to fallback.
        }
    }

    // Simple fallback: manual symbol + toFixed
    const formatted = value.toFixed(meta.decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return meta.symbol + formatted;
}

// ---------------------------------------------------------------------------
// getCurrencySymbol — returns just the symbol for a given code.
// Useful for populating <span class="currency-symbol"> elements.
// ---------------------------------------------------------------------------
function getCurrencySymbol(currency) {
    const code = (currency || DEFAULT_CURRENCY).toUpperCase();
    const meta = CURRENCY_META[code];
    if (meta) return meta.symbol;
    // Try Intl to extract the symbol for an unsupported code.
    if (typeof Intl !== 'undefined' && Intl.NumberFormat) {
        try {
            const parts = new Intl.NumberFormat('en-US', { style: 'currency', currency: code })
                .formatToParts(0);
            const sym = parts.find(p => p.type === 'currency');
            if (sym) return sym.value;
        } catch (_) { /* ignore */ }
    }
    return code;
}

// ---------------------------------------------------------------------------
// isValidCurrency — returns true if the code is in SUPPORTED_CURRENCIES.
// ---------------------------------------------------------------------------
function isValidCurrency(code) {
    return typeof code === 'string' && SUPPORTED_CURRENCIES.includes(code.toUpperCase());
}

// ---------------------------------------------------------------------------
// Export for Node/Jest environments (tree-shaken in browser builds).
// ---------------------------------------------------------------------------
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SUPPORTED_CURRENCIES, DEFAULT_CURRENCY, CURRENCY_META, formatMoney, getCurrencySymbol, isValidCurrency };
}
