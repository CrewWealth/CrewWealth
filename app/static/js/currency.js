/**
 * currency.js — CrewWealth shared currency constants and helpers
 *
 * Include this file in pages that need currency formatting:
 *   <script src="/static/js/currency.js"></script>
 *
 * Then use:
 *   formatMoney(1234.5, 'USD')          // "$1,234.50"
 *   formatMoney(12000, 'PHP', 'fil-PH') // "₱12,000.00"
 *   SUPPORTED_CURRENCIES                // [{code, symbol, name, locale}, …]
 */

'use strict';

/**
 * The five currencies supported in the CrewWealth MVP (ISO 4217).
 * This is the single source-of-truth for the frontend.
 * Backend equivalent: config/currencies.py → SUPPORTED_CURRENCIES
 */
const SUPPORTED_CURRENCIES = [
    { code: 'EUR', symbol: '€',  name: 'Euro',               locale: 'nl-NL' },
    { code: 'USD', symbol: '$',  name: 'US Dollar',           locale: 'en-US' },
    { code: 'GBP', symbol: '£',  name: 'British Pound',       locale: 'en-GB' },
    { code: 'PHP', symbol: '₱',  name: 'Philippine Peso',     locale: 'fil-PH' },
    { code: 'IDR', symbol: 'Rp', name: 'Indonesian Rupiah',   locale: 'id-ID' },
];

/** Lookup map: code → currency metadata */
const CURRENCY_MAP = Object.fromEntries(
    SUPPORTED_CURRENCIES.map(c => [c.code, c])
);

/**
 * Default base currency applied when no user preference has been loaded yet.
 * Always overridden by the authenticated user's `baseCurrency` field.
 */
const DEFAULT_BASE_CURRENCY = 'EUR';

/**
 * Format a numeric amount as a localised currency string using
 * the browser's built-in Intl.NumberFormat API.
 *
 * @param {number} amount   - The numeric value to format.
 * @param {string} currency - ISO 4217 code (e.g. 'USD', 'PHP').
 *                            Falls back to DEFAULT_BASE_CURRENCY if unknown.
 * @param {string} [locale] - BCP 47 locale string (e.g. 'en-US').
 *                            Defaults to the locale registered for the currency.
 * @returns {string}        - Formatted string, e.g. "$1,234.50" or "₱12,000.00".
 *
 * @example
 * formatMoney(1500, 'USD')           // "$1,500.00"
 * formatMoney(12000, 'PHP')          // "₱12,000.00"
 * formatMoney(15000000, 'IDR')       // "Rp15,000,000"
 */
function formatMoney(amount, currency, locale) {
    const safeAmount = typeof amount === 'number' && isFinite(amount) ? amount : 0;
    const safeCode = (CURRENCY_MAP[currency] ? currency : DEFAULT_BASE_CURRENCY);
    const safeLocale = locale || CURRENCY_MAP[safeCode]?.locale || 'en-US';

    try {
        return new Intl.NumberFormat(safeLocale, {
            style: 'currency',
            currency: safeCode,
            minimumFractionDigits: safeCode === 'IDR' ? 0 : 2,
            maximumFractionDigits: safeCode === 'IDR' ? 0 : 2,
        }).format(safeAmount);
    } catch (_) {
        // Fallback: manual symbol + fixed decimals (should never happen for our 5 currencies)
        const meta = CURRENCY_MAP[safeCode] || CURRENCY_MAP[DEFAULT_BASE_CURRENCY];
        const decimals = safeCode === 'IDR' ? 0 : 2;
        return meta.symbol + safeAmount.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
}

/**
 * Return true if `code` is one of the five supported ISO 4217 codes.
 *
 * @param {string} code
 * @returns {boolean}
 */
function isSupportedCurrency(code) {
    return Object.prototype.hasOwnProperty.call(CURRENCY_MAP, code);
}

// Expose on window for non-module scripts
if (typeof window !== 'undefined') {
    window.SUPPORTED_CURRENCIES = SUPPORTED_CURRENCIES;
    window.CURRENCY_MAP = CURRENCY_MAP;
    window.DEFAULT_BASE_CURRENCY = DEFAULT_BASE_CURRENCY;
    window.formatMoney = formatMoney;
    window.isSupportedCurrency = isSupportedCurrency;
}
