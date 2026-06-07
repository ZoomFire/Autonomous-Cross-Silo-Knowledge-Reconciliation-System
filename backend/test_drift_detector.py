import unittest

from claim_extractor import build_truth_triangle, extract_claims, extract_entity
from drift_detector import detect_drift
from models import AnalysisRequest


def analyze_case(documentation="", code="", jira="", commit="", logs="", database_config=""):
    request = AnalysisRequest(
        documentation=documentation,
        code=code,
        jira=jira,
        commit=commit,
        logs=logs,
        database_config=database_config,
    )
    entity = extract_entity(
        [
            request.documentation,
            request.code,
            request.jira,
            request.commit,
            request.logs,
            request.database_config,
        ]
    )
    claims = extract_claims(request, entity)
    return detect_drift(build_truth_triangle(claims), entity)


class DriftDetectorConfigTests(unittest.TestCase):
    def test_public_claim_with_internal_database_config_is_configuration_drift(self):
        report = analyze_case(
            documentation="The /api/customer/profile endpoint is public for customer profile access.",
            code="@public\n@app.route('/api/customer/profile')\ndef profile():\n    return get_profile()",
            jira="JIRA-515: Customer profile is user-facing.",
            commit="Made public profile endpoint available.",
            logs="Request completed for /api/customer/profile",
            database_config="visibility=internal, feature_enabled=true",
        )

        self.assertEqual(report.drift_type, "Configuration Drift")
        self.assertIn("Update database or feature flag configuration", report.recommended_action)
        self.assertTrue(any("Database config says internal" in item for item in report.evidence))

    def test_internal_code_with_public_database_config_is_configuration_drift(self):
        report = analyze_case(
            documentation="The /api/admin/report endpoint is internal-only for operations.",
            code="@internal_only\n@app.route('/api/admin/report')\ndef admin_report():\n    return report()",
            jira="JIRA-1303: Admin report is internal only and restricted.",
            commit="Kept internal-only access for admin report.",
            logs="200 OK for internal user on /api/admin/report",
            database_config="access_type=public, feature_enabled=true",
        )

        self.assertEqual(report.drift_type, "Configuration Drift")
        self.assertTrue(any("Database config says public" in item for item in report.evidence))

    def test_customer_facing_feature_disabled_in_database_is_configuration_drift(self):
        report = analyze_case(
            documentation="The /v2/customer/profile feature is public for customers.",
            code="@public\n@app.route('/v2/customer/profile')\ndef profile_v2():\n    return profile()",
            jira="JIRA-717: Customer profile v2 is ready for production.",
            commit="Completed customer profile v2 rollout.",
            logs="Request completed for /v2/customer/profile",
            database_config="access_type=public, feature_enabled=false",
        )

        self.assertEqual(report.drift_type, "Configuration Drift")
        self.assertTrue(any("Feature is disabled" in item for item in report.evidence))


if __name__ == "__main__":
    unittest.main()
