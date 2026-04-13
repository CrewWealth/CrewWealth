import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_TEMPLATE = ROOT / "app" / "templates" / "index.html"
REPORTS_TEMPLATE = ROOT / "app" / "templates" / "reports.html"
REGISTER_TEMPLATE = ROOT / "app" / "templates" / "register.html"
SUPPORT_TEMPLATE = ROOT / "app" / "templates" / "support.html"
GOALS_TEMPLATE = ROOT / "app" / "templates" / "goals.html"
BUDGET_TEMPLATE = ROOT / "app" / "templates" / "budget.html"
SETTINGS_TEMPLATE = ROOT / "app" / "templates" / "settings.html"
FX_TEMPLATE = ROOT / "app" / "templates" / "fx.html"
DAY3_TEMPLATE = ROOT / "app" / "templates" / "day3.html"
MAIN_ROUTES = ROOT / "app" / "routes" / "main.py"
APP_GUIDE_JS = ROOT / "app" / "static" / "js" / "app-guide.js"


class TestPolishTemplateFeatures(unittest.TestCase):
    def test_reports_has_pdf_export_button_and_function(self):
        content = REPORTS_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("Export complete PDF", content)
        self.assertIn("async function exportReportsToPdf()", content)
        self.assertIn("window.exportReportsToPdf = exportReportsToPdf;", content)
        self.assertIn("jspdf.umd.min.js", content)
        self.assertIn("doc.output('blob')", content)
        self.assertIn("function downloadBlobFile(blob, fileName)", content)
        self.assertIn(
            "Could not download PDF. Please retry. If it keeps failing, refresh the page and try again.",
            content
        )
        self.assertNotIn("window.open('', '_blank'", content)
        self.assertNotIn("Popup blocked. Please allow popups for PDF export.", content)

    def test_dashboard_has_onboarding_tour_button_and_hooks(self):
        content = INDEX_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("id=\"tourInfoButton\"", content)
        self.assertIn("/static/js/app-guide.js", content)
        self.assertIn("async function maybeStartOnboardingTour()", content)
        self.assertIn("onclick=\"openCrewwealthTour()\"", content)
        self.assertNotIn("📘 Guide", content)

    def test_app_guide_covers_all_main_sections_and_navigation(self):
        content = APP_GUIDE_JS.read_text(encoding="utf-8")
        self.assertIn("page: 'dashboard'", content)
        self.assertIn("page: 'budget'", content)
        self.assertIn("page: 'goals'", content)
        self.assertIn("page: 'reports'", content)
        self.assertIn("page: 'fx'", content)
        self.assertIn("page: 'smart-tools'", content)
        self.assertIn("page: 'settings'", content)
        self.assertIn("tourPauseBtn", content)
        self.assertIn("window.location.href = step.url;", content)

    def test_registration_sets_onboarding_default_preference(self):
        content = REGISTER_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("preferences: {", content)
        self.assertIn("onboardingCompleted: false", content)

    def test_guide_route_removed(self):
        content = MAIN_ROUTES.read_text(encoding="utf-8")
        self.assertNotIn("@main_bp.route('/guide')", content)
        self.assertNotIn("guide.html", content)

    def test_support_and_legal_routes_exist(self):
        content = MAIN_ROUTES.read_text(encoding="utf-8")
        self.assertIn("@main_bp.route('/support')", content)
        self.assertIn("@main_bp.route('/privacy')", content)
        self.assertIn("@main_bp.route('/terms')", content)

    def test_support_page_has_contact_and_legal_links(self):
        content = SUPPORT_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("support@crewwealth.app", content)
        self.assertIn("href=\"/privacy\"", content)
        self.assertIn("href=\"/terms\"", content)

    def test_dashboard_has_support_link_in_navigation(self):
        content = INDEX_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("id=\"navSupportLink\"", content)
        self.assertIn("href=\"/support\"", content)

    def test_help_legal_links_are_only_in_support_and_dashboard_navigation(self):
        self.assertNotIn("Help & Legal", GOALS_TEMPLATE.read_text(encoding="utf-8"))
        self.assertNotIn("Help & Legal", BUDGET_TEMPLATE.read_text(encoding="utf-8"))
        self.assertNotIn("Help & Legal", SETTINGS_TEMPLATE.read_text(encoding="utf-8"))
        self.assertNotIn("Help & Legal", FX_TEMPLATE.read_text(encoding="utf-8"))
        self.assertNotIn("Help & Legal", DAY3_TEMPLATE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
