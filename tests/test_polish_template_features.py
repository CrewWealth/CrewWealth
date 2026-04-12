import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_TEMPLATE = ROOT / "app" / "templates" / "index.html"
REPORTS_TEMPLATE = ROOT / "app" / "templates" / "reports.html"
REGISTER_TEMPLATE = ROOT / "app" / "templates" / "register.html"
MAIN_ROUTES = ROOT / "app" / "routes" / "main.py"
APP_GUIDE_JS = ROOT / "app" / "static" / "js" / "app-guide.js"


class TestPolishTemplateFeatures(unittest.TestCase):
    def test_reports_has_pdf_export_button_and_function(self):
        content = REPORTS_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("Export complete PDF", content)
        self.assertIn("async function exportReportsToPdf()", content)
        self.assertIn("window.exportReportsToPdf = exportReportsToPdf;", content)

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


if __name__ == "__main__":
    unittest.main()
