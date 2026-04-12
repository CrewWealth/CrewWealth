(function () {
    const GUIDE_STATE_KEY = 'cw_app_guide_state_v1';
    const HIGHLIGHT_CLASS = 'cw-guide-highlight';
    const OVERLAY_ID = 'crewwealthTourOverlay';
    const STEPS = [
        {
            page: 'dashboard',
            url: '/',
            selector: '#monthOverviewCard',
            title: 'Dashboard: your financial command center',
            text: 'Use this overview to quickly check net worth, monthly direction, and account health before every voyage or contract cycle.'
        },
        {
            page: 'dashboard',
            url: '/',
            selector: '#recentTransactionsCard',
            title: 'Dashboard: track activity and clean records',
            text: 'Review recent transactions here. For corrections, open Budget & Accounts to edit or delete items so reports and projections stay accurate.'
        },
        {
            page: 'dashboard',
            url: '/',
            selector: '#projectionWidget',
            title: 'Dashboard: projection and planning',
            text: 'Use the 36-month projection to test whether your current monthly surplus supports your shore-leave plans, savings goals, and emergency reserves.'
        },
        {
            page: 'budget',
            url: '/budget',
            selector: '.priority-strip',
            title: 'Budget & Accounts: first priorities',
            text: 'Start with To budget, Available funds, and Overspent warning. This tells you where to allocate incoming salary and where to reduce spending.'
        },
        {
            page: 'budget',
            url: '/budget',
            selector: '.quick-actions-panel',
            title: 'Budget & Accounts: add and update data fast',
            text: 'Use Quick actions to add payment, salary, deposit, transfer, budget category, or account. Open transactions to edit/delete entries when mistakes happen.'
        },
        {
            page: 'budget',
            url: '/budget',
            selector: '.categories-section',
            title: 'Budget & Accounts: monitor categories and history',
            text: 'Track category spending versus budget, review recent transactions, and keep recurring bills updated so your monthly plan stays realistic offshore and onshore.'
        },
        {
            page: 'budget',
            url: '/budget',
            selector: '.top-bar-right .back-btn[href=\"/reports?export=pdf\"]',
            title: 'Budget & Accounts: export',
            text: 'Use Export PDF to generate a shareable snapshot for personal audits, financial advisors, or family planning reviews.'
        },
        {
            page: 'goals',
            url: '/goals',
            selector: '#goalForm',
            title: 'Goals: create clear targets',
            text: 'Create goals with target amount, current amount, monthly contribution, and deadline to plan milestones like home deposit, emergency fund, or rotation savings.'
        },
        {
            page: 'goals',
            url: '/goals',
            selector: '.stats-sidebar',
            title: 'Goals: check progress and adjust',
            text: 'Use the Summary panel to decide when to increase contributions after high-income months or rebalance when expenses rise.'
        },
        {
            page: 'goals',
            url: '/goals',
            selector: '#goalsList',
            title: 'Goals: maintain your plan',
            text: 'Use your goal cards to review progress and delete goals that are no longer relevant. Keep only active targets to stay focused.'
        },
        {
            page: 'reports',
            url: '/reports',
            selector: '.reports-grid',
            title: 'Reports: decision-ready insights',
            text: 'Read net worth, income, and spending summaries here before making larger financial decisions such as investments or contract transitions.'
        },
        {
            page: 'reports',
            url: '/reports',
            selector: '#exportCompletePdfButton',
            title: 'Reports: full PDF export',
            text: 'Click Export complete PDF for a complete package (summary, projection, and transaction history) that you can save, print, or share.'
        },
        {
            page: 'reports',
            url: '/reports',
            selector: '.card',
            title: 'Reports: projection chart',
            text: 'Use the 3-year projection card to compare expected balances over time and decide whether your current saving pace is sufficient.'
        },
        {
            page: 'fx',
            url: '/fx',
            selector: '#fxSyncCard',
            title: 'FX Center: keep rates fresh',
            text: 'Run auto refresh when exchange markets move quickly. This helps multi-currency seafarers keep balances and reports aligned with current rates.'
        },
        {
            page: 'fx',
            url: '/fx',
            selector: '#pairConfigCard',
            title: 'FX Center: configure currency pairs',
            text: 'Set pair mode to Auto for live updates or Fixed for locked planning scenarios. Save pair settings before generating comparisons or forecasts.'
        },
        {
            page: 'fx',
            url: '/fx',
            selector: '#fxHistoryCard',
            title: 'FX Center: verify history and audit trail',
            text: 'Use FX history to confirm who changed rates and when. This is useful when validating export totals and trend differences over time.'
        },
        {
            page: 'smart-tools',
            url: '/day3',
            selector: '#smartToolsHero',
            title: 'Smart Tools Hub: automation workspace',
            text: 'This page combines advanced features so you can reduce manual work and quickly process real-world finance admin tasks.'
        },
        {
            page: 'smart-tools',
            url: '/day3',
            selector: '#importCard',
            title: 'Smart Tools Hub: import, apply, and export',
            text: 'Parse bank or payslip files, preview rows, then click Apply to Budgets & Accounts to write data. Use CSV/JSON exports for accountant workflows.'
        },
        {
            page: 'smart-tools',
            url: '/day3',
            selector: '#scenarioCard',
            title: 'Smart Tools Hub: scenario planning',
            text: 'Run what-if scenarios (income, expenses, FX shifts, one-offs) before signing a new contract or changing monthly allocations.'
        },
        {
            page: 'settings',
            url: '/settings',
            selector: '#currencySettingsSection',
            title: 'Settings: personalization and defaults',
            text: 'Set your default currency and app preferences here so all sections present values in your preferred operating currency.'
        },
        {
            page: 'settings',
            url: '/settings',
            selector: '#manualFxSettingsSection',
            title: 'Settings: manual FX control',
            text: 'Add manual FX overrides when needed. Use this when public rates are delayed or when you need stable planning assumptions.'
        },
        {
            page: 'dashboard',
            url: '/',
            selector: '#tourInfoButton',
            title: 'Guide access, pause, and resume',
            text: 'You can pause this guide anytime and continue later. Use the top-right ℹ️ App Guide icon on Dashboard to reopen and review features whenever needed.'
        }
    ];

    let highlightedEl = null;
    let currentPage = 'dashboard';
    let stepIndex = 0;

    function readState() {
        if (!window.localStorage) return { status: 'idle', stepIndex: 0 };
        try {
            const raw = window.localStorage.getItem(GUIDE_STATE_KEY);
            if (!raw) return { status: 'idle', stepIndex: 0 };
            const parsed = JSON.parse(raw);
            return {
                status: parsed.status || 'idle',
                stepIndex: Number.isInteger(parsed.stepIndex) ? parsed.stepIndex : 0
            };
        } catch (_) {
            return { status: 'idle', stepIndex: 0 };
        }
    }

    function writeState(next) {
        if (!window.localStorage) return;
        window.localStorage.setItem(GUIDE_STATE_KEY, JSON.stringify({
            status: next.status,
            stepIndex: next.stepIndex,
            updatedAt: Date.now()
        }));
    }

    function ensureStyles() {
        if (document.getElementById('cwGuideStyles')) return;
        const style = document.createElement('style');
        style.id = 'cwGuideStyles';
        style.textContent = `
            .tour-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.42); z-index: 2400; display: none; align-items: center; justify-content: center; padding: 16px; }
            .tour-overlay.active { display: flex; }
            .tour-modal { width: min(640px, 100%); background: #fff; border-radius: 14px; border: 1px solid #dbe3ef; box-shadow: 0 20px 70px rgba(2, 6, 23, 0.22); padding: 18px; }
            .tour-title { font-size: 20px; font-weight: 700; margin-bottom: 10px; color: #0f172a; }
            .tour-text { font-size: 14px; line-height: 1.6; color: #334155; margin-bottom: 12px; }
            .tour-progress { font-size: 12px; color: #64748b; margin-bottom: 12px; }
            .tour-actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
            .tour-btn { border-radius: 10px; border: 1px solid #cbd5e1; background: #fff; color: #0f172a; padding: 8px 12px; font-size: 13px; font-weight: 600; cursor: pointer; }
            .tour-btn.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
            .cw-guide-highlight { position: relative; z-index: 2000; box-shadow: 0 0 0 3px #32b8c6; border-radius: 10px; }
        `;
        document.head.appendChild(style);
    }

    function ensureOverlay() {
        ensureStyles();
        let overlay = document.getElementById(OVERLAY_ID);
        if (overlay) return overlay;
        overlay = document.createElement('div');
        overlay.id = OVERLAY_ID;
        overlay.className = 'tour-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-labelledby', 'tourTitle');
        overlay.setAttribute('aria-describedby', 'tourText');
        overlay.innerHTML = `
            <div class="tour-modal">
                <div class="tour-title" id="tourTitle">CrewWealth App Guide</div>
                <div class="tour-text" id="tourText"></div>
                <div class="tour-progress" id="tourProgress"></div>
                <div class="tour-actions">
                    <div style="display:flex; gap:8px;">
                        <button type="button" class="tour-btn" id="tourBackBtn">← Back</button>
                        <button type="button" class="tour-btn primary" id="tourNextBtn">Next →</button>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button type="button" class="tour-btn" id="tourPauseBtn">Pause</button>
                        <button type="button" class="tour-btn" id="tourCloseBtn">Close guide</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        document.getElementById('tourBackBtn').addEventListener('click', () => previousTourStep());
        document.getElementById('tourNextBtn').addEventListener('click', () => nextTourStep());
        document.getElementById('tourPauseBtn').addEventListener('click', () => pauseCrewwealthTour());
        document.getElementById('tourCloseBtn').addEventListener('click', () => skipTour());
        return overlay;
    }

    function clearHighlight() {
        if (highlightedEl) {
            highlightedEl.classList.remove(HIGHLIGHT_CLASS);
            highlightedEl = null;
        }
    }

    function closeOverlay() {
        const overlay = ensureOverlay();
        overlay.classList.remove('active');
        clearHighlight();
    }

    function markGuideCompleted() {
        writeState({ status: 'completed', stepIndex: 0 });
        closeOverlay();
        if (typeof window.onCrewwealthTourCompleted === 'function') {
            Promise.resolve(window.onCrewwealthTourCompleted()).catch(() => {});
        }
    }

    function showTourStep(index) {
        const bounded = Math.max(0, Math.min(index, STEPS.length - 1));
        stepIndex = bounded;
        const step = STEPS[stepIndex];
        writeState({ status: 'active', stepIndex });

        if (step.page !== currentPage) {
            window.location.href = step.url;
            return;
        }

        const overlay = ensureOverlay();
        overlay.classList.add('active');
        document.getElementById('tourTitle').textContent = step.title;
        document.getElementById('tourText').textContent = step.text;
        document.getElementById('tourProgress').textContent = `Step ${stepIndex + 1} of ${STEPS.length}`;

        const backBtn = document.getElementById('tourBackBtn');
        const nextBtn = document.getElementById('tourNextBtn');
        backBtn.disabled = stepIndex === 0;
        nextBtn.textContent = stepIndex >= STEPS.length - 1 ? 'Finish' : 'Next →';

        clearHighlight();
        const target = step.selector ? document.querySelector(step.selector) : null;
        if (target) {
            highlightedEl = target;
            highlightedEl.classList.add(HIGHLIGHT_CLASS);
            highlightedEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function nextTourStep() {
        if (stepIndex >= STEPS.length - 1) {
            markGuideCompleted();
            return;
        }
        showTourStep(stepIndex + 1);
    }

    function previousTourStep() {
        if (stepIndex <= 0) return;
        showTourStep(stepIndex - 1);
    }

    function pauseCrewwealthTour() {
        writeState({ status: 'paused', stepIndex });
        closeOverlay();
    }

    function skipTour() {
        markGuideCompleted();
    }

    function openCrewwealthTour(forceStart = false) {
        const state = readState();
        const initialIndex = forceStart ? 0 : (state.status === 'paused' || state.status === 'active' ? state.stepIndex : 0);
        showTourStep(initialIndex);
    }

    function initGuide() {
        currentPage = document.body?.dataset?.guidePage || 'dashboard';
        ensureOverlay();
        const state = readState();
        if (state.status === 'active') {
            const step = STEPS[Math.max(0, Math.min(state.stepIndex, STEPS.length - 1))];
            if (step && step.page === currentPage) {
                showTourStep(state.stepIndex);
            }
        }
    }

    window.CREWWEALTH_GUIDE_STEPS = STEPS;
    window.showTourStep = showTourStep;
    window.openCrewwealthTour = openCrewwealthTour;
    window.nextTourStep = nextTourStep;
    window.previousTourStep = previousTourStep;
    window.pauseCrewwealthTour = pauseCrewwealthTour;
    window.skipTour = skipTour;
    window.addEventListener('DOMContentLoaded', initGuide);
})();
