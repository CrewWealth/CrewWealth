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
const DEFAULT_FX_FALLBACK_RATE = 1.0;
const PUBLIC_FX_API_BASE_URL = 'https://open.er-api.com/v6/latest/';

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

function buildFxPairKey(fromCurrency, toCurrency) {
    const from = (fromCurrency || '').toUpperCase();
    const to = (toCurrency || '').toUpperCase();
    return `${from}_${to}`;
}

function buildPublicFxRateMap(baseCurrency, apiRates, currencies) {
    const base = (baseCurrency || DEFAULT_CURRENCY).toUpperCase();
    const allowed = Array.isArray(currencies) && currencies.length
        ? currencies.map(code => String(code || '').toUpperCase())
        : SUPPORTED_CURRENCIES;
    const rates = {};
    const normalizedRates = apiRates || {};

    allowed.forEach(targetCode => {
        if (!targetCode) return;
        if (targetCode === base) {
            rates[buildFxPairKey(base, targetCode)] = 1;
            return;
        }
        const rawRate = Number(normalizedRates[targetCode]);
        if (!isFinite(rawRate) || rawRate <= 0) return;
        rates[buildFxPairKey(base, targetCode)] = rawRate;
        rates[buildFxPairKey(targetCode, base)] = 1 / rawRate;
    });

    return rates;
}

async function fetchPublicFxRates(baseCurrency, currencies) {
    const base = (baseCurrency || DEFAULT_CURRENCY).toUpperCase();
    if (typeof fetch !== 'function') return {};

    try {
        const response = await fetch(`${PUBLIC_FX_API_BASE_URL}${encodeURIComponent(base)}`);
        if (!response.ok) return {};
        const payload = await response.json();
        const apiRates = payload?.rates;
        if (!apiRates || typeof apiRates !== 'object') return {};
        return buildPublicFxRateMap(base, apiRates, currencies);
    } catch (_) {
        return {};
    }
}

function resolveFxRate(fromCurrency, toCurrency, fxRates) {
    const from = (fromCurrency || DEFAULT_CURRENCY).toUpperCase();
    const to = (toCurrency || DEFAULT_CURRENCY).toUpperCase();
    if (from === to) return 1;

    const rates = fxRates || {};
    const direct = rates[buildFxPairKey(from, to)];
    if (typeof direct === 'number' && isFinite(direct) && direct > 0) {
        return direct;
    }

    const inverse = rates[buildFxPairKey(to, from)];
    if (typeof inverse === 'number' && isFinite(inverse) && inverse > 0) {
        return 1 / inverse;
    }

    // Fallback: try to find an indirect conversion path through known FX pairs.
    // Example: EUR->GBP via EUR->USD and USD->GBP.
    const adjacency = new Map();
    Object.entries(rates).forEach(([pairKey, rawRate]) => {
        const rate = Number(rawRate);
        if (!isFinite(rate) || rate <= 0) return;
        const parts = String(pairKey).split('_');
        if (parts.length !== 2) return;
        const [base, quote] = parts.map(code => String(code || '').toUpperCase());
        if (!base || !quote) return;
        if (!adjacency.has(base)) adjacency.set(base, []);
        if (!adjacency.has(quote)) adjacency.set(quote, []);
        adjacency.get(base).push({ to: quote, rate });
        adjacency.get(quote).push({ to: base, rate: 1 / rate });
    });

    if (!adjacency.has(from) || !adjacency.has(to)) return null;

    const queue = [{ currency: from, rate: 1 }];
    const visited = new Set([from]);

    while (queue.length > 0) {
        const current = queue.shift();
        if (!current || !adjacency.has(current.currency)) continue;
        const neighbors = adjacency.get(current.currency) || [];
        for (const neighbor of neighbors) {
            if (!neighbor || visited.has(neighbor.to)) continue;
            const nextRate = current.rate * neighbor.rate;
            if (neighbor.to === to) return nextRate;
            visited.add(neighbor.to);
            queue.push({ currency: neighbor.to, rate: nextRate });
        }
    }

    return DEFAULT_FX_FALLBACK_RATE;
}

function convertMoney(amount, fromCurrency, toCurrency, fxRates) {
    const value = typeof amount === 'number' && isFinite(amount) ? amount : 0;
    const rate = resolveFxRate(fromCurrency, toCurrency, fxRates);
    return value * rate;
}

// ---------------------------------------------------------------------------
// Export for Node/Jest environments (tree-shaken in browser builds).
// ---------------------------------------------------------------------------
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SUPPORTED_CURRENCIES,
        DEFAULT_CURRENCY,
        DEFAULT_FX_FALLBACK_RATE,
        CURRENCY_META,
        formatMoney,
        getCurrencySymbol,
        isValidCurrency,
        buildFxPairKey,
        buildPublicFxRateMap,
        fetchPublicFxRates,
        resolveFxRate,
        convertMoney
    };
}
